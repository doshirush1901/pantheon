#!/usr/bin/env python3
"""
MACHINECRAFT MACHINE DATABASE
=============================

Source of truth for machine specs. Loads from data/brain/machine_specs.json
so specs can be updated without code changes.

Use reload_specs() to hot-reload after editing the JSON file.
"""

import json
import logging
import re
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict, field
from datetime import datetime

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent.parent
SPECS_FILE = PROJECT_ROOT / "data" / "brain" / "machine_specs.json"
DATABASE_FILE = PROJECT_ROOT / "data" / "machine_database.json"
IMPORTS_DIR = PROJECT_ROOT / "data" / "imports"

# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class MachineSpec:
    """Complete specification for a machine model."""
    # Identity
    model: str
    series: str
    variant: str = ""  # e.g., "standard", "servo", "pressure"
    
    # Pricing
    price_inr: Optional[int] = None
    price_usd: Optional[int] = None
    
    # Dimensions
    forming_area_mm: str = ""  # e.g., "2000 x 1500"
    forming_area_raw: tuple = ()  # (width_mm, height_mm)
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
    vacuum_pump_capacity: str = ""  # m³/hr
    vacuum_tank_size: str = ""  # liters
    
    # Mechanical
    clamp_force: str = ""
    closing_force: str = ""
    
    # Electrical
    power_supply: str = ""
    
    # Performance
    cycle_time: str = ""
    
    # Additional
    description: str = ""
    features: List[str] = field(default_factory=list)
    applications: List[str] = field(default_factory=list)
    
    # Metadata
    source_documents: List[str] = field(default_factory=list)
    last_updated: str = ""


# ============================================================================
# LOAD MACHINE SPECS FROM JSON
# ============================================================================

def _load_specs_from_json() -> Dict[str, "MachineSpec"]:
    """Load machine specs from the JSON file. Falls back to empty dict on error."""
    if not SPECS_FILE.exists():
        logger.warning(f"Machine specs file not found: {SPECS_FILE}")
        return {}
    try:
        raw = json.loads(SPECS_FILE.read_text())
        specs = {}
        for model_key, data in raw.items():
            raw_area = data.pop("forming_area_raw", [])
            if isinstance(raw_area, list) and len(raw_area) == 2:
                data["forming_area_raw"] = tuple(raw_area)
            else:
                data["forming_area_raw"] = ()
            data["last_updated"] = datetime.now().isoformat()
            specs[model_key] = MachineSpec(**data)
        logger.info(f"Loaded {len(specs)} machine specs from {SPECS_FILE}")
        return specs
    except Exception as e:
        logger.error(f"Failed to load machine specs: {e}")
        return {}


def reload_specs() -> int:
    """Hot-reload machine specs from JSON. Returns count of loaded specs."""
    global MACHINE_SPECS
    MACHINE_SPECS = _load_specs_from_json()
    return len(MACHINE_SPECS)


MACHINE_SPECS: Dict[str, MachineSpec] = _load_specs_from_json()


# Hardcoded specs removed in v3 — all 46 machines now in data/brain/machine_specs.json.
# To add a machine: edit that JSON file, then call reload_specs() or restart.
_REMOVED_LEGACY_BLOCK = """REMOVED(
        model="AM-5060",  # noqa: E501
        series="AM",
        variant="standard",
        price_inr=750000,
        forming_area_mm="500 x 600",
        forming_area_raw=(500, 600),
        max_draw_depth_mm=100,
        max_sheet_thickness_mm=1.2,
        min_sheet_thickness_mm=0.2,
        heater_power_kw=12,  # 24 heaters x 500W = 12kW
        total_power_kw=15,
        heater_type="Ceramic Trough",
        num_heaters=24,
        heater_zones=8,
        vacuum_pump_capacity="40 m³/hr",
        vacuum_tank_size="200L",
        power_supply="400V, 50Hz, 3P+N+PE",
        description="Standard AM machine for thin gauge vacuum forming",
        features=["Servo chain indexing", "4-pillar guided press", "PLC/HMI control"],
        applications=["Blister packaging", "Trays", "Clamshells"],
        source_documents=["AM Machine Catalogue.pdf"]
    ),
    "AM-6060": MachineSpec(
        model="AM-6060",
        series="AM",
        variant="standard",
        price_inr=900000,
        forming_area_mm="600 x 600",
        forming_area_raw=(600, 600),
        max_draw_depth_mm=100,
        max_sheet_thickness_mm=1.2,
        min_sheet_thickness_mm=0.2,
        heater_power_kw=15,
        total_power_kw=18,
        heater_type="Ceramic Trough",
        vacuum_pump_capacity="40 m³/hr",
        vacuum_tank_size="200L",
        power_supply="400V, 50Hz, 3P+N+PE",
        description="Standard AM machine 600x600 for thin gauge vacuum forming",
        source_documents=["AM Machine Catalogue.pdf", "Price List"]
    ),
    "AM-5060-P": MachineSpec(
        model="AM-5060-P",
        series="AM",
        variant="with press",
        price_inr=1500000,
        forming_area_mm="500 x 600",
        forming_area_raw=(500, 600),
        max_draw_depth_mm=100,
        max_sheet_thickness_mm=1.2,
        min_sheet_thickness_mm=0.2,
        heater_power_kw=15,
        heater_type="Ceramic Trough",
        vacuum_pump_capacity="40 m³/hr",
        vacuum_tank_size="200L",
        power_supply="400V, 50Hz, 3P+N+PE",
        description="AM machine with inline hydro-pneumatic press for cut-and-stack",
        features=["Inline press station", "Cut-and-stack capability", "Servo indexing", "PLC control"],
        applications=["Food trays", "Blister packs", "Clamshells with trimming"],
        source_documents=["Price List"]
    ),
    "AMP-5060": MachineSpec(
        model="AMP-5060",
        series="AM",
        variant="pressure forming",
        price_inr=3500000,
        forming_area_mm="500 x 600",
        forming_area_raw=(500, 600),
        max_draw_depth_mm=100,
        max_sheet_thickness_mm=1.5,
        min_sheet_thickness_mm=0.3,
        heater_power_kw=18,
        heater_type="Ceramic Trough",
        vacuum_pump_capacity="60 m³/hr",
        vacuum_tank_size="200L",
        power_supply="400V, 50Hz, 3P+N+PE",
        description="AM pressure forming machine for high-detail parts",
        features=["Pressure forming (up to 3 bar)", "Higher detail parts", "Sharper corners", "PLC control"],
        applications=["Electronics housings", "Medical trays", "High-detail packaging"],
        source_documents=["Price List"]
    ),
    
    # =========================================================================
    # PF1-X SERIES - All Servo Single Sheet (Premium line)
    # Source: Print PF1-X Machinecraft Catalogue.pdf
    # =========================================================================
    # PF1-X SERIES PRICING (30% reduced, PF1-XL-3020 = $300K benchmark)
    # =========================================================================
    "PF1-X-1006": MachineSpec(
        model="PF1-X-1006",
        series="PF1",
        variant="X (all-servo)",
        price_inr=7055000,  # ₹70.55 L
        price_usd=85000,
        forming_area_mm="1000 x 600",
        forming_area_raw=(1000, 600),
        max_tool_height_mm=400,
        heater_power_kw=26,
        heater_type="IR Ceramic/Quartz/Halogen (configurable)",
        vacuum_pump_capacity="120 m³/hr",
        power_supply="415V, 50Hz, 3P+N+PE",
        description="Compact all-servo thermoformer for small parts",
        features=["All servo drives", "Auto load/unload option", "Plug assist", "Ball transfer tool slide"],
        applications=["Small enclosures", "Medical parts", "Electronics"],
        source_documents=["PF1-X Catalogue"]
    ),
    "PF1-X-1208": MachineSpec(
        model="PF1-X-1208",
        series="PF1",
        variant="X (all-servo)",
        price_inr=8300000,  # ₹83 L
        price_usd=100000,
        forming_area_mm="1200 x 800",
        forming_area_raw=(1200, 800),
        max_tool_height_mm=400,
        heater_power_kw=40,
        heater_type="IR Ceramic/Quartz/Halogen (configurable)",
        vacuum_pump_capacity="140 m³/hr",
        power_supply="415V, 50Hz, 3P+N+PE",
        description="All-servo thermoformer for medium parts",
        features=["All servo drives", "Auto load/unload option", "Plug assist", "Ball transfer tool slide"],
        applications=["Enclosures", "Medical parts", "Automotive trim"],
        source_documents=["PF1-X Catalogue"]
    ),
    # AUTOLOADER STARTS FROM THIS MODEL
    "PF1-X-1210": MachineSpec(
        model="PF1-X-1210",
        series="PF1",
        variant="X (all-servo)",
        price_inr=11620000,  # ₹1.162 Cr
        price_usd=140000,
        forming_area_mm="1200 x 1000",
        forming_area_raw=(1200, 1000),
        max_tool_height_mm=500,
        heater_power_kw=48,
        heater_type="IR Ceramic/Quartz/Halogen (configurable)",
        vacuum_pump_capacity="160 m³/hr",
        power_supply="415V, 50Hz, 3P+N+PE",
        description="All-servo thermoformer with 500mm depth",
        features=["All servo drives", "Auto load/unload option", "Plug assist", "Ball transfer tool slide"],
        applications=["Automotive parts", "Medical equipment", "Industrial enclosures"],
        source_documents=["PF1-X Catalogue"]
    ),
    "PF1-X-1510": MachineSpec(
        model="PF1-X-1510",
        series="PF1",
        variant="X (all-servo)",
        price_inr=13280000,  # ₹1.328 Cr
        price_usd=160000,
        forming_area_mm="1500 x 1000",
        forming_area_raw=(1500, 1000),
        max_tool_height_mm=500,
        heater_power_kw=58,
        heater_type="IR Ceramic/Quartz/Halogen (configurable)",
        vacuum_pump_capacity="180 m³/hr",
        power_supply="415V, 50Hz, 3P+N+PE",
        description="All-servo thermoformer for larger parts",
        features=["All servo drives", "Auto load/unload option", "Plug assist", "Ball transfer tool slide"],
        applications=["Automotive panels", "EV components", "Luggage"],
        source_documents=["PF1-X Catalogue"]
    ),
    # PF1-X-1520 - IDEAL FOR PICKUP BEDLINERS (1500 x 2000 mm)
    "PF1-X-1520": MachineSpec(
        model="PF1-X-1520",
        series="PF1",
        variant="X (all-servo)",
        price_inr=15770000,  # ₹1.577 Cr
        price_usd=190000,
        forming_area_mm="1500 x 2000",
        forming_area_raw=(1500, 2000),
        max_tool_height_mm=500,
        max_draw_depth_mm=500,
        max_sheet_thickness_mm=10,
        min_sheet_thickness_mm=2,
        heater_power_kw=115,
        total_power_kw=150,
        heater_type="IR Ceramic/Quartz dual zone",
        num_heaters=2,
        heater_zones=8,
        vacuum_pump_capacity="220 m³/hr",
        vacuum_tank_size="500L",
        power_supply="415V, 50Hz, 3P+N+PE",
        description="Perfect for pickup truck bedliners, ideal forming area 1500x2000mm with 500mm depth for HDPE",
        features=["All servo drives", "Auto load/unload", "Plug assist", "Ball transfer tool slide", "Sag control", "Zone heater control"],
        applications=["Pickup truck bedliners", "Automotive panels", "Agricultural parts", "Tractor fenders"],
        source_documents=["PF1-X Catalogue", "PF1-X-1525 Quote"]
    ),
    "PF1-X-2116": MachineSpec(
        model="PF1-X-2116",
        series="PF1",
        variant="X (all-servo)",
        price_inr=18260000,  # ₹1.826 Cr
        price_usd=220000,
        forming_area_mm="2100 x 1600",
        forming_area_raw=(2100, 1600),
        max_tool_height_mm=500,
        heater_power_kw=128,
        heater_type="IR Ceramic/Quartz dual zone",
        vacuum_pump_capacity="250 m³/hr",
        power_supply="415V, 50Hz, 3P+N+PE",
        description="All-servo thermoformer for large panels",
        features=["All servo drives", "Auto load/unload", "Plug assist", "Ball transfer tool slide", "Sag control"],
        applications=["Bus interiors", "Railway parts", "Automotive panels"],
        source_documents=["PF1-X Catalogue"]
    ),
    "PF1-X-2412": MachineSpec(
        model="PF1-X-2412",
        series="PF1",
        variant="X (all-servo)",
        price_inr=19920000,  # ₹1.992 Cr
        price_usd=240000,
        forming_area_mm="2400 x 1200",
        forming_area_raw=(2400, 1200),
        max_tool_height_mm=650,
        heater_power_kw=101,
        heater_type="IR Ceramic/Quartz dual zone",
        vacuum_pump_capacity="200 m³/hr",
        power_supply="415V, 50Hz, 3P+N+PE",
        description="All-servo thermoformer for long parts",
        features=["All servo drives", "Auto load/unload", "Plug assist", "Ball transfer tool slide"],
        applications=["Automotive trim", "Long panels", "Industrial enclosures"],
        source_documents=["PF1-X Catalogue"]
    ),
    "PF1-X-2515": MachineSpec(
        model="PF1-X-2515",
        series="PF1",
        variant="X (all-servo)",
        price_inr=20750000,  # ₹2.075 Cr
        price_usd=250000,
        forming_area_mm="2500 x 1500",
        forming_area_raw=(2500, 1500),
        max_tool_height_mm=650,
        heater_power_kw=144,
        heater_type="IR Ceramic/Quartz dual zone",
        vacuum_pump_capacity="280 m³/hr",
        power_supply="415V, 50Hz, 3P+N+PE",
        description="Large all-servo thermoformer",
        features=["All servo drives", "Auto load/unload", "Plug assist", "Ball transfer tool slide", "Sag control"],
        applications=["Large automotive parts", "Bathtubs", "Spa shells"],
        source_documents=["PF1-X Catalogue"]
    ),
    "PF1-X-2020": MachineSpec(
        model="PF1-X-2020",
        series="PF1",
        variant="X (all-servo)",
        price_inr=20750000,  # ₹2.075 Cr
        price_usd=250000,
        forming_area_mm="2000 x 2000",
        forming_area_raw=(2000, 2000),
        max_tool_height_mm=650,
        heater_power_kw=154,
        heater_type="IR Ceramic/Quartz dual zone",
        vacuum_pump_capacity="300 m³/hr",
        power_supply="415V, 50Hz, 3P+N+PE",
        description="Large square format all-servo thermoformer",
        features=["All servo drives", "Auto load/unload", "Plug assist", "Ball transfer tool slide", "Sag control", "Zone control"],
        applications=["Large automotive parts", "Bathtubs", "Spa shells", "EV battery covers"],
        source_documents=["PF1-X Catalogue"]
    ),
    "PF1-X-2520": MachineSpec(
        model="PF1-X-2520",
        series="PF1",
        variant="X (all-servo)",
        price_inr=22410000,  # ₹2.241 Cr
        price_usd=270000,
        forming_area_mm="2500 x 2000",
        forming_area_raw=(2500, 2000),
        max_tool_height_mm=800,
        heater_power_kw=192,
        heater_type="IR Ceramic/Quartz dual zone",
        vacuum_pump_capacity="350 m³/hr",
        power_supply="415V, 50Hz, 3P+N+PE",
        description="Extra large all-servo thermoformer",
        features=["All servo drives", "Auto load/unload", "Plug assist", "Ball transfer tool slide", "Sag control", "Zone control"],
        applications=["Large truck parts", "Industrial containers", "Aerospace interiors"],
        source_documents=["PF1-X Catalogue"]
    ),
    "PF1-XL-3020": MachineSpec(
        model="PF1-XL-3020",
        series="PF1",
        variant="XL (all-servo large)",
        price_inr=24900000,  # ₹2.49 Cr
        price_usd=300000,
        forming_area_mm="3000 x 2000",
        forming_area_raw=(3000, 2000),
        max_tool_height_mm=800,
        heater_power_kw=230,
        heater_type="IR Ceramic/Quartz dual zone",
        vacuum_pump_capacity="400 m³/hr",
        power_supply="415V, 50Hz, 3P+N+PE",
        description="Extra large all-servo thermoformer for massive parts",
        features=["All servo drives", "Auto load/unload", "Plug assist", "Ball transfer tool slide", "Sag control", "Zone control"],
        applications=["Bus panels", "Railway interiors", "Aerospace", "Large automotive"],
        source_documents=["PF1-X Catalogue"]
    ),
    
    # =========================================================================
    # PF1-C SERIES - Pneumatic (from price list + quotations)
    # Note: PF1-A was merged into PF1-C (same machines, different naming)
    # =========================================================================
    "PF1-C-1008": MachineSpec(
        model="PF1-C-1008",
        series="PF1",
        variant="C (pneumatic)",
        price_inr=3300000,
        forming_area_mm="1000 x 800",
        forming_area_raw=(1000, 800),
        max_tool_height_mm=400,
        heater_power_kw=30,
        heater_type="IR Ceramic",
        vacuum_pump_capacity="100 m³/hr",
        vacuum_tank_size="200L",
        max_sheet_thickness_mm=8,
        power_supply="415V, 50Hz, 3P+N+PE",
        description="Standard Pneumatic PF1 closed-chamber machine with sag control",
        features=["Sag control chamber", "PLC + HMI control", "Centrifugal cooling fans"],
        source_documents=["Price List"]
    ),
    "PF1-C-1208": MachineSpec(
        model="PF1-C-1208",
        series="PF1",
        variant="C (pneumatic)",
        price_inr=3500000,
        forming_area_mm="1200 x 800",
        forming_area_raw=(1200, 800),
        max_tool_height_mm=400,
        heater_power_kw=36,
        heater_type="IR Ceramic",
        vacuum_pump_capacity="120 m³/hr",
        vacuum_tank_size="200L",
        max_sheet_thickness_mm=8,
        power_supply="415V, 50Hz, 3P+N+PE",
        features=["Sag control chamber", "PLC + HMI control"],
        source_documents=["Price List"]
    ),
    "PF1-C-1212": MachineSpec(
        model="PF1-C-1212",
        series="PF1",
        variant="C (pneumatic)",
        price_inr=3800000,
        forming_area_mm="1200 x 1200",
        forming_area_raw=(1200, 1200),
        max_tool_height_mm=400,
        heater_power_kw=44,
        heater_type="IR Ceramic",
        vacuum_pump_capacity="140 m³/hr",
        vacuum_tank_size="300L",
        max_sheet_thickness_mm=8,
        power_supply="415V, 50Hz, 3P+N+PE",
        source_documents=["Price List"]
    ),
    "PF1-C-1309": MachineSpec(
        model="PF1-C-1309",
        series="PF1",
        variant="C (pneumatic)",
        price_inr=3600000,
        forming_area_mm="1300 x 900",
        forming_area_raw=(1300, 900),
        max_tool_height_mm=400,
        max_sheet_thickness_mm=8,
        heater_power_kw=44,
        heater_type="IR Ceramic / IR Quartz",
        vacuum_pump_capacity="140 m³/hr",
        vacuum_tank_size="300L",
        power_supply="415V, 50Hz, 3P+N+PE",
        features=["Centrifugal blower", "Sag control chamber", "PLC + HMI control"],
        source_documents=["Print PF1-A Machinecraft Catalogue (1).pdf"]
    ),
    "PF1-C-1510": MachineSpec(
        model="PF1-C-1510",
        series="PF1",
        variant="C (pneumatic)",
        price_inr=4000000,
        forming_area_mm="1500 x 1000",
        forming_area_raw=(1500, 1000),
        max_tool_height_mm=500,
        heater_power_kw=56,
        heater_type="IR Ceramic/Quartz",
        vacuum_pump_capacity="160 m³/hr",
        vacuum_tank_size="300L",
        max_sheet_thickness_mm=10,
        power_supply="415V, 50Hz, 3P+N+PE",
        description="Popular mid-size machine for automotive parts",
        features=["Sag control", "Zone heating control", "PLC + 10\" HMI"],
        source_documents=["Price List", "PF1-C-1510 Quotation"]
    ),
    "PF1-C-1812": MachineSpec(
        model="PF1-C-1812",
        series="PF1",
        variant="C (pneumatic)",
        price_inr=4500000,
        forming_area_mm="1800 x 1200",
        forming_area_raw=(1800, 1200),
        max_tool_height_mm=500,
        heater_power_kw=80,
        heater_type="IR Quartz",
        vacuum_pump_capacity="180 m³/hr",
        vacuum_tank_size="400L",
        max_sheet_thickness_mm=10,
        power_supply="415V, 50Hz, 3P+N+PE",
        features=["Sag control", "Individual heater control", "Ball transfer tool change"],
        source_documents=["Price List"]
    ),
    "PF1-C-2010": MachineSpec(
        model="PF1-C-2010",
        series="PF1",
        variant="C (pneumatic)",
        price_inr=5000000,
        forming_area_mm="2000 x 1000",
        forming_area_raw=(2000, 1000),
        max_tool_height_mm=500,
        heater_power_kw=76,
        heater_type="IR Quartz",
        vacuum_pump_capacity="200 m³/hr",
        vacuum_tank_size="400L",
        max_sheet_thickness_mm=10,
        power_supply="415V, 50Hz, 3P+N+PE",
        source_documents=["Price List"]
    ),
    "PF1-C-2015": MachineSpec(
        model="PF1-C-2015",
        series="PF1",
        variant="C (pneumatic)",
        price_inr=6000000,
        forming_area_mm="2000 x 1500",
        forming_area_raw=(2000, 1500),
        max_tool_height_mm=500,
        heater_power_kw=125,
        heater_type="IR Quartz",
        vacuum_pump_capacity="220 m³/hr",
        vacuum_tank_size="500L",
        max_sheet_thickness_mm=10,
        power_supply="415V, 50Hz, 3P+N+PE",
        description="Popular large machine for truck bedliners, automotive parts, luggage",
        features=["Sag control chamber", "Individual heater zone control", "Ball transfer tool change", "Recipe management"],
        applications=["Truck bedliners", "Automotive panels", "Luggage shells", "Large enclosures"],
        source_documents=["Price List"]
    ),
    "PF1-C-2020": MachineSpec(
        model="PF1-C-2020",
        series="PF1",
        variant="C (pneumatic)",
        price_inr=6500000,
        forming_area_mm="2000 x 2000",
        forming_area_raw=(2000, 2000),
        max_tool_height_mm=650,
        heater_power_kw=154,
        heater_type="IR Quartz",
        vacuum_pump_capacity="250 m³/hr",
        vacuum_tank_size="500L",
        max_sheet_thickness_mm=10,
        power_supply="415V, 50Hz, 3P+N+PE",
        features=["Sag control", "Zone control", "Plug assist ready"],
        source_documents=["Price List"]
    ),
    "PF1-C-2412": MachineSpec(
        model="PF1-C-2412",
        series="PF1",
        variant="C (pneumatic)",
        price_inr=5500000,
        forming_area_mm="2400 x 1200",
        forming_area_raw=(2400, 1200),
        max_tool_height_mm=650,
        max_sheet_thickness_mm=10,
        heater_power_kw=110,
        heater_type="IR Quartz",
        vacuum_pump_capacity="240 m³/hr",
        vacuum_tank_size="500L",
        power_supply="415V, 50Hz, 3P+N+PE",
        features=["Sag control", "Zone heating", "Ball transfer", "Recipe management"],
        applications=["Large automotive", "Bus interiors", "Luggage"],
        source_documents=["Print PF1-A Machinecraft Catalogue (1).pdf"]
    ),
    "PF1-C-2515": MachineSpec(
        model="PF1-C-2515",
        series="PF1",
        variant="C (pneumatic)",
        price_inr=7000000,
        forming_area_mm="2500 x 1500",
        forming_area_raw=(2500, 1500),
        max_tool_height_mm=650,
        heater_power_kw=144,
        heater_type="IR Quartz",
        vacuum_pump_capacity="260 m³/hr",
        vacuum_tank_size="600L",
        max_sheet_thickness_mm=10,
        power_supply="415V, 50Hz, 3P+N+PE",
        source_documents=["Price List"]
    ),
    "PF1-C-2520": MachineSpec(
        model="PF1-C-2520",
        series="PF1",
        variant="C (pneumatic)",
        price_inr=7200000,
        forming_area_mm="2500 x 2000",
        forming_area_raw=(2500, 2000),
        max_tool_height_mm=800,
        max_sheet_thickness_mm=10,
        heater_power_kw=192,
        heater_type="IR Quartz",
        vacuum_pump_capacity="280 m³/hr",
        vacuum_tank_size="600L",
        power_supply="415V, 50Hz, 3P+N+PE",
        features=["Sag control", "Zone heating", "Ball transfer", "8 cooling fans"],
        applications=["Large enclosures", "Bus panels", "Industrial parts"],
        source_documents=["Print PF1-A Machinecraft Catalogue (1).pdf"]
    ),
    "PF1-C-3015": MachineSpec(
        model="PF1-C-3015",
        series="PF1",
        variant="C (pneumatic)",
        price_inr=7500000,
        forming_area_mm="3000 x 1500",
        forming_area_raw=(3000, 1500),
        max_tool_height_mm=650,
        heater_power_kw=170,
        heater_type="IR Quartz",
        vacuum_pump_capacity="280 m³/hr",
        vacuum_tank_size="600L",
        max_sheet_thickness_mm=10,
        power_supply="415V, 50Hz, 3P+N+PE",
        source_documents=["Price List"]
    ),
    "PF1-C-3020": MachineSpec(
        model="PF1-C-3020",
        series="PF1",
        variant="C (pneumatic)",
        price_inr=8000000,
        forming_area_mm="3000 x 2000",
        forming_area_raw=(3000, 2000),
        max_tool_height_mm=800,
        heater_power_kw=260,
        heater_type="IR Quartz",
        vacuum_pump_capacity="300 m³/hr",
        vacuum_tank_size="800L",
        max_sheet_thickness_mm=10,
        power_supply="415V, 50Hz, 3P+N+PE",
        description="Large format machine for big parts - truck liners, bus panels",
        features=["Sag control", "Zone heating", "Ball transfer tool change", "8 centrifugal fans"],
        source_documents=["Price List", "PF1-C-3020 Quotation"]
    ),
    
    # =========================================================================
    # IMG SERIES - In-Mold Graining (with COMPLETE specs)
    # =========================================================================
    "IMG-1205": MachineSpec(
        model="IMG-1205",
        series="IMG",
        variant="standard",
        price_inr=12500000,
        forming_area_mm="1200 x 500",
        forming_area_raw=(1200, 500),
        max_tool_height_mm=300,
        max_sheet_thickness_mm=3,
        heater_power_kw=60,
        heater_type="IR Quartz (precision zones)",
        vacuum_pump_capacity="150 m³/hr",
        vacuum_tank_size="300L",
        power_supply="415V, 50Hz, 3P+N+PE",
        description="IMG machine for automotive interior lamination with grain transfer",
        features=["Vacuum lamination", "Grain transfer", "Soft-feel finish", "Precision temperature control"],
        applications=["Automotive dashboards", "Door panels", "Console covers", "Armrests"],
        source_documents=["Print IMG-1350 Machinecraft Catalogue.pdf", "Price List"]
    ),
    "IMG-2012": MachineSpec(
        model="IMG-2012",
        series="IMG",
        variant="standard",
        price_inr=17500000,
        forming_area_mm="2000 x 1200",
        forming_area_raw=(2000, 1200),
        max_tool_height_mm=400,
        max_sheet_thickness_mm=3,
        heater_power_kw=100,
        heater_type="IR Quartz (precision zones)",
        vacuum_pump_capacity="200 m³/hr",
        vacuum_tank_size="400L",
        power_supply="415V, 50Hz, 3P+N+PE",
        description="Large IMG machine for full automotive interior panels",
        features=["Vacuum lamination", "Grain transfer", "Soft-feel finish", "Large format capability"],
        applications=["Large dashboards", "Full door panels", "Instrument panels", "Headliners"],
        source_documents=["Price List"]
    ),
    "IMG-1350": MachineSpec(
        model="IMG-1350",
        series="IMG",
        variant="standard",
        price_inr=14000000,
        forming_area_mm="1350 x 500",
        forming_area_raw=(1350, 500),
        max_tool_height_mm=300,
        max_sheet_thickness_mm=3,
        heater_power_kw=70,
        heater_type="IR Quartz (precision zones)",
        vacuum_pump_capacity="160 m³/hr",
        vacuum_tank_size="300L",
        power_supply="415V, 50Hz, 3P+N+PE",
        description="IMG machine for automotive soft-touch interiors with hot-melt lamination",
        features=["Vacuum lamination", "Grain transfer", "Soft-feel finish", "Hot-melt compatible", "Servo positioning"],
        applications=["IP covers", "Door inserts", "Armrests", "Center console covers"],
        source_documents=["Print IMG-1350 Machinecraft Catalogue.pdf", "IMGS -1350_ Machinecraft IAC Project Summary (2).pdf"]
    ),
    
    # =========================================================================
    # FCS SERIES - Inline Form-Cut-Stack (with COMPLETE specs)
    # =========================================================================
    "FCS-6050-3ST": MachineSpec(
        model="FCS-6050-3ST",
        series="FCS",
        variant="3 station pneumatic",
        price_inr=10000000,
        forming_area_mm="600 x 500",
        forming_area_raw=(600, 500),
        max_sheet_thickness_mm=1.5,
        min_sheet_thickness_mm=0.3,
        heater_power_kw=40,
        heater_type="Ceramic IR",
        vacuum_pump_capacity="80 m³/hr",
        vacuum_tank_size="200L",
        power_supply="415V, 50Hz, 3P+N+PE",
        description="Form, cut, stack - pneumatic - 3 station inline machine",
        features=["Inline production", "Form station", "Cut station", "Stack station", "Roll-fed"],
        applications=["Food packaging trays", "Disposable cups", "Containers"],
        source_documents=["Price List", "FCS Machinecraft Brochure Oct22.pdf"]
    ),
    "FCS-6050-4ST": MachineSpec(
        model="FCS-6050-4ST",
        series="FCS",
        variant="4 station pneumatic",
        price_inr=12500000,
        forming_area_mm="600 x 500",
        forming_area_raw=(600, 500),
        max_sheet_thickness_mm=1.5,
        min_sheet_thickness_mm=0.3,
        heater_power_kw=45,
        heater_type="Ceramic IR",
        vacuum_pump_capacity="80 m³/hr",
        vacuum_tank_size="200L",
        power_supply="415V, 50Hz, 3P+N+PE",
        description="Form, cut, hole, stack - pneumatic - 4 station inline",
        features=["Inline production", "Form station", "Cut station", "Hole punch station", "Stack station"],
        applications=["Food packaging", "Cups with holes", "Multi-feature containers"],
        source_documents=["Price List"]
    ),
    "FCS-7060-3ST": MachineSpec(
        model="FCS-7060-3ST",
        series="FCS",
        variant="3 station servo",
        price_inr=15000000,
        forming_area_mm="700 x 600",
        forming_area_raw=(700, 600),
        max_sheet_thickness_mm=2.0,
        min_sheet_thickness_mm=0.3,
        heater_power_kw=55,
        heater_type="Ceramic IR",
        vacuum_pump_capacity="100 m³/hr",
        vacuum_tank_size="300L",
        power_supply="415V, 50Hz, 3P+N+PE",
        description="Form, cut, stack - servo driven - 3 station high-speed",
        features=["Servo drives", "High precision", "Faster cycles", "Lower energy consumption"],
        applications=["High-volume packaging", "Premium food trays", "Medical packaging"],
        source_documents=["Price List"]
    ),
    "FCS-7060-4ST": MachineSpec(
        model="FCS-7060-4ST",
        series="FCS",
        variant="4 station servo",
        price_inr=17500000,
        forming_area_mm="700 x 600",
        forming_area_raw=(700, 600),
        max_sheet_thickness_mm=2.0,
        min_sheet_thickness_mm=0.3,
        heater_power_kw=60,
        heater_type="Ceramic IR",
        vacuum_pump_capacity="100 m³/hr",
        vacuum_tank_size="300L",
        power_supply="415V, 50Hz, 3P+N+PE",
        description="Form, cut, hole, stack - servo - 4 station high-speed",
        features=["Servo drives", "4 processing stations", "High precision", "Recipe management"],
        applications=["High-volume packaging", "Premium containers", "Export-quality trays"],
        source_documents=["Price List"]
    ),
    
    # =========================================================================
    # UNO SERIES - Single Station Basic (with COMPLETE specs)
    # =========================================================================
    "UNO-0806": MachineSpec(
        model="UNO-0806",
        series="UNO",
        variant="single heater",
        price_inr=5000000,  # ~$60K USD
        price_usd=60000,
        forming_area_mm="800 x 600",
        forming_area_raw=(800, 600),
        max_tool_height_mm=250,
        max_sheet_thickness_mm=6,
        heater_power_kw=18,
        heater_type="IR Ceramic (top only)",
        vacuum_pump_capacity="60 m³/hr",
        vacuum_tank_size="100L",
        power_supply="415V, 50Hz, 3P+N+PE",
        description="Entry-level single station machine with top heater only",
        features=["Single cylinder mould", "2 cylinder clamp", "Top heater", "PLC control"],
        applications=["Signage", "Simple trays", "Prototyping"],
        source_documents=["Price List"]
    ),
    "UNO-1208": MachineSpec(
        model="UNO-1208",
        series="UNO",
        variant="single heater",
        price_inr=5500000,  # ~$66K USD
        price_usd=66000,
        forming_area_mm="1200 x 800",
        forming_area_raw=(1200, 800),
        max_tool_height_mm=300,
        max_sheet_thickness_mm=6,
        heater_power_kw=28,
        heater_type="IR Ceramic (top only)",
        vacuum_pump_capacity="80 m³/hr",
        vacuum_tank_size="150L",
        power_supply="415V, 50Hz, 3P+N+PE",
        description="Mid-size single station machine with top heater",
        features=["Single cylinder mould", "2 cylinder clamp", "Top heater", "PLC control"],
        applications=["Signage", "Enclosures", "Covers"],
        source_documents=["Price List"]
    ),
    "UNO-1208-2H": MachineSpec(
        model="UNO-1208-2H",
        series="UNO",
        variant="twin heater",
        price_inr=6000000,  # ~$72K USD
        price_usd=72000,
        forming_area_mm="1200 x 800",
        forming_area_raw=(1200, 800),
        max_tool_height_mm=300,
        max_sheet_thickness_mm=8,
        heater_power_kw=56,
        heater_type="IR Ceramic (sandwich - top & bottom)",
        vacuum_pump_capacity="80 m³/hr",
        vacuum_tank_size="150L",
        power_supply="415V, 50Hz, 3P+N+PE",
        description="Single station with sandwich heaters for thicker sheets",
        features=["Twin heaters", "Faster heating", "Better uniformity", "PLC control"],
        applications=["Thicker materials", "Better detail", "Faster cycles"],
        source_documents=["Price List"]
    ),
    
    # =========================================================================
    # DUO SERIES - Double Station (with COMPLETE specs)
    # =========================================================================
    "DUO-0806": MachineSpec(
        model="DUO-0806",
        series="DUO",
        variant="standard",
        price_inr=5500000,  # ~$66K USD
        price_usd=66000,
        forming_area_mm="800 x 600",
        forming_area_raw=(800, 600),
        max_tool_height_mm=250,
        max_sheet_thickness_mm=6,
        heater_power_kw=18,
        heater_type="IR Ceramic (single, swing-over)",
        vacuum_pump_capacity="60 m³/hr",
        vacuum_tank_size="100L",
        power_supply="415V, 50Hz, 3P+N+PE",
        description="Double station with swing-over heater for higher output",
        features=["Two forming stations", "Alternating production", "Single heater swings over", "2x output"],
        applications=["Higher volume signage", "Batch production"],
        source_documents=["Price List"]
    ),
    "DUO-1208": MachineSpec(
        model="DUO-1208",
        series="DUO",
        variant="standard",
        price_inr=6500000,  # ~$78K USD
        price_usd=78000,
        forming_area_mm="1200 x 800",
        forming_area_raw=(1200, 800),
        max_tool_height_mm=300,
        max_sheet_thickness_mm=6,
        heater_power_kw=28,
        heater_type="IR Ceramic (single, swing-over)",
        vacuum_pump_capacity="80 m³/hr",
        vacuum_tank_size="150L",
        power_supply="415V, 50Hz, 3P+N+PE",
        description="Larger double station for higher output production",
        features=["Two forming stations", "Alternating production", "Swing-over heater", "Higher productivity"],
        applications=["Signage", "Industrial covers", "Batch production"],
        source_documents=["Price List"]
    ),
    
    # =========================================================================
    # PF1-R SERIES - With Roll Feeder (with COMPLETE specs)
    # =========================================================================
    "PF1-R-1510": MachineSpec(
        model="PF1-R-1510",
        series="PF1",
        variant="R (with roll feeder)",
        price_inr=5500000,
        forming_area_mm="1500 x 1000",
        forming_area_raw=(1500, 1000),
        max_tool_height_mm=500,
        max_sheet_thickness_mm=3,
        min_sheet_thickness_mm=0.5,
        heater_power_kw=56,
        heater_type="IR Quartz",
        vacuum_pump_capacity="160 m³/hr",
        vacuum_tank_size="300L",
        power_supply="415V, 50Hz, 3P+N+PE",
        description="PF1 machine with integrated roll feeder for continuous production",
        features=["Roll feeder", "Continuous sheet feed", "Higher productivity", "Servo indexing"],
        applications=["Semi-continuous production", "Thick gauge roll stock", "Automotive parts"],
        source_documents=["Price List", "Print PF1-R Machinecraft Catalogue .pdf"]
    ),
    
    # =========================================================================
    # PF2 SERIES - Open Type (with COMPLETE specs)
    # =========================================================================
    "PF2-P2010": MachineSpec(
        model="PF2-P2010",
        series="PF2",
        variant="open type",
        price_inr=3500000,
        forming_area_mm="2000 x 1000",
        forming_area_raw=(2000, 1000),
        max_tool_height_mm=400,
        max_sheet_thickness_mm=8,
        heater_power_kw=60,
        heater_type="IR Quartz",
        vacuum_pump_capacity="150 m³/hr",
        vacuum_tank_size="300L",
        power_supply="415V, 50Hz, 3P+N+PE",
        description="Open type PF2 machine - easier access for large parts",
        features=["Open frame design", "Easy part removal", "Large access area", "Manual loading"],
        applications=["Large signage", "Architectural panels", "Exhibition displays"],
        source_documents=["Price List"]
    ),
    "PF2-P2020": MachineSpec(
        model="PF2-P2020",
        series="PF2",
        variant="open type",
        price_inr=5200000,
        forming_area_mm="2000 x 2000",
        forming_area_raw=(2000, 2000),
        max_tool_height_mm=500,
        max_sheet_thickness_mm=8,
        heater_power_kw=80,
        heater_type="IR Quartz",
        vacuum_pump_capacity="180 m³/hr",
        vacuum_tank_size="400L",
        power_supply="415V, 50Hz, 3P+N+PE",
        description="Large open type PF2 for oversized parts",
        features=["Open frame design", "Large format", "Easy access", "Zone heating"],
        applications=["Large signage", "Bathtubs", "Spa covers", "Architectural"],
        source_documents=["Price List"]
    ),
    "PF2-P2424": MachineSpec(
        model="PF2-P2424",
        series="PF2",
        variant="open type",
        price_inr=6000000,
        forming_area_mm="2400 x 2400",
        forming_area_raw=(2400, 2400),
        max_tool_height_mm=600,
        max_sheet_thickness_mm=10,
        heater_power_kw=100,
        heater_type="IR Quartz",
        vacuum_pump_capacity="200 m³/hr",
        vacuum_tank_size="500L",
        power_supply="415V, 50Hz, 3P+N+PE",
        description="Extra large open type for oversized parts",
        features=["Open frame design", "Extra large format", "Easy access", "Zone heating"],
        applications=["Very large signage", "Hot tubs", "Pool covers", "Industrial enclosures"],
        source_documents=["Price List"]
    ),
    
    # =========================================================================
    # PLAY SERIES - Desktop (with COMPLETE specs)
    # =========================================================================
    "PLAY-450-DT": MachineSpec(
        model="PLAY-450-DT",
        series="PLAY",
        variant="desktop",
        price_inr=350000,
        forming_area_mm="450 x 450",
        forming_area_raw=(450, 450),
        max_tool_height_mm=150,
        max_sheet_thickness_mm=3,
        heater_power_kw=3,
        heater_type="IR Ceramic",
        vacuum_pump_capacity="20 m³/hr",
        power_supply="220V, 50Hz, Single Phase",
        description="Compact desktop vacuum forming machine",
        features=["Manual operation", "Compact size", "Entry-level", "Educational use"],
        applications=["Prototyping", "Small batches", "Education", "Hobbyist projects"],
        source_documents=["Price List"]
    ),
}
"""  # end of _REMOVED_LEGACY_BLOCK


# ============================================================================
# DATABASE FUNCTIONS
# ============================================================================

def normalize_model_alias(model: str) -> str:
    """
    Normalize model aliases to canonical names:
    - PF1-A-xxxx → PF1-C-xxxx (same machine, different naming)
    - PF1-S-xxxx → PF1-X-xxxx (same machine, different naming)
    - PF1-C-1020 → PF1-C-2010 (same machine, rotated dimensions)
    
    Model naming convention:
    - PF1-C-XXYY where XX = width in decimeters, YY = height in decimeters
    - PF1-C-2010 = 2000mm x 1000mm
    - PF1-C-1020 = 1000mm x 2000mm (same area, rotated naming)
    """
    model_upper = model.upper().replace(" ", "-").replace("_", "-")
    
    # Handle series aliases
    if model_upper.startswith("PF1-A-"):
        model_upper = model_upper.replace("PF1-A-", "PF1-C-")
    if model_upper.startswith("PF1-S-"):
        model_upper = model_upper.replace("PF1-S-", "PF1-X-")
    
    # Handle rotated dimension aliases (e.g., PF1-C-1020 → PF1-C-2010)
    # Canonical form has larger dimension first
    import re
    match = re.match(r'^(PF1-[CX])-(\d{2})(\d{2})$', model_upper)
    if match:
        prefix = match.group(1)
        dim1 = int(match.group(2))
        dim2 = int(match.group(3))
        # Normalize to canonical form (larger dimension first)
        if dim2 > dim1:
            model_upper = f"{prefix}-{dim2:02d}{dim1:02d}"
    
    return model_upper


def get_machine(model: str) -> Optional[MachineSpec]:
    """Get machine specs by model name. Handles aliases automatically."""
    # Normalize aliases first
    model_clean = normalize_model_alias(model)
    
    # Try exact match
    if model_clean in MACHINE_SPECS:
        return MACHINE_SPECS[model_clean]
    
    # Try fuzzy match
    for key, spec in MACHINE_SPECS.items():
        if model_clean.replace("-", "") == key.replace("-", ""):
            return spec
    
    return None


def get_machines_by_series(series: str) -> List[MachineSpec]:
    """Get all machines in a series."""
    series_upper = series.upper()
    return [spec for spec in MACHINE_SPECS.values() if spec.series.upper() == series_upper]


def find_machines_by_size(min_width: int = 0, min_height: int = 0, max_price: int = None) -> List[MachineSpec]:
    """
    Find machines that meet size requirements.
    
    Prioritizes:
    1. Exact size matches (lowest excess area)
    2. Then by price
    """
    results = []
    for spec in MACHINE_SPECS.values():
        if not spec.forming_area_raw:
            continue
        w, h = spec.forming_area_raw
        # Check if machine fits (allowing for orientation)
        fits_normal = w >= min_width and h >= min_height
        fits_rotated = w >= min_height and h >= min_width
        
        if fits_normal or fits_rotated:
            if max_price is None or (spec.price_inr and spec.price_inr <= max_price):
                # Calculate excess area (smaller = better fit)
                if fits_normal:
                    excess = (w - min_width) + (h - min_height)
                else:
                    excess = (w - min_height) + (h - min_width)
                results.append((spec, excess))
    
    # Sort by: 1) Excess area (best fit first), 2) Price
    results.sort(key=lambda x: (x[1], x[0].price_inr or 999999999))
    return [r[0] for r in results]


def format_spec_table(machines: List[MachineSpec], include_all: bool = False) -> str:
    """
    Format machines as a properly aligned text table.
    
    This generates PLAIN TEXT that renders correctly in email.
    """
    if not machines:
        return "No machines found."
    
    # Define columns
    if include_all:
        columns = [
            ("Model", lambda m: m.model, 16),
            ("Forming Area", lambda m: m.forming_area_mm, 18),
            ("Tool Height", lambda m: f"{m.max_tool_height_mm}mm" if m.max_tool_height_mm else "—", 12),
            ("Heater (kW)", lambda m: f"{m.heater_power_kw}" if m.heater_power_kw else "—", 12),
            ("Vacuum Pump", lambda m: m.vacuum_pump_capacity or "—", 14),
            ("Price (INR)", lambda m: f"₹{m.price_inr:,}" if m.price_inr else "Contact", 14),
            ("Price (USD)", lambda m: f"${m.price_inr // 83:,}" if m.price_inr else "Contact", 12),
        ]
    else:
        columns = [
            ("Model", lambda m: m.model, 16),
            ("Forming Area", lambda m: m.forming_area_mm, 18),
            ("Heater (kW)", lambda m: f"{m.heater_power_kw}" if m.heater_power_kw else "—", 12),
            ("Price (INR)", lambda m: f"₹{m.price_inr:,}" if m.price_inr else "Contact", 14),
        ]
    
    # Build table
    lines = []
    
    # Header
    header = ""
    separator = ""
    for name, _, width in columns:
        header += name.ljust(width)
        separator += "-" * (width - 1) + " "
    lines.append(header)
    lines.append(separator)
    
    # Rows
    for machine in machines:
        row = ""
        for _, getter, width in columns:
            value = str(getter(machine) or "—")
            row += value[:width-1].ljust(width)
        lines.append(row)
    
    return "\n".join(lines)


def get_all_models() -> List[str]:
    """Get list of all available models."""
    return sorted(MACHINE_SPECS.keys())


def save_database():
    """Save database to JSON file."""
    DATABASE_FILE.parent.mkdir(exist_ok=True)
    data = {model: asdict(spec) for model, spec in MACHINE_SPECS.items()}
    DATABASE_FILE.write_text(json.dumps(data, indent=2, default=str))
    logger.info("Saved %d machines to %s", len(data), DATABASE_FILE)


def print_summary():
    """Print database summary."""
    series_counts = {}
    for spec in MACHINE_SPECS.values():
        series_counts[spec.series] = series_counts.get(spec.series, 0) + 1
    
    logger.info("\n" + "=" * 50)
    logger.info("MACHINECRAFT MACHINE DATABASE")
    logger.info("=" * 50)
    logger.info("Total machines: %d", len(MACHINE_SPECS))
    logger.info("By series:")
    for series, count in sorted(series_counts.items()):
        logger.info("  %s: %d models", series, count)
    logger.info("=" * 50)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print_summary()
    
    # Test lookups
    print("\nTest: Get PF1-C-2015")
    m = get_machine("PF1-C-2015")
    if m:
        print(f"  {m.model}: {m.forming_area_mm}, {m.heater_power_kw}kW, ₹{m.price_inr:,}")
    
    print("\nTest: AM series machines")
    am_machines = get_machines_by_series("AM")
    print(format_spec_table(am_machines[:3]))
    
    print("\nTest: Find machines >= 1500x1000mm")
    large = find_machines_by_size(1500, 1000)
    print(format_spec_table(large[:5]))
