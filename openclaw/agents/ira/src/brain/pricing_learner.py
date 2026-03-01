#!/usr/bin/env python3
"""
PRICING LEARNER - Learn Prices from Historical Quotes
======================================================

Scans ingested quotes and knowledge to:
1. Extract actual prices quoted to customers
2. Build a price index by machine model
3. Learn pricing patterns (price per sqm, variant multipliers)
4. Provide estimated prices for machines without explicit pricing

Usage:
    from pricing_learner import PricingLearner
    
    learner = PricingLearner()
    learner.scan_knowledge()  # Learn from ingested quotes
    
    # Get price for a machine
    price = learner.get_price("PF1-C-3020")
    # Returns: {"price_inr": 8500000, "source": "quote", "confidence": 0.9}
    
    # Estimate price for unknown machine
    price = learner.estimate_price("PF1-X-2515")
    # Returns: {"price_inr": 7800000, "source": "estimated", "confidence": 0.7}
"""

import os
import sys
import re
import json
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict

# Centralized configuration - handles path setup, env loading, and API keys
BRAIN_DIR = Path(__file__).parent
SKILLS_DIR = BRAIN_DIR.parent
AGENT_DIR = SKILLS_DIR.parent
PROJECT_ROOT = AGENT_DIR.parent.parent.parent

# Use centralized config for path setup and env loading
try:
    sys.path.insert(0, str(AGENT_DIR))
    from config import (
        QDRANT_URL, VOYAGE_API_KEY, PROJECT_ROOT, get_logger,
        setup_import_paths
    )
    setup_import_paths()
    logger = get_logger(__name__)
    QDRANT_API_KEY = os.environ.get("QDRANT_API_KEY", "")
    CONFIG_AVAILABLE = True
except ImportError:
    CONFIG_AVAILABLE = False
    import logging
    logger = logging.getLogger(__name__)
    # Fallback to manual env loading
    for line in (PROJECT_ROOT / ".env").read_text().splitlines():
        if line.strip() and not line.startswith('#') and '=' in line:
            key, _, value = line.partition('=')
            os.environ.setdefault(key.strip(), value.strip().strip('"'))
    QDRANT_URL = os.environ.get("QDRANT_URL", "http://localhost:6333")
    QDRANT_API_KEY = os.environ.get("QDRANT_API_KEY", "")
    VOYAGE_API_KEY = os.environ.get("VOYAGE_API_KEY", "")

PRICE_INDEX_FILE = PROJECT_ROOT / "data" / "knowledge" / "price_index.json"
PRICING_PATTERNS_FILE = PROJECT_ROOT / "data" / "knowledge" / "pricing_patterns.json"
PRICE_CONFLICTS_FILE = PROJECT_ROOT / "data" / "knowledge" / "price_conflicts.json"

RUSHABH_CHAT_ID = "5700751574"
PRICE_VARIANCE_THRESHOLD = 0.15

# Import centralized patterns
try:
    from patterns import (
        MACHINE_PATTERNS,
        extract_machine_models,
        extract_prices,
        USD_TO_INR,
        EUR_TO_INR,
    )
    PATTERNS_AVAILABLE = True
except ImportError:
    PATTERNS_AVAILABLE = False
    # Fallback patterns
    MACHINE_PATTERNS = {"pf1": re.compile(r'PF1-([A-Z])-?(\d{2,4})', re.IGNORECASE)}
    USD_TO_INR = 83
    EUR_TO_INR = 90

# Additional price patterns for pricing_learner specific extractions
PRICE_PATTERNS_LOCAL = [
    r'(?:INR|Rs\.?|₹)\s*([\d,]+(?:\.\d+)?)\s*(?:/-|lakhs?|lacs?)?',
    r'(?:USD|\$)\s*([\d,]+(?:\.\d+)?)',
    r'(?:EUR|€)\s*([\d,]+(?:\.\d+)?)',
    r'([\d,]+)\s*(?:INR|Rs)',
    r'Price[:\s]+(?:INR|Rs\.?|₹)?\s*([\d,]+)',
    r'Budget[:\s]+(?:INR|Rs\.?|₹)?\s*([\d,]+)',
]

# Define MACHINE_PATTERN for price extraction (captures variant and size)
MACHINE_PATTERN = r'PF1-([A-Z])-?(\d{4})'
PRICE_PATTERNS = PRICE_PATTERNS_LOCAL


@dataclass
class PriceRecord:
    """A single price record from a quote."""
    machine_model: str
    price_inr: int
    currency_original: str
    source_file: str
    quote_date: Optional[str] = None
    customer: Optional[str] = None
    confidence: float = 0.8
    context: str = ""


@dataclass
class PriceConflict:
    """A detected price conflict requiring clarification."""
    machine_model: str
    prices: List[Dict]  # [{price_inr, source, confidence}, ...]
    variance_percent: float
    detected_at: str
    status: str = "pending"  # pending, clarified, resolved
    resolution: Optional[str] = None


@dataclass
class PriceIndex:
    """Index of all known prices."""
    prices_by_model: Dict[str, List[PriceRecord]] = field(default_factory=dict)
    prices_by_variant: Dict[str, List[int]] = field(default_factory=dict)
    prices_by_size: Dict[str, List[int]] = field(default_factory=dict)
    last_updated: str = ""
    total_records: int = 0


class PricingLearner:
    """
    Learns pricing from historical quotes and provides estimates.
    """
    
    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self._qdrant = None
        self._voyage = None
        self.price_index = self._load_price_index()
        self.pricing_patterns = self._load_pricing_patterns()
    
    def _log(self, msg: str):
        if self.verbose:
            logger.info(msg)
    
    def _get_qdrant(self):
        if self._qdrant is None:
            from qdrant_client import QdrantClient
            self._qdrant = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
        return self._qdrant
    
    def _load_price_index(self) -> Dict:
        """Load existing price index."""
        if PRICE_INDEX_FILE.exists():
            try:
                return json.loads(PRICE_INDEX_FILE.read_text())
            except (json.JSONDecodeError, IOError, OSError):
                pass
        return {"prices_by_model": {}, "prices_by_variant": {}, "last_updated": "", "total_records": 0}
    
    def _save_price_index(self):
        """Save price index to disk."""
        PRICE_INDEX_FILE.parent.mkdir(parents=True, exist_ok=True)
        self.price_index["last_updated"] = datetime.now().isoformat()
        PRICE_INDEX_FILE.write_text(json.dumps(self.price_index, indent=2))
    
    def _load_pricing_patterns(self) -> Dict:
        """Load learned pricing patterns."""
        if PRICING_PATTERNS_FILE.exists():
            try:
                return json.loads(PRICING_PATTERNS_FILE.read_text())
            except (json.JSONDecodeError, IOError, OSError):
                pass
        return {
            "price_per_sqm_by_variant": {},
            "variant_multipliers": {},
            "option_premiums": {},
        }
    
    def _save_pricing_patterns(self):
        """Save learned pricing patterns."""
        PRICING_PATTERNS_FILE.parent.mkdir(parents=True, exist_ok=True)
        PRICING_PATTERNS_FILE.write_text(json.dumps(self.pricing_patterns, indent=2))
    
    def _load_conflicts(self) -> List[Dict]:
        """Load pending price conflicts."""
        if PRICE_CONFLICTS_FILE.exists():
            try:
                return json.loads(PRICE_CONFLICTS_FILE.read_text())
            except (json.JSONDecodeError, IOError, OSError):
                pass
        return []
    
    def _save_conflicts(self, conflicts: List[Dict]):
        """Save price conflicts."""
        PRICE_CONFLICTS_FILE.parent.mkdir(parents=True, exist_ok=True)
        PRICE_CONFLICTS_FILE.write_text(json.dumps(conflicts, indent=2, default=str))
    
    def _extract_prices_from_text(self, text: str, source_file: str) -> List[PriceRecord]:
        """Extract price records from text."""
        records = []
        
        machines = re.findall(MACHINE_PATTERN, text, re.IGNORECASE)
        if not machines:
            return records
        
        prices_found = []
        for pattern in PRICE_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    price_str = match.replace(',', '').replace(' ', '')
                    price = float(price_str)
                    
                    if price < 100:
                        price = int(price * 100000)
                    elif price < 10000:
                        price = int(price * 1000)
                    else:
                        price = int(price)
                    
                    if 100000 < price < 500000000:
                        currency = "INR"
                        if "$" in text[:text.find(match) + 20] if match in text else False:
                            currency = "USD"
                            price = int(price * USD_TO_INR)
                        elif "€" in text[:text.find(match) + 20] if match in text else False:
                            currency = "EUR"
                            price = int(price * EUR_TO_INR)
                        
                        if price >= 2_000_000:
                            prices_found.append((price, currency))
                except (ValueError, TypeError):
                    continue
        
        if not prices_found:
            return records
        
        for variant, size in machines:
            model = f"PF1-{variant.upper()}-{size}"
            
            for price, currency in prices_found:
                context_start = max(0, text.find(model) - 100)
                context_end = min(len(text), text.find(model) + 200)
                context = text[context_start:context_end]
                
                records.append(PriceRecord(
                    machine_model=model,
                    price_inr=price,
                    currency_original=currency,
                    source_file=source_file,
                    confidence=0.7 if len(machines) > 1 else 0.9,
                    context=context[:200],
                ))
        
        return records
    
    def scan_knowledge(self) -> Dict[str, Any]:
        """
        Scan ingested knowledge for price information.
        """
        self._log("Scanning knowledge for pricing data...")
        
        qdrant = self._get_qdrant()
        
        collections = [
            "ira_discovered_knowledge",
            "ira_chunks_v4_voyage",
            "ira_dream_knowledge_v1",
        ]
        
        all_records = []
        
        for collection in collections:
            try:
                results = qdrant.scroll(
                    collection_name=collection,
                    limit=500,
                    with_payload=True,
                )
                
                self._log(f"  Scanning {collection}: {len(results[0])} points")
                
                for point in results[0]:
                    payload = point.payload or {}
                    text = payload.get("text", payload.get("raw_text", ""))
                    source = payload.get("filename", payload.get("source_file", "unknown"))
                    
                    if not text:
                        continue
                    
                    records = self._extract_prices_from_text(text, source)
                    all_records.extend(records)
                    
            except Exception as e:
                self._log(f"  Error scanning {collection}: {e}")
        
        quotes_json = PROJECT_ROOT / "data" / "quotes_knowledge.json"
        if quotes_json.exists():
            try:
                quotes = json.loads(quotes_json.read_text())
                self._log(f"  Scanning quotes JSON: {len(quotes)} items")
                
                for item in quotes:
                    text = item.get("text", "")
                    source = item.get("filename", "quotes.json")
                    records = self._extract_prices_from_text(text, source)
                    all_records.extend(records)
            except Exception as e:
                self._log(f"  Error scanning quotes JSON: {e}")
        
        self._log(f"\nExtracted {len(all_records)} price records")
        
        self._index_prices(all_records)
        self._learn_patterns()
        
        return {
            "records_found": len(all_records),
            "models_indexed": len(self.price_index["prices_by_model"]),
            "variants_indexed": len(self.price_index.get("prices_by_variant", {})),
        }
    
    def _index_prices(self, records: List[PriceRecord]):
        """Build price index from records."""
        prices_by_model = defaultdict(list)
        prices_by_variant = defaultdict(list)
        prices_by_size = defaultdict(list)
        
        for record in records:
            model = record.machine_model
            prices_by_model[model].append({
                "price_inr": record.price_inr,
                "source": record.source_file,
                "confidence": record.confidence,
                "context": record.context[:100],
            })
            
            match = re.match(MACHINE_PATTERN, model)
            if match:
                variant = match.group(1).upper()
                size = match.group(2)
                
                prices_by_variant[variant].append(record.price_inr)
                prices_by_size[size].append(record.price_inr)
        
        best_by_model = {}
        for model, price_list in prices_by_model.items():
            sorted_prices = sorted(price_list, key=lambda x: -x["confidence"])
            best_by_model[model] = sorted_prices[:5]
        
        self.price_index = {
            "prices_by_model": best_by_model,
            "prices_by_variant": {k: list(set(v)) for k, v in prices_by_variant.items()},
            "prices_by_size": {k: list(set(v)) for k, v in prices_by_size.items()},
            "total_records": len(records),
            "last_updated": datetime.now().isoformat(),
        }
        
        self._save_price_index()
        self._log(f"Indexed {len(best_by_model)} unique models")
        
        conflicts = self._detect_conflicts(best_by_model)
        if conflicts:
            self._log(f"⚠ Detected {len(conflicts)} price conflicts")
    
    def _detect_conflicts(self, prices_by_model: Dict) -> List[Dict]:
        """Detect price conflicts (same model, different prices)."""
        conflicts = []
        existing_conflicts = self._load_conflicts()
        existing_models = {c["machine_model"] for c in existing_conflicts if c.get("status") == "pending"}
        
        for model, price_list in prices_by_model.items():
            if len(price_list) < 2:
                continue
            
            prices = [p["price_inr"] for p in price_list]
            min_price = min(prices)
            max_price = max(prices)
            
            if min_price == 0:
                continue
            
            variance = (max_price - min_price) / min_price
            
            if variance > PRICE_VARIANCE_THRESHOLD:
                if model not in existing_models:
                    conflict = {
                        "machine_model": model,
                        "prices": price_list[:5],
                        "variance_percent": round(variance * 100, 1),
                        "min_price": min_price,
                        "max_price": max_price,
                        "detected_at": datetime.now().isoformat(),
                        "status": "pending",
                    }
                    conflicts.append(conflict)
        
        if conflicts:
            all_conflicts = existing_conflicts + conflicts
            self._save_conflicts(all_conflicts)
        
        return conflicts
    
    def get_pending_conflicts(self) -> List[Dict]:
        """Get all pending price conflicts."""
        conflicts = self._load_conflicts()
        return [c for c in conflicts if c.get("status") == "pending"]
    
    def resolve_conflict(self, model: str, correct_price: int, resolution_note: str = ""):
        """Mark a conflict as resolved with the correct price."""
        conflicts = self._load_conflicts()
        
        for conflict in conflicts:
            if conflict.get("machine_model") == model and conflict.get("status") == "pending":
                conflict["status"] = "resolved"
                conflict["correct_price"] = correct_price
                conflict["resolution"] = resolution_note
                conflict["resolved_at"] = datetime.now().isoformat()
        
        self._save_conflicts(conflicts)
    
    def format_conflicts_message(self) -> str:
        """Format pending conflicts as a Telegram message."""
        conflicts = self.get_pending_conflicts()
        
        if not conflicts:
            return ""
        
        lines = ["🔍 **Price Conflicts Detected**\n"]
        lines.append("I found some price discrepancies that need your clarification:\n")
        
        for i, c in enumerate(conflicts[:5], 1):
            model = c["machine_model"]
            variance = c["variance_percent"]
            
            lines.append(f"**{i}. {model}** (variance: {variance}%)")
            
            for p in c["prices"][:3]:
                price = p["price_inr"]
                source = p.get("source", "unknown")[:25]
                lines.append(f"   • ₹{price:,} ({source})")
            
            lines.append("")
        
        if len(conflicts) > 5:
            lines.append(f"... and {len(conflicts) - 5} more conflicts")
        
        lines.append("\n📝 Reply with the correct price for each model, e.g.:")
        lines.append("`PF1-C-3020: 85 lakh` or `resolve PF1-C-3020 8500000`")
        
        return "\n".join(lines)
    
    def send_conflicts_notification(self) -> bool:
        """Send price conflicts notification via Telegram."""
        message = self.format_conflicts_message()
        
        if not message:
            self._log("No pending conflicts to notify")
            return False
        
        try:
            import requests
            
            telegram_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
            if not telegram_token:
                self._log("No Telegram token configured")
                return False
            
            url = f"https://api.telegram.org/bot{telegram_token}/sendMessage"
            payload = {
                "chat_id": RUSHABH_CHAT_ID,
                "text": message,
                "parse_mode": "Markdown",
            }
            
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                self._log(f"✓ Sent conflicts notification to Telegram")
                return True
            else:
                self._log(f"✗ Telegram notification failed: {response.text}")
                return False
                
        except Exception as e:
            self._log(f"✗ Error sending notification: {e}")
            return False
    
    def _learn_patterns(self):
        """Learn pricing patterns from indexed data."""
        prices_by_variant = self.price_index.get("prices_by_variant", {})
        
        variant_avg = {}
        for variant, prices in prices_by_variant.items():
            if prices:
                variant_avg[variant] = sum(prices) / len(prices)
        
        if "C" in variant_avg:
            base = variant_avg["C"]
            multipliers = {}
            for variant, avg in variant_avg.items():
                multipliers[variant] = round(avg / base, 2)
            self.pricing_patterns["variant_multipliers"] = multipliers
        
        self._save_pricing_patterns()
        self._log(f"Learned variant multipliers: {self.pricing_patterns.get('variant_multipliers', {})}")
    
    def get_price(self, model: str) -> Optional[Dict]:
        """
        Get known price for a machine model.
        
        Returns:
            {"price_inr": int, "price_usd": int, "source": str, "confidence": float}
            or None if not found
        """
        model = model.upper()
        
        prices = self.price_index.get("prices_by_model", {}).get(model)
        if prices:
            best = prices[0]
            return {
                "price_inr": best["price_inr"],
                "price_usd": best["price_inr"] // USD_TO_INR,
                "source": "quote",
                "source_file": best.get("source", "unknown"),
                "confidence": best["confidence"],
            }
        
        return None
    
    def estimate_price(self, model: str) -> Dict:
        """
        Estimate price for a machine model (even if not in index).
        
        Uses:
        1. Exact match from price index
        2. Similar models (same size, different variant)
        3. Learned patterns (price per sqm, variant multipliers)
        """
        known = self.get_price(model)
        if known:
            return known
        
        match = re.match(MACHINE_PATTERN, model.upper())
        if not match:
            return {"error": f"Invalid model format: {model}"}
        
        variant = match.group(1).upper()
        size = match.group(2)
        
        other_variants = ["C", "X", "S", "A", "P", "R"]
        multipliers = self.pricing_patterns.get("variant_multipliers", {
            "C": 1.0, "X": 1.35, "S": 1.35, "A": 1.0, "P": 0.85, "R": 1.15
        })
        
        for other_var in other_variants:
            if other_var == variant:
                continue
            other_model = f"PF1-{other_var}-{size}"
            other_price = self.get_price(other_model)
            if other_price:
                base_mult = multipliers.get(other_var, 1.0)
                target_mult = multipliers.get(variant, 1.0)
                
                estimated_price = int(other_price["price_inr"] * (target_mult / base_mult))
                
                return {
                    "price_inr": estimated_price,
                    "price_usd": estimated_price // USD_TO_INR,
                    "source": "estimated",
                    "method": f"derived from {other_model}",
                    "confidence": 0.7,
                }
        
        prices_for_size = self.price_index.get("prices_by_size", {}).get(size, [])
        if prices_for_size:
            avg_price = sum(prices_for_size) / len(prices_for_size)
            target_mult = multipliers.get(variant, 1.0)
            
            estimated_price = int(avg_price * target_mult)
            
            return {
                "price_inr": estimated_price,
                "price_usd": estimated_price // USD_TO_INR,
                "source": "estimated",
                "method": f"size average for {size}",
                "confidence": 0.5,
            }
        
        try:
            width = int(size[:2]) * 100
            height = int(size[2:]) * 100
            sqm = (width * height) / 1_000_000
            
            base_per_sqm = 1_800_000
            base_price = int(sqm * base_per_sqm)
            base_price = max(base_price, 3_000_000)
            
            target_mult = multipliers.get(variant, 1.0)
            estimated_price = int(base_price * target_mult)
            
            return {
                "price_inr": estimated_price,
                "price_usd": estimated_price // USD_TO_INR,
                "source": "estimated",
                "method": "formula (no historical data)",
                "confidence": 0.4,
            }
        except (ValueError, KeyError, TypeError) as e:
            return {"error": f"Could not estimate price for {model}: {e}"}
    
    def get_price_summary(self) -> str:
        """Get a summary of indexed prices."""
        lines = []
        lines.append("=" * 60)
        lines.append("PRICE INDEX SUMMARY")
        lines.append("=" * 60)
        
        prices_by_model = self.price_index.get("prices_by_model", {})
        lines.append(f"Models indexed: {len(prices_by_model)}")
        lines.append(f"Last updated: {self.price_index.get('last_updated', 'never')}")
        lines.append("")
        
        lines.append("Prices by Model:")
        for model in sorted(prices_by_model.keys())[:20]:
            prices = prices_by_model[model]
            best = prices[0]
            lines.append(f"  {model}: ₹{best['price_inr']:,} ({best.get('source', '?')[:30]})")
        
        if len(prices_by_model) > 20:
            lines.append(f"  ... and {len(prices_by_model) - 20} more")
        
        lines.append("")
        lines.append("Variant Multipliers (learned):")
        for v, m in self.pricing_patterns.get("variant_multipliers", {}).items():
            lines.append(f"  PF1-{v}: {m:.2f}x")
        
        return "\n".join(lines)


def get_price_for_model(model: str) -> Dict:
    """Quick function to get price for a model."""
    learner = PricingLearner(verbose=False)
    return learner.estimate_price(model)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Pricing Learner")
    parser.add_argument("--scan", action="store_true", help="Scan knowledge for prices")
    parser.add_argument("--model", type=str, help="Get price for a model")
    parser.add_argument("--summary", action="store_true", help="Show price summary")
    parser.add_argument("--conflicts", action="store_true", help="Show pending price conflicts")
    parser.add_argument("--notify", action="store_true", help="Send conflicts notification via Telegram")
    parser.add_argument("--resolve", nargs=2, metavar=("MODEL", "PRICE"), help="Resolve a conflict")
    args = parser.parse_args()
    
    learner = PricingLearner()
    
    if args.scan:
        result = learner.scan_knowledge()
        print(f"\nScan complete: {result}")
    
    if args.model:
        price = learner.estimate_price(args.model)
        print(f"\nPrice for {args.model}:")
        print(json.dumps(price, indent=2))
    
    if args.conflicts:
        conflicts = learner.get_pending_conflicts()
        if conflicts:
            print(f"\n=== {len(conflicts)} Pending Price Conflicts ===\n")
            for c in conflicts:
                model = c["machine_model"]
                variance = c["variance_percent"]
                print(f"{model} (variance: {variance}%)")
                for p in c["prices"][:3]:
                    print(f"  ₹{p['price_inr']:,} from {p.get('source', '?')[:30]}")
                print()
        else:
            print("\nNo pending conflicts.")
    
    if args.notify:
        learner.send_conflicts_notification()
    
    if args.resolve:
        model, price_str = args.resolve
        try:
            price = int(price_str.replace(",", "").replace("lakh", "00000").replace(" ", ""))
            learner.resolve_conflict(model.upper(), price, "Resolved via CLI")
            print(f"✓ Resolved {model} with price ₹{price:,}")
        except ValueError:
            print(f"✗ Invalid price: {price_str}")
    
    if args.summary or not any([args.scan, args.model, args.conflicts, args.notify, args.resolve]):
        print(learner.get_price_summary())


# =============================================================================
# SINGLETON
# =============================================================================

_pricing_learner: Optional[PricingLearner] = None


def get_pricing_learner() -> PricingLearner:
    """Get singleton PricingLearner instance."""
    global _pricing_learner
    if _pricing_learner is None:
        _pricing_learner = PricingLearner()
    return _pricing_learner
