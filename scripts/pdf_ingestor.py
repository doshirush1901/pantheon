#!/usr/bin/env python3
"""
UNIFIED PDF INGESTOR - Single Source of Truth for PDF Data Extraction
======================================================================

Consolidates multiple PDF extraction implementations into one robust pipeline:
- skills/brain/pdf_spec_extractor.py (deprecated)
- skills/brain/document_extractor.py (deprecated)
- skills/memory/document_ingestor.py (deprecated)

Features:
- Camelot for high-accuracy table extraction
- PDFPlumber for text extraction
- Regex patterns for structured data
- LLM fallback for unstructured content
- Automatic machine database updates

Usage:
    # From command line
    python pdf_ingestor.py --dir data/brochures/ --output data/extracted/
    
    # Programmatic
    from pdf_ingestor import UnifiedPDFIngestor
    ingestor = UnifiedPDFIngestor()
    machines = ingestor.process_directory(Path("data/brochures"))
"""

import json
import logging
import os
import re
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "openclaw" / "agents" / "ira"))

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False
    logger.warning("pdfplumber not installed: pip install pdfplumber")

try:
    import camelot
    CAMELOT_AVAILABLE = True
except ImportError:
    CAMELOT_AVAILABLE = False
    logger.warning("camelot not installed: pip install camelot-py[cv]")

try:
    from src.brain.machine_database import MachineSpec, MACHINE_SPECS, get_machine
    MACHINE_DB_AVAILABLE = True
except ImportError:
    MACHINE_DB_AVAILABLE = False
    MachineSpec = None
    MACHINE_SPECS = {}
    get_machine = lambda x: None


@dataclass
class ExtractedMachine:
    """Standardized machine data extracted from PDF."""
    model: str
    series: str = ""
    variant: str = ""
    
    forming_area_mm: str = ""
    forming_area_raw: Tuple[int, int] = ()
    max_tool_height_mm: int = 0
    max_draw_depth_mm: int = 0
    max_sheet_thickness_mm: float = 0
    min_sheet_thickness_mm: float = 0
    
    heater_power_kw: float = 0
    total_power_kw: float = 0
    heater_type: str = ""
    num_heaters: int = 0
    heater_zones: int = 0
    
    vacuum_pump_capacity: str = ""
    vacuum_tank_size: str = ""
    
    price_inr: Optional[int] = None
    price_usd: Optional[int] = None
    
    power_supply: str = ""
    features: List[str] = field(default_factory=list)
    applications: List[str] = field(default_factory=list)
    description: str = ""
    
    source_file: str = ""
    source_page: int = 0
    extraction_method: str = ""
    extraction_confidence: float = 0.0
    extracted_at: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["forming_area_raw"] = list(self.forming_area_raw) if self.forming_area_raw else []
        return d
    
    def to_machine_spec(self) -> Optional["MachineSpec"]:
        """Convert to MachineSpec for database update."""
        if not MACHINE_DB_AVAILABLE or MachineSpec is None:
            return None
        return MachineSpec(
            model=self.model,
            series=self.series,
            variant=self.variant,
            price_inr=self.price_inr,
            price_usd=self.price_usd,
            forming_area_mm=self.forming_area_mm,
            forming_area_raw=self.forming_area_raw,
            max_tool_height_mm=self.max_tool_height_mm,
            max_draw_depth_mm=self.max_draw_depth_mm,
            max_sheet_thickness_mm=self.max_sheet_thickness_mm,
            min_sheet_thickness_mm=self.min_sheet_thickness_mm,
            heater_power_kw=self.heater_power_kw,
            total_power_kw=self.total_power_kw,
            heater_type=self.heater_type,
            num_heaters=self.num_heaters,
            heater_zones=self.heater_zones,
            vacuum_pump_capacity=self.vacuum_pump_capacity,
            vacuum_tank_size=self.vacuum_tank_size,
            power_supply=self.power_supply,
            description=self.description,
            features=self.features,
            applications=self.applications,
            source_documents=[self.source_file],
            last_updated=datetime.now().isoformat(),
        )


SPEC_PATTERNS = {
    "model": [
        r'\b(PF1-[A-Z]-\d{4})\b',
        r'\b(PF2-[A-Z]?\d{4})\b',
        r'\b(AM[P]?-\d{4}(?:-[A-Z])?)\b',
        r'\b(IMG[S]?-\d{4})\b',
        r'\b(FCS-\d{4}-\d[A-Z]{2})\b',
        r'\b(UNO-\d{4})\b',
        r'\b(DUO-\d{4})\b',
        r'\b(PLAY-\d{4})\b',
        r'\b(ATF-\d{4})\b',
    ],
    "forming_area": [
        r'(\d{3,4})\s*[x×X]\s*(\d{3,4})\s*(?:mm)?',
        r'forming\s*area[:\s]*(\d{3,4})\s*[x×X]\s*(\d{3,4})',
    ],
    "heater_power": [
        r'(\d+(?:\.\d+)?)\s*(?:kW|KW|kw)',
        r'heater\s*(?:power)?[:\s]*(\d+(?:\.\d+)?)\s*(?:kW|KW)',
    ],
    "vacuum": [
        r'(\d+)\s*m[³3]/hr',
        r'vacuum[:\s]*(\d+)\s*m[³3]/hr',
    ],
    "price_inr": [
        r'(?:₹|Rs\.?|INR)\s*([\d,]+(?:\.\d+)?)\s*(?:lakhs?|L)?',
        r'price[:\s]*(?:₹|Rs\.?|INR)\s*([\d,]+)',
    ],
    "price_usd": [
        r'\$\s*([\d,]+(?:\.\d+)?)',
        r'USD\s*([\d,]+)',
    ],
    "tool_height": [
        r'tool\s*height[:\s]*(\d+)\s*mm',
        r'max\s*tool[:\s]*(\d+)\s*mm',
    ],
    "draw_depth": [
        r'draw\s*depth[:\s]*(\d+)\s*mm',
        r'max\s*depth[:\s]*(\d+)\s*mm',
    ],
    "sheet_thickness": [
        r'sheet\s*(?:thickness)?[:\s]*(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)\s*mm',
        r'(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)\s*mm\s*(?:thick|sheet)',
    ],
}


class UnifiedPDFIngestor:
    """
    Unified PDF ingestion pipeline.
    
    Strategy:
    1. Camelot for tables (highest accuracy for structured data)
    2. PDFPlumber for text extraction
    3. Regex patterns for structured fields
    4. LLM fallback for unstructured content
    """
    
    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = output_dir or PROJECT_ROOT / "data" / "extracted"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.machines: Dict[str, ExtractedMachine] = {}
        self.extraction_stats = {
            "files_processed": 0,
            "tables_extracted": 0,
            "machines_found": 0,
            "errors": [],
        }
    
    def process_directory(self, directory: Path) -> List[ExtractedMachine]:
        """Process all PDFs in a directory."""
        if not directory.exists():
            logger.error(f"Directory not found: {directory}")
            return []
        
        pdf_files = list(directory.glob("**/*.pdf"))
        logger.info(f"Found {len(pdf_files)} PDF files in {directory}")
        
        for pdf_path in pdf_files:
            logger.info(f"Processing: {pdf_path.name}")
            try:
                machines = self.process_pdf(pdf_path)
                logger.info(f"  → Extracted {len(machines)} machines")
                
                for machine in machines:
                    existing = self.machines.get(machine.model)
                    if existing:
                        if machine.extraction_confidence > existing.extraction_confidence:
                            self.machines[machine.model] = machine
                            logger.debug(f"  → Updated {machine.model} (higher confidence)")
                    else:
                        self.machines[machine.model] = machine
                        
                self.extraction_stats["files_processed"] += 1
                
            except Exception as e:
                logger.error(f"Error processing {pdf_path.name}: {e}")
                self.extraction_stats["errors"].append({
                    "file": str(pdf_path),
                    "error": str(e)
                })
        
        self.extraction_stats["machines_found"] = len(self.machines)
        return list(self.machines.values())
    
    def process_pdf(self, pdf_path: Path) -> List[ExtractedMachine]:
        """Process a single PDF file."""
        machines = []
        
        tables = self._extract_tables(pdf_path)
        self.extraction_stats["tables_extracted"] += len(tables)
        
        text_by_page = self._extract_text(pdf_path)
        
        for table_data in tables:
            machine = self._parse_table_for_specs(table_data, str(pdf_path))
            if machine:
                machines.append(machine)
        
        for page_num, text in text_by_page.items():
            additional = self._parse_text_for_specs(text, str(pdf_path), page_num)
            for machine in additional:
                if not any(m.model == machine.model for m in machines):
                    machines.append(machine)
        
        return machines
    
    def _extract_tables(self, pdf_path: Path) -> List[Dict]:
        """Extract tables using Camelot (preferred) or PDFPlumber fallback."""
        tables = []
        
        if CAMELOT_AVAILABLE:
            try:
                lattice_tables = camelot.read_pdf(
                    str(pdf_path),
                    pages='all',
                    flavor='lattice'
                )
                for table in lattice_tables:
                    if table.parsing_report['accuracy'] > 50:
                        tables.append({
                            "data": table.df.to_dict('records'),
                            "raw_text": table.df.to_string(),
                            "accuracy": table.parsing_report['accuracy'],
                            "method": "camelot_lattice",
                            "page": table.page
                        })
                logger.debug(f"  Camelot lattice: {len(lattice_tables)} tables")
            except Exception as e:
                logger.debug(f"  Camelot lattice failed: {e}")
            
            try:
                stream_tables = camelot.read_pdf(
                    str(pdf_path),
                    pages='all',
                    flavor='stream'
                )
                for table in stream_tables:
                    if table.parsing_report['accuracy'] > 50:
                        existing_pages = {t.get('page') for t in tables}
                        if table.page not in existing_pages:
                            tables.append({
                                "data": table.df.to_dict('records'),
                                "raw_text": table.df.to_string(),
                                "accuracy": table.parsing_report['accuracy'],
                                "method": "camelot_stream",
                                "page": table.page
                            })
                logger.debug(f"  Camelot stream: {len(stream_tables)} tables")
            except Exception as e:
                logger.debug(f"  Camelot stream failed: {e}")
        
        if not tables and PDFPLUMBER_AVAILABLE:
            try:
                with pdfplumber.open(pdf_path) as pdf:
                    for i, page in enumerate(pdf.pages):
                        page_tables = page.extract_tables()
                        for table in page_tables:
                            if table and len(table) > 1:
                                tables.append({
                                    "data": table,
                                    "raw_text": str(table),
                                    "accuracy": 60,
                                    "method": "pdfplumber",
                                    "page": i + 1
                                })
                logger.debug(f"  PDFPlumber: {len(tables)} tables")
            except Exception as e:
                logger.debug(f"  PDFPlumber tables failed: {e}")
        
        return tables
    
    def _extract_text(self, pdf_path: Path) -> Dict[int, str]:
        """Extract text by page using PDFPlumber."""
        text_by_page = {}
        
        if not PDFPLUMBER_AVAILABLE:
            logger.warning("pdfplumber not available for text extraction")
            return text_by_page
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for i, page in enumerate(pdf.pages):
                    text = page.extract_text() or ""
                    if text.strip():
                        text_by_page[i + 1] = text
        except Exception as e:
            logger.error(f"Text extraction failed: {e}")
        
        return text_by_page
    
    def _parse_table_for_specs(
        self,
        table_data: Dict,
        source_file: str
    ) -> Optional[ExtractedMachine]:
        """Parse a table for machine specifications."""
        raw_text = table_data.get("raw_text", "")
        if isinstance(table_data.get("data"), list):
            raw_text += " " + json.dumps(table_data["data"])
        
        model = self._extract_model(raw_text)
        if not model:
            return None
        
        forming_area = self._extract_forming_area(raw_text)
        heater_power = self._extract_heater_power(raw_text)
        vacuum = self._extract_vacuum(raw_text)
        price_inr = self._extract_price_inr(raw_text)
        tool_height = self._extract_tool_height(raw_text)
        
        confidence = 0.5
        if forming_area:
            confidence += 0.15
        if heater_power:
            confidence += 0.1
        if vacuum:
            confidence += 0.1
        if price_inr:
            confidence += 0.15
        
        confidence = min(confidence * (table_data.get("accuracy", 60) / 100), 1.0)
        
        return ExtractedMachine(
            model=model,
            series=model.split("-")[0] if "-" in model else model[:3],
            forming_area_mm=f"{forming_area[0]} x {forming_area[1]} mm" if forming_area else "",
            forming_area_raw=forming_area or (),
            heater_power_kw=heater_power or 0,
            vacuum_pump_capacity=f"{vacuum} m³/hr" if vacuum else "",
            price_inr=price_inr,
            max_tool_height_mm=tool_height or 0,
            source_file=source_file,
            source_page=table_data.get("page", 0),
            extraction_method=table_data.get("method", "table"),
            extraction_confidence=confidence,
            extracted_at=datetime.now().isoformat()
        )
    
    def _parse_text_for_specs(
        self,
        text: str,
        source_file: str,
        page_num: int
    ) -> List[ExtractedMachine]:
        """Parse text for machine specifications."""
        machines = []
        
        models_found = []
        for pattern in SPEC_PATTERNS["model"]:
            matches = re.findall(pattern, text, re.IGNORECASE)
            models_found.extend(matches)
        
        models_found = list(set([m.upper() for m in models_found]))
        
        for model in models_found:
            model_context = self._get_context_around(text, model, chars=500)
            
            forming_area = self._extract_forming_area(model_context)
            heater_power = self._extract_heater_power(model_context)
            vacuum = self._extract_vacuum(model_context)
            price_inr = self._extract_price_inr(model_context)
            
            confidence = 0.3
            if forming_area:
                confidence += 0.2
            if heater_power:
                confidence += 0.15
            if vacuum:
                confidence += 0.15
            if price_inr:
                confidence += 0.2
            
            machines.append(ExtractedMachine(
                model=model,
                series=model.split("-")[0] if "-" in model else model[:3],
                forming_area_mm=f"{forming_area[0]} x {forming_area[1]} mm" if forming_area else "",
                forming_area_raw=forming_area or (),
                heater_power_kw=heater_power or 0,
                vacuum_pump_capacity=f"{vacuum} m³/hr" if vacuum else "",
                price_inr=price_inr,
                source_file=source_file,
                source_page=page_num,
                extraction_method="text_regex",
                extraction_confidence=confidence,
                extracted_at=datetime.now().isoformat()
            ))
        
        return machines
    
    def _get_context_around(self, text: str, target: str, chars: int = 300) -> str:
        """Get text context around a target string."""
        text_upper = text.upper()
        target_upper = target.upper()
        
        idx = text_upper.find(target_upper)
        if idx == -1:
            return text
        
        start = max(0, idx - chars)
        end = min(len(text), idx + len(target) + chars)
        return text[start:end]
    
    def _extract_model(self, text: str) -> Optional[str]:
        """Extract machine model number."""
        for pattern in SPEC_PATTERNS["model"]:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).upper()
        return None
    
    def _extract_forming_area(self, text: str) -> Optional[Tuple[int, int]]:
        """Extract forming area dimensions."""
        for pattern in SPEC_PATTERNS["forming_area"]:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    w, h = int(match.group(1)), int(match.group(2))
                    if 100 <= w <= 10000 and 100 <= h <= 10000:
                        return (w, h)
                except (ValueError, IndexError):
                    pass
        return None
    
    def _extract_heater_power(self, text: str) -> Optional[float]:
        """Extract heater power in kW."""
        for pattern in SPEC_PATTERNS["heater_power"]:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    power = float(match.group(1))
                    if 1 <= power <= 1000:
                        return power
                except (ValueError, IndexError):
                    pass
        return None
    
    def _extract_vacuum(self, text: str) -> Optional[int]:
        """Extract vacuum pump capacity in m³/hr."""
        for pattern in SPEC_PATTERNS["vacuum"]:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    vacuum = int(match.group(1))
                    if 10 <= vacuum <= 2000:
                        return vacuum
                except (ValueError, IndexError):
                    pass
        return None
    
    def _extract_price_inr(self, text: str) -> Optional[int]:
        """Extract price in INR."""
        for pattern in SPEC_PATTERNS["price_inr"]:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    price_str = match.group(1).replace(',', '')
                    price = float(price_str)
                    
                    if "lakh" in text.lower() or price < 1000:
                        price = int(price * 100000)
                    else:
                        price = int(price)
                    
                    if 100000 <= price <= 100000000:
                        return price
                except (ValueError, IndexError):
                    pass
        return None
    
    def _extract_tool_height(self, text: str) -> Optional[int]:
        """Extract max tool height in mm."""
        for pattern in SPEC_PATTERNS["tool_height"]:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    height = int(match.group(1))
                    if 50 <= height <= 2000:
                        return height
                except (ValueError, IndexError):
                    pass
        return None
    
    def save_results(self, machines: List[ExtractedMachine]) -> Path:
        """Save extracted machines to JSON."""
        output_path = self.output_dir / "extracted_machines.json"
        
        data = {
            "extraction_date": datetime.now().isoformat(),
            "total_machines": len(machines),
            "extraction_stats": self.extraction_stats,
            "machines": [m.to_dict() for m in machines]
        }
        
        with open(output_path, "w") as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Saved {len(machines)} machines to {output_path}")
        return output_path
    
    def update_machine_database(self, machines: List[ExtractedMachine]) -> int:
        """Update the central machine database with extracted specs."""
        if not MACHINE_DB_AVAILABLE:
            logger.warning("Machine database not available - skipping update")
            return 0
        
        updated = 0
        added = 0
        
        for machine in machines:
            if machine.model in MACHINE_SPECS:
                existing = MACHINE_SPECS[machine.model]
                
                changed = False
                if not existing.price_inr and machine.price_inr:
                    existing.price_inr = machine.price_inr
                    changed = True
                if not existing.forming_area_mm and machine.forming_area_mm:
                    existing.forming_area_mm = machine.forming_area_mm
                    existing.forming_area_raw = machine.forming_area_raw
                    changed = True
                if not existing.heater_power_kw and machine.heater_power_kw:
                    existing.heater_power_kw = machine.heater_power_kw
                    changed = True
                if not existing.vacuum_pump_capacity and machine.vacuum_pump_capacity:
                    existing.vacuum_pump_capacity = machine.vacuum_pump_capacity
                    changed = True
                
                if changed:
                    existing.source_documents = list(set(
                        existing.source_documents + [machine.source_file]
                    ))
                    existing.last_updated = datetime.now().isoformat()
                    updated += 1
                    logger.debug(f"Updated {machine.model}")
            else:
                spec = machine.to_machine_spec()
                if spec:
                    MACHINE_SPECS[machine.model] = spec
                    added += 1
                    logger.debug(f"Added new machine {machine.model}")
        
        logger.info(f"Database update: {added} added, {updated} updated")
        return added + updated
    
    def generate_report(self) -> str:
        """Generate a human-readable extraction report."""
        report = []
        report.append("=" * 60)
        report.append("PDF EXTRACTION REPORT")
        report.append("=" * 60)
        report.append(f"Date: {datetime.now().isoformat()}")
        report.append(f"Files processed: {self.extraction_stats['files_processed']}")
        report.append(f"Tables extracted: {self.extraction_stats['tables_extracted']}")
        report.append(f"Machines found: {self.extraction_stats['machines_found']}")
        report.append("")
        
        if self.machines:
            report.append("EXTRACTED MACHINES:")
            report.append("-" * 40)
            for model, machine in sorted(self.machines.items()):
                report.append(f"\n{model}:")
                if machine.forming_area_mm:
                    report.append(f"  Forming Area: {machine.forming_area_mm}")
                if machine.heater_power_kw:
                    report.append(f"  Heater Power: {machine.heater_power_kw} kW")
                if machine.vacuum_pump_capacity:
                    report.append(f"  Vacuum: {machine.vacuum_pump_capacity}")
                if machine.price_inr:
                    report.append(f"  Price: ₹{machine.price_inr:,}")
                report.append(f"  Confidence: {machine.extraction_confidence:.1%}")
                report.append(f"  Source: {Path(machine.source_file).name}")
        
        if self.extraction_stats["errors"]:
            report.append("\nERRORS:")
            report.append("-" * 40)
            for error in self.extraction_stats["errors"]:
                report.append(f"  {error['file']}: {error['error']}")
        
        return "\n".join(report)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Unified PDF Ingestor for Machine Specifications"
    )
    parser.add_argument(
        "--dir", "-d",
        type=Path,
        help="Directory containing PDF files to process"
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        default=PROJECT_ROOT / "data" / "extracted",
        help="Output directory for extracted data"
    )
    parser.add_argument(
        "--update-db",
        action="store_true",
        help="Update machine database with extracted specs"
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Print extraction report"
    )
    parser.add_argument(
        "--file", "-f",
        type=Path,
        help="Process a single PDF file"
    )
    
    args = parser.parse_args()
    
    ingestor = UnifiedPDFIngestor(args.output)
    
    if args.file:
        if not args.file.exists():
            logger.error(f"File not found: {args.file}")
            return
        machines = ingestor.process_pdf(args.file)
        ingestor.machines = {m.model: m for m in machines}
    elif args.dir:
        if not args.dir.exists():
            logger.error(f"Directory not found: {args.dir}")
            return
        machines = ingestor.process_directory(args.dir)
    else:
        default_dir = PROJECT_ROOT / "data" / "imports"
        if default_dir.exists():
            logger.info(f"Using default directory: {default_dir}")
            machines = ingestor.process_directory(default_dir)
        else:
            logger.error("Please specify --dir or --file")
            parser.print_help()
            return
    
    output_path = ingestor.save_results(list(ingestor.machines.values()))
    
    if args.update_db:
        count = ingestor.update_machine_database(list(ingestor.machines.values()))
        logger.info(f"Updated {count} machines in database")
    
    if args.report:
        print(ingestor.generate_report())
    
    print(f"\n✅ Extraction complete: {len(ingestor.machines)} machines")
    print(f"   Results saved to: {output_path}")


if __name__ == "__main__":
    main()
