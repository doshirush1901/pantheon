#!/usr/bin/env python3
"""
PF1-C Technical Specs Ingestion Script
======================================

Ingests detailed technical specs from 'pf1 table 2016.xls' into:
1. Qdrant vector database (for semantic retrieval)
2. Machine database (for direct lookup)

Source: pf1 table 2016.xls - Air cylinder driven PF1-C series specs
"""

import os
import sys
import json
import uuid
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

BRAIN_DIR = Path(__file__).parent
SKILLS_DIR = BRAIN_DIR.parent
AGENT_DIR = SKILLS_DIR.parent
PROJECT_ROOT = AGENT_DIR.parent.parent.parent

sys.path.insert(0, str(AGENT_DIR))

# Import from centralized config
try:
    from config import QDRANT_URL, COLLECTIONS, get_logger
    CONFIG_AVAILABLE = True
    COLLECTION_NAME = COLLECTIONS.get("chunks_voyage", "ira_chunks_v4_voyage")
    DISCOVERED_COLLECTION = COLLECTIONS.get("discovered_knowledge", "ira_discovered_knowledge")
except ImportError:
    CONFIG_AVAILABLE = False
    # Fallback: Load environment manually
    env_file = PROJECT_ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if line.strip() and not line.startswith('#') and '=' in line:
                key, _, value = line.partition('=')
                os.environ.setdefault(key.strip(), value.strip().strip('"'))
    QDRANT_URL = os.environ.get("QDRANT_URL", "http://localhost:6333")
    COLLECTION_NAME = "ira_chunks_v4_voyage"
    DISCOVERED_COLLECTION = "ira_discovered_knowledge"

import voyageai
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, VectorParams, Distance

EXCEL_PATH = PROJECT_ROOT / "data" / "imports" / "pf1 table 2016.xls"

FORMING_AREA_TO_MODEL = {
    "1000mm x 600mm": "PF1-C-1006",
    "1000mm x 800mm": "PF1-C-1008",
    "1000mm x 1000mm": "PF1-C-1010",
    "1300mm x 900mm": "PF1-C-1309",
    "1300mm x 1300mm": "PF1-C-1313",
    "1500mm x 1000mm": "PF1-C-1510",
    "1800mm x 1000mm": "PF1-C-1810",
    "2000mm x 1000mm": "PF1-C-2010",
    "2000mm x 1500mm": "PF1-C-2015",
    "2000mm x 2000mm": "PF1-C-2020",
    "2500mm x 1500mm": "PF1-C-2515",
    "2500mm x 2000mm": "PF1-C-2520",
    "3000mm x 2000mm": "PF1-C-3020",
    "3000mm x 2500mm": "PF1-C-3025",
    "1500mm x 1500mm": "PF1-C-1515",
}

def parse_excel() -> Dict[str, Dict[str, Any]]:
    """Parse the Excel file and extract specs for each machine size."""
    
    print(f"Reading: {EXCEL_PATH}")
    df = pd.read_excel(str(EXCEL_PATH))
    
    machines = {}
    
    forming_areas = df.iloc[1, 2:].tolist()
    
    spec_rows = {
        "heater_layout": 2,
        "top_heater_kw": 3,
        "bottom_heater_kw": 4,
        "width_mm": 5,
        "depth_front_mm": 6,
        "depth_back_mm": 7,
        "depth_total_mm": 8,
        "height_upper_body_mm": 9,
        "height_excl_plug_mm": 10,
        "height_incl_plug_mm": 11,
        "working_height_mm": 12,
        "mould_depth_top_heater_mm": 13,
        "mould_depth_bottom_heater_mm": 14,
        "vacuum_pump_lpm": 15,
        "vacuum_pump_kw": 16,
        "vacuum_reservoir_dia_mm": 17,
        "vacuum_reservoir_lit": 18,
        "sheet_clamp_force_kg": 19,
        "table_clamp_force_kg": 20,
        "plug_assist_force_kg": 21,
        "cooling_fans": 22,
        "cooling_fans_power_kw": 23,
        "air_req_per_cycle_lit": 24,
        "electrical_req_kw": 25,
        "mould_cyl_dia_mm": 27,
        "mould_cyl_stroke_mm": 28,
        "frame_cyl_dia_mm": 29,
        "frame_cyl_stroke_mm": 30,
        "plug_cyl_dia_mm": 31,
        "plug_cyl_stroke_mm": 32,
        "bottom_frame_height": 33,
        "top_frame_height_normal_mm": 34,
        "top_frame_height_autoloader_mm": 35,
        "heater_cyl_dia_mm": 36,
        "heater_cyl_stroke_mm": 37,
    }
    
    for col_idx in range(2, len(df.columns)):
        forming_area = df.iloc[1, col_idx]
        
        if pd.isna(forming_area) or not isinstance(forming_area, str):
            continue
        
        forming_area = str(forming_area).strip()
        model = FORMING_AREA_TO_MODEL.get(forming_area)
        
        if not model:
            print(f"  Unknown forming area: {forming_area}")
            continue
        
        specs = {
            "model": model,
            "series": "PF1",
            "variant": "C (pneumatic/air cylinder)",
            "forming_area_mm": forming_area.replace("mm", "").strip(),
            "source_document": "pf1 table 2016.xls",
            "ingested_at": datetime.now().isoformat(),
        }
        
        for spec_name, row_idx in spec_rows.items():
            try:
                value = df.iloc[row_idx, col_idx]
                if pd.notna(value):
                    if isinstance(value, (int, float)):
                        specs[spec_name] = round(value, 2) if isinstance(value, float) else int(value)
                    else:
                        specs[spec_name] = str(value).strip()
            except (IndexError, KeyError):
                pass
        
        machines[model] = specs
        print(f"  Parsed: {model} ({forming_area})")
    
    return machines


def generate_knowledge_text(model: str, specs: Dict[str, Any]) -> str:
    """Generate human-readable knowledge text for a machine's specs."""
    
    lines = [
        f"## Technical Specifications for {model}",
        f"Series: PF1 Series - Air Cylinder Driven Thermoforming Machine",
        f"Variant: Pneumatic (C variant)",
        "",
        "### Forming Specifications",
        f"- Maximum Forming Area: {specs.get('forming_area_mm', 'N/A')}",
        f"- Moulding Depth (with top heater): {specs.get('mould_depth_top_heater_mm', 'N/A')} mm",
        f"- Moulding Depth (with bottom heater): {specs.get('mould_depth_bottom_heater_mm', 'N/A')} mm",
        "",
        "### Heating System",
        f"- Heater Layout: {specs.get('heater_layout', 'N/A')} (Rows x Columns)",
        f"- Top Heater Power: {specs.get('top_heater_kw', 'N/A')} kW",
        f"- Bottom Heater Power: {specs.get('bottom_heater_kw', 'N/A')} kW",
        f"- Total Heater Power: {(specs.get('top_heater_kw', 0) or 0) + (specs.get('bottom_heater_kw', 0) or 0)} kW",
        "",
        "### Machine Dimensions",
        f"- Width: {specs.get('width_mm', 'N/A')} mm",
        f"- Depth (Front): {specs.get('depth_front_mm', 'N/A')} mm",
        f"- Depth (Back): {specs.get('depth_back_mm', 'N/A')} mm",
        f"- Depth (Total): {specs.get('depth_total_mm', 'N/A')} mm",
        f"- Height (Upper Body): {specs.get('height_upper_body_mm', 'N/A')} mm",
        f"- Height (Excl. Plug Assist): {specs.get('height_excl_plug_mm', 'N/A')} mm",
        f"- Height (Incl. Plug Assist): {specs.get('height_incl_plug_mm', 'N/A')} mm",
        f"- Working Height: {specs.get('working_height_mm', 'N/A')} mm",
        "",
        "### Vacuum System",
        f"- Vacuum Pump Capacity: {specs.get('vacuum_pump_lpm', 'N/A')} LPM ({(specs.get('vacuum_pump_lpm', 0) or 0) * 0.06} m³/hr)",
        f"- Vacuum Pump Power: {specs.get('vacuum_pump_kw', 'N/A')} kW",
        f"- Vacuum Reservoir Diameter: {specs.get('vacuum_reservoir_dia_mm', 'N/A')} mm",
        f"- Vacuum Reservoir Capacity: {specs.get('vacuum_reservoir_lit', 'N/A')} liters",
        "",
        "### Clamping & Force",
        f"- Sheet Clamp Force (@6 bar): {specs.get('sheet_clamp_force_kg', 'N/A')} kg",
        f"- Table Clamp Force (@6 bar): {specs.get('table_clamp_force_kg', 'N/A')} kg",
        f"- Plug Assist Force (@6 bar): {specs.get('plug_assist_force_kg', 'N/A')} kg",
        "",
        "### Cooling System",
        f"- Cooling Fans: {specs.get('cooling_fans', 'N/A')}",
        f"- Cooling Fans Power: {specs.get('cooling_fans_power_kw', 'N/A')} kW",
        "",
        "### Pneumatic Requirements",
        f"- Air Required per Cycle: {specs.get('air_req_per_cycle_lit', 'N/A')} liters",
        "",
        "### Electrical Requirements",
        f"- Total Electrical Load: {specs.get('electrical_req_kw', 'N/A')} kW",
        "",
        "### Cylinder Specifications",
        f"#### Mould Cylinder",
        f"- Diameter: {specs.get('mould_cyl_dia_mm', 'N/A')} mm",
        f"- Stroke: {specs.get('mould_cyl_stroke_mm', 'N/A')} mm",
        "",
        f"#### Frame Cylinder",
        f"- Diameter: {specs.get('frame_cyl_dia_mm', 'N/A')} mm",
        f"- Stroke: {specs.get('frame_cyl_stroke_mm', 'N/A')} mm",
        "",
        f"#### Plug Assist Cylinder",
        f"- Diameter: {specs.get('plug_cyl_dia_mm', 'N/A')} mm",
        f"- Stroke: {specs.get('plug_cyl_stroke_mm', 'N/A')} mm",
        "",
        f"#### Heater Cylinder",
        f"- Diameter: {specs.get('heater_cyl_dia_mm', 'N/A')} mm",
        f"- Stroke: {specs.get('heater_cyl_stroke_mm', 'N/A')} mm",
        "",
        "### Frame Heights",
        f"- Bottom Frame Height: {specs.get('bottom_frame_height', 'N/A')}",
        f"- Top Frame Height (Normal): {specs.get('top_frame_height_normal_mm', 'N/A')} mm",
        f"- Top Frame Height (With Autoloader): {specs.get('top_frame_height_autoloader_mm', 'N/A')} mm",
        "",
        f"Source: {specs.get('source_document', 'pf1 table 2016.xls')}",
    ]
    
    return "\n".join(lines)


def ingest_to_qdrant(machines: Dict[str, Dict[str, Any]]):
    """Ingest machine specs into Qdrant for semantic retrieval."""
    
    print("\n" + "=" * 60)
    print("INGESTING TO QDRANT")
    print("=" * 60)
    
    voyage = voyageai.Client()
    qdrant = QdrantClient(url=QDRANT_URL)
    
    try:
        qdrant.get_collection(DISCOVERED_COLLECTION)
    except Exception:
        qdrant.create_collection(
            collection_name=DISCOVERED_COLLECTION,
            vectors_config=VectorParams(size=1024, distance=Distance.COSINE)
        )
        print(f"Created collection: {DISCOVERED_COLLECTION}")
    
    points = []
    
    for model, specs in machines.items():
        knowledge_text = generate_knowledge_text(model, specs)
        
        print(f"  Embedding: {model}...")
        embedding = voyage.embed(
            [knowledge_text],
            model="voyage-3",
            input_type="document"
        ).embeddings[0]
        
        point_id = str(uuid.uuid4())
        
        points.append(PointStruct(
            id=point_id,
            vector=embedding,
            payload={
                "text": knowledge_text,
                "raw_text": knowledge_text,
                "model": model,
                "series": "PF1",
                "variant": "C (pneumatic)",
                "doc_type": "machine_spec",
                "source_group": "business",
                "filename": "pf1 table 2016.xls",
                "machines": [model],
                "specs": specs,
                "ingested_at": datetime.now().isoformat(),
                "source": "pf1_table_2016_ingestion",
            }
        ))
    
    qdrant.upsert(
        collection_name=DISCOVERED_COLLECTION,
        points=points
    )
    print(f"\n✓ Ingested {len(points)} machine specs to {DISCOVERED_COLLECTION}")
    
    try:
        qdrant.get_collection(COLLECTION_NAME)
        qdrant.upsert(
            collection_name=COLLECTION_NAME,
            points=points
        )
        print(f"✓ Also ingested to main collection: {COLLECTION_NAME}")
    except Exception as e:
        print(f"Note: Could not add to {COLLECTION_NAME}: {e}")


def ingest_to_mem0(machines: Dict[str, Dict[str, Any]]):
    """Ingest machine specs into Mem0 for long-term memory."""
    
    MEM0_API_KEY = os.environ.get("MEM0_API_KEY")
    if not MEM0_API_KEY:
        print("\n⚠ MEM0_API_KEY not set, skipping Mem0 ingestion")
        return
    
    print("\n" + "=" * 60)
    print("INGESTING TO MEM0")
    print("=" * 60)
    
    try:
        from mem0 import MemoryClient
        mem0 = MemoryClient(api_key=MEM0_API_KEY)
    except ImportError:
        print("  ⚠ mem0 package not installed, skipping")
        return
    except Exception as e:
        print(f"  ✗ Mem0 init error: {e}")
        return
    
    for model, specs in machines.items():
        knowledge_text = generate_knowledge_text(model, specs)
        
        summary = f"PF1-C {model} specs: {specs.get('forming_area_mm')} forming area, " \
                  f"{specs.get('top_heater_kw')}kW top heater, {specs.get('bottom_heater_kw')}kW bottom heater, " \
                  f"{specs.get('vacuum_pump_lpm')} LPM vacuum pump, {specs.get('electrical_req_kw')}kW electrical."
        
        try:
            mem0.add(
                summary,
                user_id="machinecraft_knowledge",
                metadata={
                    "type": "machine_spec",
                    "model": model,
                    "series": "PF1",
                    "variant": "C (pneumatic)",
                    "source": "pf1 table 2016.xls",
                }
            )
            print(f"  ✓ Added to Mem0: {model}")
        except Exception as e:
            print(f"  ✗ Mem0 error for {model}: {e}")
    
    print(f"\n✓ Ingested {len(machines)} specs to Mem0")


def save_to_json(machines: Dict[str, Dict[str, Any]]):
    """Save parsed specs to JSON for reference."""
    
    output_path = PROJECT_ROOT / "data" / "pf1_c_technical_specs.json"
    
    output = {
        "source": "pf1 table 2016.xls",
        "description": "PF1-C Series Air Cylinder Driven Thermoforming Machines - Detailed Technical Specifications",
        "extracted_at": datetime.now().isoformat(),
        "machines": machines
    }
    
    output_path.write_text(json.dumps(output, indent=2, default=str))
    print(f"\n✓ Saved specs to: {output_path}")


def main():
    """Main ingestion flow."""
    
    print("=" * 60)
    print("PF1-C TECHNICAL SPECS INGESTION")
    print("=" * 60)
    print(f"Source: {EXCEL_PATH}")
    print(f"Qdrant: {QDRANT_URL}")
    print("=" * 60)
    
    machines = parse_excel()
    
    if not machines:
        print("\n✗ No machines parsed from Excel file")
        return
    
    print(f"\n✓ Parsed {len(machines)} machine configurations")
    
    save_to_json(machines)
    
    ingest_to_qdrant(machines)
    
    ingest_to_mem0(machines)
    
    print("\n" + "=" * 60)
    print("INGESTION COMPLETE")
    print("=" * 60)
    print(f"Total machines ingested: {len(machines)}")
    print("Storage locations:")
    print(f"  - Qdrant: {DISCOVERED_COLLECTION}")
    print(f"  - Qdrant: {COLLECTION_NAME}")
    print(f"  - Mem0: machinecraft_knowledge")
    print(f"  - JSON: data/pf1_c_technical_specs.json")
    print("=" * 60)


if __name__ == "__main__":
    main()
