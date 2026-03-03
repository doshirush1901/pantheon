#!/usr/bin/env python3
"""
DATABASE POPULATOR - Automated extraction from PDF documents
=============================================================

Implements Strategy 1 from DEEP_REPLY_IMPROVEMENT_STRATEGY.md:
Auto-extract technical specifications from PDF catalogues and quotations.

This directly addresses the data completeness gap:
- Only 29% of machines have vacuum specs → Target 95%
- Only 34% of machines have heater type → Target 95%
- Only 43% of machines have features → Target 90%

Flow:
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  PDF Catalogues │────▶│  LLM Extractor   │────▶│ Machine Database│
│  & Quotations   │     │  (structured)    │     │   (verified)    │
└─────────────────┘     └──────────────────┘     └─────────────────┘

Usage:
    from database_populator import DatabasePopulator, populate_from_pdfs
    
    # Auto-populate from all PDFs
    result = populate_from_pdfs("/path/to/data/imports")
    
    # Or use the class directly
    populator = DatabasePopulator()
    extractions = populator.scan_directory("/path/to/pdfs")
    populator.save_extractions(extractions)
"""

import json
import hashlib
import logging
import os
import re
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

SKILL_DIR = Path(__file__).parent
AGENT_DIR = SKILL_DIR.parent.parent
PROJECT_ROOT = AGENT_DIR.parent.parent.parent

sys.path.insert(0, str(AGENT_DIR))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

IMPORTS_DIR = PROJECT_ROOT / "data" / "imports"
EXTRACTION_LOG_FILE = PROJECT_ROOT / "data" / "knowledge" / "extraction_log.json"
EXTRACTED_SPECS_FILE = PROJECT_ROOT / "data" / "knowledge" / "extracted_machine_specs.json"
PROCESSED_HASHES_FILE = PROJECT_ROOT / "data" / "knowledge" / "pdf_processed_hashes.json"


@dataclass
class ExtractedMachineSpec:
    """Structured machine specification extracted from a document."""
    model: str
    series: str = ""
    variant: str = ""
    
    price_inr: Optional[int] = None
    price_usd: Optional[int] = None
    
    forming_area_mm: str = ""
    max_tool_height_mm: Optional[int] = None
    max_draw_depth_mm: Optional[int] = None
    max_sheet_thickness_mm: Optional[float] = None
    min_sheet_thickness_mm: Optional[float] = None
    
    heater_power_kw: Optional[float] = None
    heater_type: str = ""
    num_heaters: Optional[int] = None
    heater_zones: Optional[int] = None
    
    vacuum_pump_capacity: str = ""
    vacuum_tank_size: str = ""
    
    power_supply: str = ""
    
    features: List[str] = field(default_factory=list)
    applications: List[str] = field(default_factory=list)
    
    source_file: str = ""
    source_page: Optional[int] = None
    extraction_confidence: float = 0.0
    extracted_at: str = ""
    raw_text_snippet: str = ""
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass 
class ExtractionResult:
    """Result of processing a single document."""
    file_path: str
    file_hash: str
    machines_found: List[ExtractedMachineSpec]
    processing_time_seconds: float
    success: bool
    error_message: str = ""


class DatabasePopulator:
    """
    Extracts structured machine specifications from PDF documents.
    
    Uses LLM to identify and extract:
    - Model numbers and series identification
    - Technical specifications (dimensions, power, vacuum)
    - Pricing information
    - Features and applications
    """
    
    EXTRACTION_SCHEMA = """
Extract machine specifications from this document. Return a JSON array of machines.

For EACH machine found, extract:
{
    "model": "exact model number (e.g., PF1-C-2015, IMG-1350)",
    "series": "series name (PF1, AM, IMG, FCS, etc.)",
    "variant": "variant if applicable (e.g., 'X (all-servo)', 'C (pneumatic)')",
    "price_inr": integer price in INR or null,
    "price_usd": integer price in USD or null,
    "forming_area_mm": "width x height (e.g., '2000 x 1500')",
    "max_tool_height_mm": integer in mm or null,
    "max_draw_depth_mm": integer in mm or null,
    "max_sheet_thickness_mm": float in mm or null,
    "min_sheet_thickness_mm": float in mm or null,
    "heater_power_kw": float in kW or null,
    "heater_type": "type description (e.g., 'IR Quartz', 'IR Ceramic')",
    "num_heaters": integer count or null,
    "heater_zones": integer count or null,
    "vacuum_pump_capacity": "capacity string (e.g., '220 m³/hr')",
    "vacuum_tank_size": "size string (e.g., '500L')",
    "power_supply": "power spec (e.g., '415V, 50Hz, 3P+N+PE')",
    "features": ["list", "of", "features"],
    "applications": ["list", "of", "applications"],
    "confidence": float 0.0-1.0 for extraction confidence
}

Rules:
1. Only extract data EXPLICITLY stated in the document - do not infer or estimate
2. Model numbers must match Machinecraft naming: PF1-X-XXXX, PF1-C-XXXX, AM-XXXX, IMG-XXXX, etc.
3. Convert all dimensions to mm (meters → mm)
4. Extract prices as integers (remove lakhs notation: 70.55L = 7055000)
5. If a spec is not clearly stated, use null - never guess
6. Confidence should reflect how clearly the data was stated

Return ONLY the JSON array, no other text.
"""
    
    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self._openai = None
        self._processed_hashes = self._load_processed_hashes()
    
    def _log(self, msg: str):
        if self.verbose:
            logger.info(f"[POPULATOR] {msg}")
    
    def _get_openai(self):
        if self._openai is None:
            try:
                from config import get_openai_client
                self._openai = get_openai_client()
            except ImportError:
                import openai
                self._openai = openai.OpenAI()
        return self._openai
    
    def _load_processed_hashes(self) -> Dict[str, str]:
        """Load previously processed file hashes."""
        if PROCESSED_HASHES_FILE.exists():
            try:
                return json.loads(PROCESSED_HASHES_FILE.read_text())
            except (json.JSONDecodeError, IOError):
                pass
        return {}
    
    def _save_processed_hashes(self):
        """Save processed file hashes."""
        PROCESSED_HASHES_FILE.parent.mkdir(parents=True, exist_ok=True)
        PROCESSED_HASHES_FILE.write_text(json.dumps(self._processed_hashes, indent=2))
    
    def _file_hash(self, file_path: Path) -> str:
        """Generate hash of file for deduplication."""
        hasher = hashlib.md5()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(65536), b''):
                hasher.update(chunk)
        return hasher.hexdigest()
    
    def _extract_text_from_pdf(self, pdf_path: Path) -> Tuple[str, List[Tuple[int, str]]]:
        """Extract text from PDF using shared DocumentExtractor, returns (full_text, [(page_num, page_text), ...])."""
        # Use shared document extractor (has fallback chain: PyMuPDF → pdfplumber → pypdf)
        try:
            from document_extractor import extract_pdf, get_extractor
            
            extractor = get_extractor()
            result = extractor.extract(pdf_path)
            
            if result.success:
                # Parse the extracted text to reconstruct page structure
                full_text = result.text
                page_texts = []
                
                # Split by page markers if present
                import re
                page_pattern = r'\[PAGE (\d+)\]\n(.*?)(?=\[PAGE \d+\]|$)'
                matches = re.findall(page_pattern, full_text, re.DOTALL)
                
                if matches:
                    page_texts = [(int(m[0]), m[1].strip()) for m in matches]
                else:
                    # No page markers, treat as single page
                    page_texts = [(1, full_text)]
                
                return full_text, page_texts
        except ImportError:
            logger.warning("document_extractor not available, falling back to pdfplumber")
        except Exception as e:
            logger.warning(f"Shared extractor failed: {e}, falling back to pdfplumber")
        
        # Fallback to direct pdfplumber
        try:
            import pdfplumber
        except ImportError:
            logger.error("pdfplumber not installed. Run: pip install pdfplumber")
            return "", []
        
        full_text = ""
        page_texts = []
        
        try:
            with pdfplumber.open(str(pdf_path)) as pdf:
                for i, page in enumerate(pdf.pages[:30]):  # Limit to 30 pages
                    text = page.extract_text() or ""
                    full_text += f"\n--- Page {i+1} ---\n{text}"
                    page_texts.append((i + 1, text))
        except Exception as e:
            logger.error(f"PDF extraction error for {pdf_path.name}: {e}")
        
        return full_text, page_texts
    
    def _extract_specs_with_llm(self, text: str, source_file: str) -> List[ExtractedMachineSpec]:
        """Use LLM to extract structured specs from document text."""
        if len(text) < 100:
            return []
        
        text_truncated = text[:15000]
        
        prompt = f"""{self.EXTRACTION_SCHEMA}

DOCUMENT TEXT:
{text_truncated}

SOURCE FILE: {source_file}

Remember: Only extract explicitly stated data. Return valid JSON array."""
        
        try:
            client = self._get_openai()
            response = client.chat.completions.create(
                model="gpt-4.1",
                messages=[
                    {"role": "system", "content": "You are a technical specification extractor. Extract machine specs from documents with high precision. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=4000,
                temperature=0.1
            )
            
            result_text = response.choices[0].message.content.strip()
            
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0]
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0]
            
            data = json.loads(result_text)
            
            if not isinstance(data, list):
                data = [data]
            
            specs = []
            for item in data:
                if not item.get("model"):
                    continue
                
                spec = ExtractedMachineSpec(
                    model=item.get("model", "").upper(),
                    series=item.get("series", ""),
                    variant=item.get("variant", ""),
                    price_inr=item.get("price_inr"),
                    price_usd=item.get("price_usd"),
                    forming_area_mm=item.get("forming_area_mm", ""),
                    max_tool_height_mm=item.get("max_tool_height_mm"),
                    max_draw_depth_mm=item.get("max_draw_depth_mm"),
                    max_sheet_thickness_mm=item.get("max_sheet_thickness_mm"),
                    min_sheet_thickness_mm=item.get("min_sheet_thickness_mm"),
                    heater_power_kw=item.get("heater_power_kw"),
                    heater_type=item.get("heater_type", ""),
                    num_heaters=item.get("num_heaters"),
                    heater_zones=item.get("heater_zones"),
                    vacuum_pump_capacity=item.get("vacuum_pump_capacity", ""),
                    vacuum_tank_size=item.get("vacuum_tank_size", ""),
                    power_supply=item.get("power_supply", ""),
                    features=item.get("features", []),
                    applications=item.get("applications", []),
                    source_file=source_file,
                    extraction_confidence=item.get("confidence", 0.7),
                    extracted_at=datetime.now().isoformat(),
                )
                specs.append(spec)
            
            return specs
            
        except json.JSONDecodeError as e:
            logger.warning(f"JSON parse error: {e}")
            return []
        except Exception as e:
            logger.error(f"LLM extraction error: {e}")
            return []
    
    def process_pdf(self, pdf_path: Path, force: bool = False) -> ExtractionResult:
        """
        Process a single PDF file and extract machine specifications.
        
        Args:
            pdf_path: Path to the PDF file
            force: If True, process even if previously processed
        
        Returns:
            ExtractionResult with extracted machines
        """
        import time
        start_time = time.time()
        
        file_hash = self._file_hash(pdf_path)
        
        if not force and file_hash in self._processed_hashes:
            self._log(f"Skipping (already processed): {pdf_path.name}")
            return ExtractionResult(
                file_path=str(pdf_path),
                file_hash=file_hash,
                machines_found=[],
                processing_time_seconds=0,
                success=True,
                error_message="Already processed"
            )
        
        self._log(f"Processing: {pdf_path.name}")
        
        full_text, page_texts = self._extract_text_from_pdf(pdf_path)
        
        if not full_text.strip():
            return ExtractionResult(
                file_path=str(pdf_path),
                file_hash=file_hash,
                machines_found=[],
                processing_time_seconds=time.time() - start_time,
                success=False,
                error_message="Could not extract text from PDF"
            )
        
        machines = self._extract_specs_with_llm(full_text, pdf_path.name)
        
        self._processed_hashes[file_hash] = pdf_path.name
        
        elapsed = time.time() - start_time
        self._log(f"  Found {len(machines)} machines in {elapsed:.1f}s")
        
        return ExtractionResult(
            file_path=str(pdf_path),
            file_hash=file_hash,
            machines_found=machines,
            processing_time_seconds=elapsed,
            success=True
        )
    
    def scan_directory(self, directory: Path = None, force: bool = False) -> List[ExtractionResult]:
        """
        Scan a directory for PDFs and extract machine specifications.
        
        Args:
            directory: Directory to scan (defaults to data/imports)
            force: If True, reprocess all files
        
        Returns:
            List of ExtractionResults
        """
        if directory is None:
            directory = IMPORTS_DIR
        
        directory = Path(directory)
        
        if not directory.exists():
            logger.error(f"Directory not found: {directory}")
            return []
        
        pdf_files = list(directory.glob("**/*.pdf"))
        self._log(f"Found {len(pdf_files)} PDF files in {directory}")
        
        results = []
        for pdf_path in pdf_files:
            if pdf_path.name.startswith(".") or pdf_path.name.startswith("~"):
                continue
            
            result = self.process_pdf(pdf_path, force=force)
            results.append(result)
        
        self._save_processed_hashes()
        
        return results
    
    def save_extractions(self, results: List[ExtractionResult]) -> Dict[str, Any]:
        """
        Save extracted specifications to JSON for review.
        
        Returns summary statistics.
        """
        all_machines = []
        for result in results:
            for machine in result.machines_found:
                all_machines.append(machine.to_dict())
        
        EXTRACTED_SPECS_FILE.parent.mkdir(parents=True, exist_ok=True)
        
        extraction_data = {
            "extracted_at": datetime.now().isoformat(),
            "total_machines": len(all_machines),
            "source_files": len(results),
            "machines": all_machines
        }
        
        EXTRACTED_SPECS_FILE.write_text(json.dumps(extraction_data, indent=2, default=str))
        self._log(f"Saved {len(all_machines)} machine specs to {EXTRACTED_SPECS_FILE}")
        
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "files_processed": len(results),
            "machines_extracted": len(all_machines),
            "successful_files": sum(1 for r in results if r.success),
            "models_found": list(set(m["model"] for m in all_machines)),
        }
        
        log_data = []
        if EXTRACTION_LOG_FILE.exists():
            try:
                log_data = json.loads(EXTRACTION_LOG_FILE.read_text())
            except (json.JSONDecodeError, IOError):
                pass
        log_data.append(log_entry)
        EXTRACTION_LOG_FILE.write_text(json.dumps(log_data[-100:], indent=2))
        
        return {
            "total_machines": len(all_machines),
            "source_files": len(results),
            "models": list(set(m["model"] for m in all_machines)),
            "specs_with_vacuum": sum(1 for m in all_machines if m.get("vacuum_pump_capacity")),
            "specs_with_heater_type": sum(1 for m in all_machines if m.get("heater_type")),
            "specs_with_features": sum(1 for m in all_machines if m.get("features")),
            "specs_with_price": sum(1 for m in all_machines if m.get("price_inr")),
        }
    
    def merge_into_database(self, dry_run: bool = True) -> Dict[str, Any]:
        """
        Merge extracted specifications into the machine database.
        
        Args:
            dry_run: If True, only report what would change (don't modify)
        
        Returns:
            Summary of changes made or proposed
        """
        if not EXTRACTED_SPECS_FILE.exists():
            return {"error": "No extractions found. Run scan_directory first."}
        
        extractions = json.loads(EXTRACTED_SPECS_FILE.read_text())
        machines = extractions.get("machines", [])
        
        try:
            from machine_database import MACHINE_SPECS, MachineSpec
        except ImportError:
            return {"error": "Could not import machine_database"}
        
        updates = []
        new_machines = []
        
        for extracted in machines:
            model = extracted.get("model", "").upper()
            if not model:
                continue
            
            if model in MACHINE_SPECS:
                existing = MACHINE_SPECS[model]
                changes = []
                
                if extracted.get("vacuum_pump_capacity") and not existing.vacuum_pump_capacity:
                    changes.append(f"vacuum_pump_capacity: → {extracted['vacuum_pump_capacity']}")
                
                if extracted.get("heater_type") and not existing.heater_type:
                    changes.append(f"heater_type: → {extracted['heater_type']}")
                
                if extracted.get("features") and not existing.features:
                    changes.append(f"features: → {extracted['features'][:3]}...")
                
                if extracted.get("price_inr") and not existing.price_inr:
                    changes.append(f"price_inr: → ₹{extracted['price_inr']:,}")
                
                if changes:
                    updates.append({
                        "model": model,
                        "changes": changes,
                        "source": extracted.get("source_file", "unknown")
                    })
                    
                    if not dry_run:
                        if extracted.get("vacuum_pump_capacity") and not existing.vacuum_pump_capacity:
                            existing.vacuum_pump_capacity = extracted["vacuum_pump_capacity"]
                        if extracted.get("heater_type") and not existing.heater_type:
                            existing.heater_type = extracted["heater_type"]
                        if extracted.get("features") and not existing.features:
                            existing.features = extracted["features"]
                        if extracted.get("price_inr") and not existing.price_inr:
                            existing.price_inr = extracted["price_inr"]
            else:
                if extracted.get("extraction_confidence", 0) >= 0.7:
                    new_machines.append({
                        "model": model,
                        "source": extracted.get("source_file", "unknown"),
                        "confidence": extracted.get("extraction_confidence", 0)
                    })
        
        return {
            "mode": "dry_run" if dry_run else "applied",
            "existing_updated": len(updates),
            "updates": updates[:20],
            "new_machines_found": len(new_machines),
            "new_machines": new_machines[:10],
        }


def populate_from_pdfs(
    pdf_directory: str = None,
    force: bool = False,
    merge: bool = False
) -> Dict[str, Any]:
    """
    Convenience function to populate database from PDF documents.
    
    Args:
        pdf_directory: Directory containing PDFs (defaults to data/imports)
        force: If True, reprocess all files even if previously processed
        merge: If True, merge extractions into database (use with caution)
    
    Returns:
        Summary statistics and extraction results
    
    Example:
        result = populate_from_pdfs()
        print(f"Found {result['total_machines']} machines from {result['source_files']} files")
    """
    populator = DatabasePopulator(verbose=True)
    
    directory = Path(pdf_directory) if pdf_directory else IMPORTS_DIR
    
    results = populator.scan_directory(directory, force=force)
    
    summary = populator.save_extractions(results)
    
    if merge:
        merge_result = populator.merge_into_database(dry_run=False)
        summary["merge_result"] = merge_result
    else:
        preview = populator.merge_into_database(dry_run=True)
        summary["merge_preview"] = preview
    
    return summary


def get_extraction_stats() -> Dict[str, Any]:
    """Get statistics about current extractions and database coverage."""
    stats = {
        "extraction_file_exists": EXTRACTED_SPECS_FILE.exists(),
        "processed_files": 0,
        "extracted_machines": 0,
    }
    
    if EXTRACTED_SPECS_FILE.exists():
        data = json.loads(EXTRACTED_SPECS_FILE.read_text())
        stats["extracted_machines"] = data.get("total_machines", 0)
        stats["extraction_date"] = data.get("extracted_at", "unknown")
        stats["models_extracted"] = list(set(m.get("model", "") for m in data.get("machines", [])))
    
    if PROCESSED_HASHES_FILE.exists():
        hashes = json.loads(PROCESSED_HASHES_FILE.read_text())
        stats["processed_files"] = len(hashes)
    
    try:
        from machine_database import MACHINE_SPECS
        total = len(MACHINE_SPECS)
        with_vacuum = sum(1 for s in MACHINE_SPECS.values() if s.vacuum_pump_capacity)
        with_heater = sum(1 for s in MACHINE_SPECS.values() if s.heater_type)
        with_features = sum(1 for s in MACHINE_SPECS.values() if s.features)
        
        stats["database_coverage"] = {
            "total_machines": total,
            "with_vacuum_specs": with_vacuum,
            "vacuum_coverage_pct": round(with_vacuum / total * 100, 1) if total else 0,
            "with_heater_type": with_heater,
            "heater_coverage_pct": round(with_heater / total * 100, 1) if total else 0,
            "with_features": with_features,
            "features_coverage_pct": round(with_features / total * 100, 1) if total else 0,
        }
    except ImportError:
        pass
    
    return stats


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Database Populator - Extract specs from PDFs")
    parser.add_argument("--scan", action="store_true", help="Scan PDFs and extract specs")
    parser.add_argument("--force", action="store_true", help="Force reprocess all files")
    parser.add_argument("--merge", action="store_true", help="Merge into database (careful!)")
    parser.add_argument("--stats", action="store_true", help="Show extraction statistics")
    parser.add_argument("--dir", type=str, help="Directory to scan (default: data/imports)")
    
    args = parser.parse_args()
    
    if args.stats:
        stats = get_extraction_stats()
        print("\n" + "=" * 60)
        print("DATABASE POPULATION STATISTICS")
        print("=" * 60)
        print(json.dumps(stats, indent=2))
    
    elif args.scan:
        result = populate_from_pdfs(
            pdf_directory=args.dir,
            force=args.force,
            merge=args.merge
        )
        print("\n" + "=" * 60)
        print("EXTRACTION COMPLETE")
        print("=" * 60)
        print(json.dumps(result, indent=2, default=str))
    
    else:
        parser.print_help()
