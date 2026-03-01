#!/usr/bin/env python3
"""
QUOTES 2 INGESTION SCRIPT
=========================

Ingests all PDF quotes from data/imports/Quotes 2/ folder.
Extracts:
- Machine models and pricing
- Quote dates (from filename patterns and file metadata)
- Customer information
- Applications

Then feeds the data to the pricing learner to build pricing logic.

Usage:
    python scripts/ingest_quotes2.py
    python scripts/ingest_quotes2.py --learn-only  # Skip ingestion, just learn pricing
    python scripts/ingest_quotes2.py --dry-run     # Preview without ingesting
"""

import os
import sys
import re
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict

# Setup paths
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
AGENT_DIR = PROJECT_ROOT / "openclaw" / "agents" / "ira"
BRAIN_DIR = AGENT_DIR / "skills" / "brain"

sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(AGENT_DIR))
sys.path.insert(0, str(BRAIN_DIR))

# Load environment
env_file = PROJECT_ROOT / ".env"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        if line.strip() and not line.startswith('#') and '=' in line:
            key, _, value = line.partition('=')
            os.environ[key.strip()] = value.strip().strip('"')

# Imports
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

QUOTES2_DIR = PROJECT_ROOT / "data" / "imports" / "Quotes 2"
QUOTES_KNOWLEDGE_FILE = PROJECT_ROOT / "data" / "quotes2_knowledge.json"

# Patterns
MACHINE_PATTERNS = [
    r'PF1-[A-Z]?-?\d{4}',
    r'PF1\s+\d{4}',
    r'PF2-\d+[xX]\d+',
    r'AM-?[A-Z]?-?\d{4}',
    r'AMP-?\d{4}',
    r'AMC-?\d{4}',
    r'IMG[SL]?-?\d{4}',
    r'FCS-?\d{4}',
    r'ATF-?\d{4}',
    r'RT-?\d[A-Z]-?\d{4}',
    r'EFX-?\d{4}',
    r'AO-?\d{4}',
]

PRICE_PATTERNS = [
    (r'(?:INR|Rs\.?|₹)\s*([\d,]+(?:\.\d+)?)\s*(?:/-|lakhs?|lacs?)?', 'INR'),
    (r'(?:USD|\$)\s*([\d,]+(?:\.\d+)?)', 'USD'),
    (r'(?:EUR|€)\s*([\d,]+(?:\.\d+)?)', 'EUR'),
    (r'([\d,]+)\s*(?:INR|Rs)', 'INR'),
    (r'Price[:\s]+(?:INR|Rs\.?|₹)?\s*([\d,]+)', 'INR'),
    (r'Total[:\s]+(?:INR|Rs\.?|₹)?\s*([\d,]+)', 'INR'),
]

USD_TO_INR = 83
EUR_TO_INR = 90


def extract_date_from_filename(filename: str) -> Optional[str]:
    """
    Extract quote date from filename patterns.
    
    Patterns recognized:
    - MT2021061801 -> 2021-06-18
    - 2022K0001 -> 2022
    - Apr 17 2023 -> 2023-04-17
    - Nov 25 2022 -> 2022-11-25
    """
    # Pattern: MT followed by YYYYMMDD
    match = re.search(r'MT(\d{4})(\d{2})(\d{2})', filename)
    if match:
        year, month, day = match.groups()
        try:
            date = datetime(int(year), int(month), int(day))
            return date.strftime('%Y-%m-%d')
        except ValueError:
            pass
    
    # Pattern: YYYYK followed by number (e.g., 2022K0001)
    match = re.search(r'(\d{4})K\d+', filename)
    if match:
        return f"{match.group(1)}-01-01"
    
    # Pattern: Month Year in filename
    months = {
        'jan': '01', 'feb': '02', 'mar': '03', 'apr': '04',
        'may': '05', 'jun': '06', 'jul': '07', 'aug': '08',
        'sep': '09', 'oct': '10', 'nov': '11', 'dec': '12'
    }
    
    for month_name, month_num in months.items():
        # Pattern: "Apr 2023" or "April 2023"
        match = re.search(rf'{month_name}\w*\s*(\d{{4}})', filename, re.IGNORECASE)
        if match:
            return f"{match.group(1)}-{month_num}-01"
        
        # Pattern: "17 Apr 2023" or similar
        match = re.search(rf'(\d{{1,2}})\s*{month_name}\w*\s*(\d{{4}})', filename, re.IGNORECASE)
        if match:
            day = match.group(1).zfill(2)
            year = match.group(2)
            return f"{year}-{month_num}-{day}"
    
    # Pattern: Just year (2023, 2022, etc.)
    match = re.search(r'20(1[8-9]|2[0-6])', filename)
    if match:
        return f"20{match.group(1)}-01-01"
    
    return None


def extract_date_from_file(pdf_path: Path) -> str:
    """Get date from filename or file modification time."""
    # Try filename first
    date_from_name = extract_date_from_filename(pdf_path.name)
    if date_from_name:
        return date_from_name
    
    # Fall back to file modification time
    mtime = pdf_path.stat().st_mtime
    return datetime.fromtimestamp(mtime).strftime('%Y-%m-%d')


def extract_machines(text: str) -> List[str]:
    """Extract machine model numbers from text."""
    machines = set()
    for pattern in MACHINE_PATTERNS:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            # Normalize
            model = match.upper().replace(' ', '-')
            # Ensure proper format
            model = re.sub(r'(\w+)-?(\d{4})', r'\1-\2', model)
            machines.add(model)
    return list(machines)


def extract_prices(text: str) -> List[Dict]:
    """Extract prices with currency from text."""
    prices = []
    
    for pattern, currency in PRICE_PATTERNS:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            try:
                price_str = match.replace(',', '').replace(' ', '')
                price = float(price_str)
                
                # Handle lakhs notation
                if price < 1000:
                    price = price * 100000  # Lakhs to actual
                
                # Convert to INR
                price_inr = int(price)
                if currency == 'USD':
                    price_inr = int(price * USD_TO_INR)
                elif currency == 'EUR':
                    price_inr = int(price * EUR_TO_INR)
                
                # Only valid machine prices (2 lakh to 50 crore)
                if 200000 <= price_inr <= 500000000:
                    prices.append({
                        'amount': price_inr,
                        'currency': currency,
                        'original': match
                    })
            except (ValueError, TypeError):
                continue
    
    # Deduplicate and return top prices
    seen = set()
    unique_prices = []
    for p in prices:
        if p['amount'] not in seen:
            seen.add(p['amount'])
            unique_prices.append(p)
    
    return unique_prices[:5]


def extract_customer(text: str, filename: str) -> str:
    """Extract customer/company name."""
    # Common patterns
    patterns = [
        r'(?:To|Attention|Attn)[:\s]+([A-Z][A-Za-z\s]+(?:Ltd|Inc|Corp|Pvt|LLC|GmbH|S\.?A\.?)?)',
        r'(?:Dear|Hi|Hello)\s+(?:Mr\.?|Ms\.?|Mrs\.?)?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',
        r'Quote\s+(?:for|to)\s+([A-Z][A-Za-z\s]+)',
        r'Offer\s+(?:for|to)\s+([A-Z][A-Za-z\s]+)',
        r'([A-Z][A-Za-z\s]+(?:Ltd|Inc|Corp|Pvt|LLC|GmbH|S\.?A\.?))',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text[:3000])
        if match:
            name = match.group(1).strip()
            # Filter out Machinecraft
            if 'machinecraft' not in name.lower() and 3 < len(name) < 50:
                return re.sub(r'\s+', ' ', name)
    
    # Try filename
    filename_clean = re.sub(r'[_\-\d]+', ' ', filename)
    words = [w for w in filename_clean.split() if len(w) > 3 and w[0].isupper()]
    if words:
        return ' '.join(words[:3])
    
    return ""


def process_pdf(pdf_path: Path, dry_run: bool = False) -> Optional[Dict]:
    """Process a single PDF and extract quote data."""
    try:
        from document_extractor import extract_pdf
    except ImportError:
        logger.error("document_extractor not available")
        return None
    
    logger.info(f"Processing: {pdf_path.name}")
    
    text = extract_pdf(pdf_path)
    if not text or len(text) < 50:
        logger.warning(f"  Could not extract text from {pdf_path.name}")
        return None
    
    # Extract data
    machines = extract_machines(text)
    prices = extract_prices(text)
    customer = extract_customer(text, pdf_path.name)
    quote_date = extract_date_from_file(pdf_path)
    
    if not machines and not prices:
        logger.info(f"  No machines or prices found")
        return None
    
    # Build result
    result = {
        "filename": pdf_path.name,
        "quote_date": quote_date,
        "machines": machines,
        "prices": prices,
        "customer": customer,
        "text": text[:10000],
        "extracted_at": datetime.now().isoformat(),
    }
    
    # Log findings
    logger.info(f"  Date: {quote_date}")
    logger.info(f"  Machines: {machines[:3]}")
    logger.info(f"  Prices: {[p['amount'] for p in prices[:3]]}")
    logger.info(f"  Customer: {customer or 'N/A'}")
    
    return result


def ingest_to_qdrant(items: List[Dict]) -> int:
    """Ingest items to Qdrant."""
    try:
        from knowledge_ingestor import KnowledgeIngestor, KnowledgeItem
    except ImportError:
        logger.error("knowledge_ingestor not available")
        return 0
    
    ingestor = KnowledgeIngestor(use_graph=False, verbose=False)
    ingested = 0
    
    for item in items:
        # Create summary with date
        date_str = item.get('quote_date', 'unknown date')
        machines_str = ', '.join(item.get('machines', [])[:3])
        prices_str = ', '.join([f"₹{p['amount']:,}" for p in item.get('prices', [])[:2]])
        customer = item.get('customer', 'unknown customer')
        
        summary = f"Quote from {date_str}"
        if machines_str:
            summary += f" for {machines_str}"
        if customer:
            summary += f" to {customer}"
        if prices_str:
            summary += f" - {prices_str}"
        
        ki = KnowledgeItem(
            text=item['text'],
            entity=item['machines'][0] if item.get('machines') else item.get('customer', 'quote'),
            knowledge_type='pricing',
            source_file=item['filename'],
            summary=summary,
            metadata={
                'doc_type': 'machine_quote',
                'quote_date': item.get('quote_date'),
                'machines': item.get('machines', []),
                'prices': item.get('prices', []),
                'customer': item.get('customer', ''),
            }
        )
        
        try:
            result = ingestor.ingest_batch([ki])
            if result.items_ingested > 0:
                ingested += 1
        except Exception as e:
            logger.error(f"Ingest error for {item['filename']}: {e}")
    
    return ingested


def save_quotes_json(items: List[Dict]):
    """Save extracted quotes to JSON for backup and pricing learner."""
    QUOTES_KNOWLEDGE_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    # Load existing
    existing = []
    if QUOTES_KNOWLEDGE_FILE.exists():
        try:
            existing = json.loads(QUOTES_KNOWLEDGE_FILE.read_text())
        except (json.JSONDecodeError, IOError):
            pass
    
    # Merge (avoid duplicates by filename)
    existing_files = {item['filename'] for item in existing}
    new_items = [item for item in items if item['filename'] not in existing_files]
    
    all_items = existing + new_items
    QUOTES_KNOWLEDGE_FILE.write_text(json.dumps(all_items, indent=2, default=str))
    
    logger.info(f"Saved {len(new_items)} new items to {QUOTES_KNOWLEDGE_FILE}")
    logger.info(f"Total items in JSON: {len(all_items)}")


def run_pricing_learner():
    """Run the pricing learner to update price index."""
    logger.info("\n" + "=" * 60)
    logger.info("RUNNING PRICING LEARNER")
    logger.info("=" * 60)
    
    try:
        from pricing_learner import PricingLearner
        
        learner = PricingLearner(verbose=True)
        result = learner.scan_knowledge()
        
        logger.info(f"\nPricing Learner Results:")
        logger.info(f"  Records found: {result.get('records_found', 0)}")
        logger.info(f"  Models indexed: {result.get('models_indexed', 0)}")
        logger.info(f"  Variants indexed: {result.get('variants_indexed', 0)}")
        
        # Show some learned prices
        if learner.price_index.get('prices_by_model'):
            logger.info("\nSample learned prices:")
            for model, prices in list(learner.price_index['prices_by_model'].items())[:10]:
                avg_price = sum(p['price_inr'] for p in prices) / len(prices)
                logger.info(f"  {model}: ₹{avg_price:,.0f} ({len(prices)} quotes)")
        
        return result
        
    except Exception as e:
        logger.error(f"Pricing learner error: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    parser = argparse.ArgumentParser(description="Ingest quotes from Quotes 2 folder")
    parser.add_argument('--dry-run', action='store_true', help="Preview without ingesting")
    parser.add_argument('--learn-only', action='store_true', help="Skip ingestion, just run pricing learner")
    parser.add_argument('--limit', type=int, default=0, help="Limit number of files to process")
    args = parser.parse_args()
    
    logger.info("=" * 60)
    logger.info("QUOTES 2 INGESTION")
    logger.info("=" * 60)
    logger.info(f"Source: {QUOTES2_DIR}")
    logger.info(f"Dry run: {args.dry_run}")
    logger.info("=" * 60)
    
    if args.learn_only:
        run_pricing_learner()
        return
    
    if not QUOTES2_DIR.exists():
        logger.error(f"Directory not found: {QUOTES2_DIR}")
        return
    
    # Get all PDFs
    pdf_files = list(QUOTES2_DIR.glob("*.pdf"))
    logger.info(f"Found {len(pdf_files)} PDF files")
    
    if args.limit > 0:
        pdf_files = pdf_files[:args.limit]
        logger.info(f"Limited to {args.limit} files")
    
    # Process files
    items = []
    stats = {
        'total': len(pdf_files),
        'processed': 0,
        'failed': 0,
        'by_year': defaultdict(int),
    }
    
    for idx, pdf_path in enumerate(pdf_files, 1):
        logger.info(f"\n[{idx}/{len(pdf_files)}] {pdf_path.name}")
        
        result = process_pdf(pdf_path, dry_run=args.dry_run)
        
        if result:
            items.append(result)
            stats['processed'] += 1
            
            # Track by year
            quote_date = result.get('quote_date', '')
            if quote_date:
                year = quote_date[:4]
                stats['by_year'][year] += 1
        else:
            stats['failed'] += 1
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("EXTRACTION COMPLETE")
    logger.info("=" * 60)
    logger.info(f"Total files: {stats['total']}")
    logger.info(f"Processed: {stats['processed']}")
    logger.info(f"Failed: {stats['failed']}")
    
    logger.info("\nQuotes by year:")
    for year in sorted(stats['by_year'].keys()):
        logger.info(f"  {year}: {stats['by_year'][year]} quotes")
    
    if args.dry_run:
        logger.info("\n[DRY RUN] Skipping ingestion")
        return
    
    # Save to JSON
    save_quotes_json(items)
    
    # Ingest to Qdrant
    logger.info("\n" + "=" * 60)
    logger.info("INGESTING TO QDRANT")
    logger.info("=" * 60)
    
    ingested = ingest_to_qdrant(items)
    logger.info(f"Ingested {ingested} items to Qdrant")
    
    # Run pricing learner
    run_pricing_learner()
    
    logger.info("\n" + "=" * 60)
    logger.info("DONE!")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
