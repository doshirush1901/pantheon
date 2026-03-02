#!/usr/bin/env python3
"""
PDF Spec Extractor - Auto-extract machine specs from PDFs
==========================================================

Extracts machine specifications from PDF documents to fill database gaps.
Uses a combination of:
- Pattern matching for known spec formats
- Table extraction via pdfplumber
- LLM-based extraction for unstructured text

Usage:
    from pdf_spec_extractor import PDFSpecExtractor
    
    extractor = PDFSpecExtractor()
    specs = extractor.extract_from_pdf("path/to/machine_catalogue.pdf")
    extractor.update_database(specs)
"""

import json
import logging
import re
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Setup paths
BRAIN_DIR = Path(__file__).parent
SKILLS_DIR = BRAIN_DIR.parent
AGENT_DIR = SKILLS_DIR.parent
PROJECT_ROOT = BRAIN_DIR.parent.parent.parent.parent.parent.parent

sys.path.insert(0, str(AGENT_DIR))

try:
    from config import get_openai_client, get_logger, FAST_LLM_MODEL, append_jsonl
    CONFIG_AVAILABLE = True
    logger = get_logger(__name__)
except ImportError:
    CONFIG_AVAILABLE = False
    import logging as log_module
    logger = log_module.getLogger(__name__)
    FAST_LLM_MODEL = "gpt-4o-mini"

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False
    logger.warning("pdfplumber not installed - PDF extraction disabled")

# Import machine database for updating
try:
    from .machine_database import MachineSpec, MACHINE_SPECS, get_machine
except ImportError:
    try:
        from machine_database import MachineSpec, MACHINE_SPECS, get_machine
    except ImportError:
        MachineSpec = None
        MACHINE_SPECS = {}
        get_machine = lambda x: None


@dataclass
class ExtractedSpec:
    """A machine spec extracted from a PDF."""
    model: str
    series: str = ""
    variant: str = ""
    
    # Dimensions
    forming_area_mm: str = ""
    forming_area_raw: Tuple[int, int] = ()
    max_tool_height_mm: int = 0
    max_draw_depth_mm: int = 0
    max_sheet_thickness_mm: float = 0
    min_sheet_thickness_mm: float = 0
    
    # Power & Heating
    heater_power_kw: float = 0
    total_power_kw: float = 0
    heater_type: str = ""
    num_heaters: int = 0
    heater_zones: int = 0
    
    # Vacuum System
    vacuum_pump_capacity: str = ""
    vacuum_tank_size: str = ""
    
    # Pricing
    price_inr: Optional[int] = None
    price_usd: Optional[int] = None
    
    # Other
    power_supply: str = ""
    features: List[str] = field(default_factory=list)
    applications: List[str] = field(default_factory=list)
    description: str = ""
    
    # Metadata
    source_file: str = ""
    source_page: int = 0
    extraction_confidence: float = 0.0
    extraction_method: str = ""
    extracted_at: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    def to_machine_spec(self) -> Optional["MachineSpec"]:
        """Convert to MachineSpec for database update."""
        if not MachineSpec:
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


# Regex patterns for extracting specs
SPEC_PATTERNS = {
    "model": [
        r'\b(PF1-[A-Z]-\d{4})\b',
        r'\b(PF2-[A-Z]?\d{4})\b',
        r'\b(AM[P]?-\d{4}(?:-[A-Z])?)\b',
        r'\b(IMG[S]?-\d{4})\b',
        r'\b(FCS-\d{4}-\d[A-Z]{2})\b',
        r'\b(UNO-\d{4}(?:-2H)?)\b',
        r'\b(DUO-\d{4})\b',
        r'\b(PLAY-\d{4}(?:-DT)?)\b',
        r'\b(ATF-\d{4})\b',
    ],
    "forming_area": [
        r'(?:forming\s*(?:area|size))[:\s]*(\d{3,4})\s*[xX×]\s*(\d{3,4})\s*(?:mm)?',
        r'(\d{3,4})\s*[xX×]\s*(\d{3,4})\s*mm\s*(?:forming)?',
        r'(?:clamp\s*(?:area|size))[:\s]*(\d{3,4})\s*[xX×]\s*(\d{3,4})',
    ],
    "heater_power": [
        r'(?:heater\s*(?:power|capacity)|heating\s*(?:power|capacity))[:\s]*(\d+(?:\.\d+)?)\s*(?:kW|KW)',
        r'(\d+(?:\.\d+)?)\s*(?:kW|KW)\s*(?:heater|heating)',
        r'(?:installed\s*power|total\s*power)[:\s]*(\d+(?:\.\d+)?)\s*(?:kW|KW)',
    ],
    "vacuum_pump": [
        r'(?:vacuum\s*pump)[:\s]*(\d+)\s*(?:m³/hr|m3/hr|m³/h)',
        r'(\d+)\s*(?:m³/hr|m3/hr)\s*(?:vacuum)',
    ],
    "tool_height": [
        r'(?:tool\s*height|max\s*(?:tool\s*)?height)[:\s]*(\d+)\s*mm',
        r'(\d+)\s*mm\s*(?:max\s*)?(?:tool\s*)?height',
    ],
    "draw_depth": [
        r'(?:draw\s*depth|forming\s*depth|max\s*depth)[:\s]*(\d+)\s*mm',
        r'(\d+)\s*mm\s*(?:draw|forming)\s*depth',
    ],
    "sheet_thickness": [
        r'(?:sheet\s*thickness|material\s*thickness)[:\s]*(\d+(?:\.\d+)?)\s*[-–to]\s*(\d+(?:\.\d+)?)\s*mm',
        r'(\d+(?:\.\d+)?)\s*mm\s*(?:max\s*)?(?:sheet|material)',
    ],
    "price_inr": [
        r'(?:price|cost)[:\s]*(?:₹|Rs\.?|INR)\s*([\d,]+)',
        r'(?:₹|Rs\.?|INR)\s*([\d,]+)',
    ],
    "price_usd": [
        r'(?:price|cost)[:\s]*\$\s*([\d,]+)',
        r'\$\s*([\d,]+)\s*(?:USD)?',
    ],
}

# LLM prompt for extraction
EXTRACTION_PROMPT = """You are extracting machine specifications from a thermoforming/vacuum forming machine document.

Extract ALL machine specs you can find from this text. For each machine, extract:
- model: Model number (e.g., PF1-C-2015, AM-5060)
- series: Series name (PF1, AM, IMG, etc.)
- forming_area_mm: Forming area in mm (e.g., "2000 x 1500")
- heater_power_kw: Heater power in kW
- vacuum_pump_capacity: Vacuum pump capacity (e.g., "220 m³/hr")
- max_tool_height_mm: Maximum tool height in mm
- max_draw_depth_mm: Maximum draw depth in mm
- max_sheet_thickness_mm: Maximum sheet thickness in mm
- heater_type: Type of heater (IR Ceramic, IR Quartz, etc.)
- power_supply: Electrical supply requirements
- price_inr: Price in Indian Rupees (if mentioned)
- price_usd: Price in US Dollars (if mentioned)
- features: List of key features
- applications: List of typical applications

TEXT TO ANALYZE:
{text}

Return a JSON array of extracted specs. Only include fields that are explicitly stated in the text.
Be precise - don't guess or invent values. If a value isn't clearly stated, omit it.

Return format:
[
  {{
    "model": "PF1-C-2015",
    "series": "PF1",
    "forming_area_mm": "2000 x 1500",
    "heater_power_kw": 125,
    ...
  }}
]
"""


class PDFSpecExtractor:
    """
    Extracts machine specifications from PDF documents.
    
    Uses multiple extraction methods:
    1. Table extraction (for structured specs)
    2. Pattern matching (for known formats)
    3. LLM extraction (for unstructured text)
    """
    
    def __init__(self, use_llm: bool = True, model: str = None):
        """
        Initialize the extractor.
        
        Args:
            use_llm: Whether to use LLM for unstructured extraction
            model: LLM model to use (defaults to FAST_LLM_MODEL)
        """
        self.use_llm = use_llm
        self.model = model or FAST_LLM_MODEL
        self._client = None
        self._extraction_log_path = PROJECT_ROOT / "data" / "knowledge" / "spec_extraction_log.jsonl"
    
    @property
    def client(self):
        """Get OpenAI client lazily."""
        if self._client is None:
            if CONFIG_AVAILABLE:
                self._client = get_openai_client()
            else:
                try:
                    from openai import OpenAI
                    import os
                    self._client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
                except Exception:
                    self._client = None
        return self._client
    
    def extract_from_pdf(
        self,
        pdf_path: str,
        pages: Optional[List[int]] = None,
    ) -> List[ExtractedSpec]:
        """
        Extract machine specs from a PDF file.
        
        Args:
            pdf_path: Path to the PDF file
            pages: Specific pages to extract from (None = all pages)
        
        Returns:
            List of ExtractedSpec objects
        """
        if not PDFPLUMBER_AVAILABLE:
            logger.error("pdfplumber not available for PDF extraction")
            return []
        
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            logger.error(f"PDF file not found: {pdf_path}")
            return []
        
        all_specs = []
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                pages_to_process = pages if pages else range(len(pdf.pages))
                
                for page_num in pages_to_process:
                    if page_num >= len(pdf.pages):
                        continue
                    
                    page = pdf.pages[page_num]
                    
                    # Method 1: Extract from tables
                    table_specs = self._extract_from_tables(page, pdf_path.name, page_num)
                    all_specs.extend(table_specs)
                    
                    # Method 2: Extract from text using patterns
                    text = page.extract_text() or ""
                    pattern_specs = self._extract_from_text_patterns(text, pdf_path.name, page_num)
                    all_specs.extend(pattern_specs)
                    
                    # Method 3: LLM extraction for remaining text
                    if self.use_llm and self.client and text:
                        llm_specs = self._extract_with_llm(text, pdf_path.name, page_num)
                        all_specs.extend(llm_specs)
            
            # Deduplicate and merge specs
            all_specs = self._deduplicate_specs(all_specs)
            
            # Log extraction
            self._log_extraction(pdf_path.name, all_specs)
            
            return all_specs
            
        except Exception as e:
            logger.error(f"Failed to extract from {pdf_path}: {e}")
            return []
    
    def _extract_from_tables(
        self,
        page,
        filename: str,
        page_num: int,
    ) -> List[ExtractedSpec]:
        """Extract specs from tables on a page."""
        specs = []
        
        try:
            tables = page.extract_tables()
            
            for table in tables:
                if not table or len(table) < 2:
                    continue
                
                # Check if it's a spec table
                header = table[0] if table else []
                header_lower = [str(h).lower() if h else "" for h in header]
                
                # Look for spec-like columns
                is_spec_table = any(
                    col in " ".join(header_lower) 
                    for col in ["model", "forming", "heater", "vacuum", "power", "kw", "mm"]
                )
                
                if not is_spec_table:
                    continue
                
                # Parse table rows
                for row in table[1:]:
                    spec = self._parse_spec_row(header, row, filename, page_num)
                    if spec and spec.model:
                        spec.extraction_method = "table"
                        spec.extraction_confidence = 0.9
                        specs.append(spec)
        
        except Exception as e:
            logger.debug(f"Table extraction error: {e}")
        
        return specs
    
    def _parse_spec_row(
        self,
        header: List[str],
        row: List[str],
        filename: str,
        page_num: int,
    ) -> Optional[ExtractedSpec]:
        """Parse a single row from a spec table."""
        if not row or len(row) < 2:
            return None
        
        spec = ExtractedSpec(
            model="",
            source_file=filename,
            source_page=page_num,
            extracted_at=datetime.now().isoformat(),
        )
        
        header_map = {}
        for i, h in enumerate(header):
            if h:
                header_map[str(h).lower()] = i
        
        for col_name, idx in header_map.items():
            if idx >= len(row) or not row[idx]:
                continue
            
            value = str(row[idx]).strip()
            
            if "model" in col_name:
                spec.model = value.upper()
            elif "forming" in col_name or "area" in col_name:
                spec.forming_area_mm = value
                match = re.search(r'(\d+)\s*[xX×]\s*(\d+)', value)
                if match:
                    spec.forming_area_raw = (int(match.group(1)), int(match.group(2)))
            elif "heater" in col_name and "kw" in col_name.lower():
                try:
                    spec.heater_power_kw = float(re.sub(r'[^\d.]', '', value))
                except ValueError:
                    pass
            elif "vacuum" in col_name:
                spec.vacuum_pump_capacity = value
            elif "height" in col_name:
                try:
                    spec.max_tool_height_mm = int(re.sub(r'[^\d]', '', value))
                except ValueError:
                    pass
            elif "price" in col_name:
                try:
                    price = int(re.sub(r'[^\d]', '', value))
                    if "usd" in col_name.lower() or "$" in value:
                        spec.price_usd = price
                    else:
                        spec.price_inr = price
                except ValueError:
                    pass
        
        return spec if spec.model else None
    
    def _extract_from_text_patterns(
        self,
        text: str,
        filename: str,
        page_num: int,
    ) -> List[ExtractedSpec]:
        """Extract specs from text using regex patterns."""
        specs_by_model = {}
        
        # Find all model numbers
        for pattern in SPEC_PATTERNS["model"]:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                model = match.group(1).upper()
                if model not in specs_by_model:
                    specs_by_model[model] = ExtractedSpec(
                        model=model,
                        source_file=filename,
                        source_page=page_num,
                        extraction_method="pattern",
                        extraction_confidence=0.7,
                        extracted_at=datetime.now().isoformat(),
                    )
                    
                    # Determine series
                    if model.startswith("PF1"):
                        specs_by_model[model].series = "PF1"
                    elif model.startswith("PF2"):
                        specs_by_model[model].series = "PF2"
                    elif model.startswith("AM"):
                        specs_by_model[model].series = "AM"
                    elif model.startswith("IMG"):
                        specs_by_model[model].series = "IMG"
                    elif model.startswith("FCS"):
                        specs_by_model[model].series = "FCS"
                    elif model.startswith("UNO"):
                        specs_by_model[model].series = "UNO"
                    elif model.startswith("DUO"):
                        specs_by_model[model].series = "DUO"
        
        if not specs_by_model:
            return []
        
        # Extract specs and associate with models
        # For now, associate with all models on this page (can be refined)
        for model, spec in specs_by_model.items():
            # Look for specs near this model in text
            model_pos = text.find(model)
            if model_pos == -1:
                continue
            
            # Search within 1000 chars of model mention
            context = text[max(0, model_pos - 200):model_pos + 800]
            
            # Extract forming area
            for pattern in SPEC_PATTERNS["forming_area"]:
                match = re.search(pattern, context, re.IGNORECASE)
                if match:
                    spec.forming_area_mm = f"{match.group(1)} x {match.group(2)}"
                    spec.forming_area_raw = (int(match.group(1)), int(match.group(2)))
                    break
            
            # Extract heater power
            for pattern in SPEC_PATTERNS["heater_power"]:
                match = re.search(pattern, context, re.IGNORECASE)
                if match:
                    try:
                        spec.heater_power_kw = float(match.group(1))
                    except ValueError:
                        pass
                    break
            
            # Extract vacuum pump
            for pattern in SPEC_PATTERNS["vacuum_pump"]:
                match = re.search(pattern, context, re.IGNORECASE)
                if match:
                    spec.vacuum_pump_capacity = f"{match.group(1)} m³/hr"
                    break
            
            # Extract tool height
            for pattern in SPEC_PATTERNS["tool_height"]:
                match = re.search(pattern, context, re.IGNORECASE)
                if match:
                    try:
                        spec.max_tool_height_mm = int(match.group(1))
                    except ValueError:
                        pass
                    break
            
            # Extract prices
            for pattern in SPEC_PATTERNS["price_inr"]:
                match = re.search(pattern, context, re.IGNORECASE)
                if match:
                    try:
                        spec.price_inr = int(match.group(1).replace(",", ""))
                    except ValueError:
                        pass
                    break
            
            for pattern in SPEC_PATTERNS["price_usd"]:
                match = re.search(pattern, context, re.IGNORECASE)
                if match:
                    try:
                        spec.price_usd = int(match.group(1).replace(",", ""))
                    except ValueError:
                        pass
                    break
        
        return list(specs_by_model.values())
    
    def _extract_with_llm(
        self,
        text: str,
        filename: str,
        page_num: int,
    ) -> List[ExtractedSpec]:
        """Extract specs using LLM for unstructured text."""
        if not self.client or len(text) < 100:
            return []
        
        try:
            # Limit text length for API
            text_truncated = text[:4000]
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": EXTRACTION_PROMPT.format(text=text_truncated)}
                ],
                temperature=0.1,
                response_format={"type": "json_object"},
            )
            
            result = json.loads(response.choices[0].message.content)
            
            # Handle both array and object responses
            if isinstance(result, dict):
                if "specs" in result:
                    result = result["specs"]
                elif "machines" in result:
                    result = result["machines"]
                else:
                    result = [result]
            
            specs = []
            for item in result:
                if not isinstance(item, dict) or not item.get("model"):
                    continue
                
                spec = ExtractedSpec(
                    model=item.get("model", "").upper(),
                    series=item.get("series", ""),
                    forming_area_mm=item.get("forming_area_mm", ""),
                    heater_power_kw=float(item.get("heater_power_kw", 0) or 0),
                    vacuum_pump_capacity=item.get("vacuum_pump_capacity", ""),
                    max_tool_height_mm=int(item.get("max_tool_height_mm", 0) or 0),
                    max_draw_depth_mm=int(item.get("max_draw_depth_mm", 0) or 0),
                    max_sheet_thickness_mm=float(item.get("max_sheet_thickness_mm", 0) or 0),
                    heater_type=item.get("heater_type", ""),
                    power_supply=item.get("power_supply", ""),
                    price_inr=item.get("price_inr"),
                    price_usd=item.get("price_usd"),
                    features=item.get("features", []),
                    applications=item.get("applications", []),
                    description=item.get("description", ""),
                    source_file=filename,
                    source_page=page_num,
                    extraction_method="llm",
                    extraction_confidence=0.8,
                    extracted_at=datetime.now().isoformat(),
                )
                
                # Parse forming area raw
                if spec.forming_area_mm:
                    match = re.search(r'(\d+)\s*[xX×]\s*(\d+)', spec.forming_area_mm)
                    if match:
                        spec.forming_area_raw = (int(match.group(1)), int(match.group(2)))
                
                specs.append(spec)
            
            return specs
            
        except Exception as e:
            logger.warning(f"LLM extraction failed: {e}")
            return []
    
    def _deduplicate_specs(self, specs: List[ExtractedSpec]) -> List[ExtractedSpec]:
        """Deduplicate and merge specs for the same model."""
        by_model = {}
        
        for spec in specs:
            if not spec.model:
                continue
            
            if spec.model not in by_model:
                by_model[spec.model] = spec
            else:
                # Merge: prefer higher confidence, fill in gaps
                existing = by_model[spec.model]
                
                if spec.extraction_confidence > existing.extraction_confidence:
                    by_model[spec.model] = spec
                    # But keep any values from existing that are missing in new
                    self._merge_spec_values(spec, existing)
                else:
                    # Keep existing but fill gaps from new
                    self._merge_spec_values(existing, spec)
        
        return list(by_model.values())
    
    def _merge_spec_values(self, target: ExtractedSpec, source: ExtractedSpec):
        """Merge values from source into target where target is missing."""
        if not target.forming_area_mm and source.forming_area_mm:
            target.forming_area_mm = source.forming_area_mm
            target.forming_area_raw = source.forming_area_raw
        if not target.heater_power_kw and source.heater_power_kw:
            target.heater_power_kw = source.heater_power_kw
        if not target.vacuum_pump_capacity and source.vacuum_pump_capacity:
            target.vacuum_pump_capacity = source.vacuum_pump_capacity
        if not target.max_tool_height_mm and source.max_tool_height_mm:
            target.max_tool_height_mm = source.max_tool_height_mm
        if not target.price_inr and source.price_inr:
            target.price_inr = source.price_inr
        if not target.price_usd and source.price_usd:
            target.price_usd = source.price_usd
        if not target.features and source.features:
            target.features = source.features
        if not target.applications and source.applications:
            target.applications = source.applications
    
    def _log_extraction(self, filename: str, specs: List[ExtractedSpec]):
        """Log extraction results."""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "filename": filename,
            "specs_extracted": len(specs),
            "models": [s.model for s in specs],
            "methods": list(set(s.extraction_method for s in specs)),
        }
        
        try:
            self._extraction_log_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._extraction_log_path, "a") as f:
                f.write(json.dumps(log_entry) + "\n")
        except Exception as e:
            logger.debug(f"Failed to log extraction: {e}")
    
    def update_database(
        self,
        specs: List[ExtractedSpec],
        overwrite: bool = False,
    ) -> Dict[str, Any]:
        """
        Update machine database with extracted specs.
        
        Args:
            specs: Extracted specs to add
            overwrite: Whether to overwrite existing specs
        
        Returns:
            Summary of updates made
        """
        if not MACHINE_SPECS:
            logger.warning("Machine database not available for updates")
            return {"error": "Database not available"}
        
        added = []
        updated = []
        skipped = []
        
        for spec in specs:
            model = spec.model
            
            existing = get_machine(model) if get_machine else MACHINE_SPECS.get(model)
            
            if existing and not overwrite:
                # Check if we're adding new info
                has_new_info = (
                    (spec.heater_power_kw and not existing.heater_power_kw) or
                    (spec.vacuum_pump_capacity and not existing.vacuum_pump_capacity) or
                    (spec.price_inr and not existing.price_inr) or
                    (spec.max_tool_height_mm and not existing.max_tool_height_mm)
                )
                
                if has_new_info:
                    # Update existing with new info
                    if spec.heater_power_kw and not existing.heater_power_kw:
                        existing.heater_power_kw = spec.heater_power_kw
                    if spec.vacuum_pump_capacity and not existing.vacuum_pump_capacity:
                        existing.vacuum_pump_capacity = spec.vacuum_pump_capacity
                    if spec.price_inr and not existing.price_inr:
                        existing.price_inr = spec.price_inr
                    if spec.max_tool_height_mm and not existing.max_tool_height_mm:
                        existing.max_tool_height_mm = spec.max_tool_height_mm
                    
                    existing.source_documents.append(spec.source_file)
                    existing.last_updated = datetime.now().isoformat()
                    updated.append(model)
                else:
                    skipped.append(model)
            elif existing and overwrite:
                # Replace with new spec
                machine_spec = spec.to_machine_spec()
                if machine_spec:
                    MACHINE_SPECS[model] = machine_spec
                    updated.append(model)
            else:
                # New model
                machine_spec = spec.to_machine_spec()
                if machine_spec:
                    MACHINE_SPECS[model] = machine_spec
                    added.append(model)
        
        return {
            "added": added,
            "updated": updated,
            "skipped": skipped,
            "total_processed": len(specs),
        }
    
    def find_database_gaps(self) -> List[str]:
        """Find models in database that are missing key specs."""
        gaps = []
        
        for model, spec in MACHINE_SPECS.items():
            missing = []
            if not spec.heater_power_kw:
                missing.append("heater_power_kw")
            if not spec.vacuum_pump_capacity:
                missing.append("vacuum_pump_capacity")
            if not spec.max_tool_height_mm:
                missing.append("max_tool_height_mm")
            if not spec.price_inr and not spec.price_usd:
                missing.append("price")
            
            if missing:
                gaps.append(f"{model}: missing {', '.join(missing)}")
        
        return gaps
    
    def extract_from_directory(
        self,
        directory: str,
        pattern: str = "*.pdf",
    ) -> Dict[str, List[ExtractedSpec]]:
        """
        Extract specs from all PDFs in a directory.
        
        Args:
            directory: Directory path to scan
            pattern: Glob pattern for PDF files
        
        Returns:
            Dictionary mapping filename to extracted specs
        """
        import glob
        
        directory = Path(directory)
        results = {}
        
        for pdf_path in directory.glob(pattern):
            logger.info(f"Processing: {pdf_path.name}")
            specs = self.extract_from_pdf(str(pdf_path))
            if specs:
                results[pdf_path.name] = specs
        
        return results


# Singleton instance
_extractor: Optional[PDFSpecExtractor] = None


def get_pdf_extractor() -> PDFSpecExtractor:
    """Get singleton PDFSpecExtractor instance."""
    global _extractor
    if _extractor is None:
        _extractor = PDFSpecExtractor()
    return _extractor


def extract_specs(pdf_path: str) -> List[ExtractedSpec]:
    """Convenience function to extract specs from a PDF."""
    return get_pdf_extractor().extract_from_pdf(pdf_path)


def fill_database_gaps(imports_dir: str = None) -> Dict[str, Any]:
    """
    Scan PDF documents and fill database gaps.
    
    This is the main entry point for auto-filling database gaps.
    """
    if imports_dir is None:
        imports_dir = str(PROJECT_ROOT / "data" / "imports")
    
    extractor = get_pdf_extractor()
    
    # First, find gaps
    gaps = extractor.find_database_gaps()
    logger.info(f"Found {len(gaps)} models with missing specs")
    
    # Extract from all PDFs
    all_specs = []
    for pdf_path in Path(imports_dir).glob("*.pdf"):
        specs = extractor.extract_from_pdf(str(pdf_path))
        all_specs.extend(specs)
    
    # Update database
    result = extractor.update_database(all_specs)
    result["gaps_before"] = len(gaps)
    result["gaps_after"] = len(extractor.find_database_gaps())
    
    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("PDF Spec Extractor")
    print("=" * 60)
    
    # Find gaps
    extractor = get_pdf_extractor()
    gaps = extractor.find_database_gaps()
    
    print(f"\nDatabase gaps ({len(gaps)} models):")
    for gap in gaps[:10]:
        print(f"  - {gap}")
    if len(gaps) > 10:
        print(f"  ... and {len(gaps) - 10} more")
    
    # Test extraction on a sample file
    imports_dir = PROJECT_ROOT / "data" / "imports"
    sample_pdf = imports_dir / "AM Machine Catalogue.pdf"
    
    if sample_pdf.exists():
        print(f"\nTesting extraction on: {sample_pdf.name}")
        specs = extractor.extract_from_pdf(str(sample_pdf))
        print(f"Extracted {len(specs)} specs:")
        for spec in specs[:5]:
            print(f"  - {spec.model}: {spec.forming_area_mm}, {spec.heater_power_kw}kW")
