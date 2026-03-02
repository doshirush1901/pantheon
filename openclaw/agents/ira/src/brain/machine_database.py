#!/usr/bin/env python3
"""
MACHINECRAFT MACHINE DATABASE
=============================

Technical specifications for all machines, loaded from data/brain/machine_specs.json.
This is the SOURCE OF TRUTH for machine specs.

To update specs: edit data/brain/machine_specs.json and call reload_specs().
See git tag v2 for the original hardcoded version.
"""

import json
import logging
import re
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent.parent
_SPECS_FILE = PROJECT_ROOT / "data" / "brain" / "machine_specs.json"
DATABASE_FILE = PROJECT_ROOT / "data" / "machine_database.json"


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class MachineSpec:
    """Complete specification for a machine model."""
    model: str
    series: str
    variant: str = ""

    price_inr: Optional[int] = None
    price_usd: Optional[int] = None

    forming_area_mm: str = ""
    forming_area_raw: tuple = ()
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

    clamp_force: str = ""
    closing_force: str = ""

    power_supply: str = ""
    cycle_time: str = ""

    description: str = ""
    features: List[str] = field(default_factory=list)
    applications: List[str] = field(default_factory=list)

    source_documents: List[str] = field(default_factory=list)
    last_updated: str = ""


# ============================================================================
# JSON LOADER
# ============================================================================

def _load_specs_from_json() -> Dict[str, MachineSpec]:
    """Load machine specs from the canonical JSON file."""
    if not _SPECS_FILE.exists():
        logger.warning("machine_specs.json not found at %s", _SPECS_FILE)
        return {}
    try:
        raw = json.loads(_SPECS_FILE.read_text())
        specs: Dict[str, MachineSpec] = {}
        for model, data in raw.items():
            if isinstance(data.get("forming_area_raw"), list):
                data["forming_area_raw"] = tuple(data["forming_area_raw"])
            data.pop("last_updated", None)
            specs[model] = MachineSpec(**data)
        logger.info("Loaded %d machine specs from %s", len(specs), _SPECS_FILE)
        return specs
    except Exception as e:
        logger.error("Failed to load machine_specs.json: %s", e)
        return {}


def reload_specs() -> int:
    """Hot-reload machine specs from JSON without restarting. Returns count loaded."""
    global MACHINE_SPECS
    MACHINE_SPECS = _load_specs_from_json()
    return len(MACHINE_SPECS)


MACHINE_SPECS: Dict[str, MachineSpec] = _load_specs_from_json()


# ============================================================================
# DATABASE FUNCTIONS
# ============================================================================

def normalize_model_alias(model: str) -> str:
    """
    Normalize model aliases to canonical names:
    - PF1-A-xxxx -> PF1-C-xxxx (same machine, different naming)
    - PF1-S-xxxx -> PF1-X-xxxx (same machine, different naming)
    - PF1-C-1020 -> PF1-C-2010 (same machine, rotated dimensions)
    """
    model_upper = model.upper().replace(" ", "-").replace("_", "-")

    if model_upper.startswith("PF1-A-"):
        model_upper = model_upper.replace("PF1-A-", "PF1-C-")
    if model_upper.startswith("PF1-S-"):
        model_upper = model_upper.replace("PF1-S-", "PF1-X-")

    match = re.match(r'^(PF1-[CX])-(\d{2})(\d{2})$', model_upper)
    if match:
        prefix = match.group(1)
        dim1 = int(match.group(2))
        dim2 = int(match.group(3))
        if dim2 > dim1:
            model_upper = f"{prefix}-{dim2:02d}{dim1:02d}"

    return model_upper


def get_machine(model: str) -> Optional[MachineSpec]:
    """Get machine specs by model name. Handles aliases automatically."""
    model_clean = normalize_model_alias(model)

    if model_clean in MACHINE_SPECS:
        return MACHINE_SPECS[model_clean]

    for key, spec in MACHINE_SPECS.items():
        if model_clean.replace("-", "") == key.replace("-", ""):
            return spec

    return None


def get_machines_by_series(series: str) -> List[MachineSpec]:
    """Get all machines in a series."""
    series_upper = series.upper()
    return [spec for spec in MACHINE_SPECS.values() if spec.series.upper() == series_upper]


def find_machines_by_size(min_width: int = 0, min_height: int = 0, max_price: int = None) -> List[MachineSpec]:
    """Find machines that meet size requirements, sorted by best fit then price."""
    results = []
    for spec in MACHINE_SPECS.values():
        if not spec.forming_area_raw:
            continue
        w, h = spec.forming_area_raw
        fits_normal = w >= min_width and h >= min_height
        fits_rotated = w >= min_height and h >= min_width

        if fits_normal or fits_rotated:
            if max_price is None or (spec.price_inr and spec.price_inr <= max_price):
                if fits_normal:
                    excess = (w - min_width) + (h - min_height)
                else:
                    excess = (w - min_height) + (h - min_width)
                results.append((spec, excess))

    results.sort(key=lambda x: (x[1], x[0].price_inr or 999999999))
    return [r[0] for r in results]


def format_spec_table(machines: List[MachineSpec], include_all: bool = False) -> str:
    """Format machines as a properly aligned text table for email/Telegram."""
    if not machines:
        return "No machines found."

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

    lines = []
    header = ""
    separator = ""
    for name, _, width in columns:
        header += name.ljust(width)
        separator += "-" * (width - 1) + " "
    lines.append(header)
    lines.append(separator)

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
    """Save current in-memory specs to JSON file."""
    DATABASE_FILE.parent.mkdir(exist_ok=True)
    data = {model: asdict(spec) for model, spec in MACHINE_SPECS.items()}
    DATABASE_FILE.write_text(json.dumps(data, indent=2, default=str))
    logger.info("Saved %d machines to %s", len(data), DATABASE_FILE)


def print_summary():
    """Print database summary."""
    series_counts: Dict[str, int] = {}
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
