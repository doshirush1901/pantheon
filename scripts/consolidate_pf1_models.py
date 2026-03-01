#!/usr/bin/env python3
"""
CONSOLIDATE PF1-A → PF1-C
=========================

PF1-A and PF1-C are the SAME machines (pneumatic series).
This script merges them into a single consistent PF1-C series.

Strategy:
1. Keep detailed technical specs from PF1-A (more complete)
2. Keep prices from PF1-C (authoritative)
3. Add estimated prices for models only in A
4. Remove all PF1-A entries
"""

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "openclaw/agents/ira/src/brain"))

from machine_database import MACHINE_SPECS, MachineSpec

def analyze_models():
    """Analyze PF1-A and PF1-C models."""
    pf1_a = {m: MACHINE_SPECS[m] for m in MACHINE_SPECS if m.startswith('PF1-A-')}
    pf1_c = {m: MACHINE_SPECS[m] for m in MACHINE_SPECS if m.startswith('PF1-C-')}
    
    print("=" * 60)
    print("PF1-A vs PF1-C ANALYSIS")
    print("=" * 60)
    
    print(f"\nPF1-A models: {len(pf1_a)}")
    print(f"PF1-C models: {len(pf1_c)}")
    
    # Extract size codes
    a_sizes = {m.replace('PF1-A-', ''): m for m in pf1_a}
    c_sizes = {m.replace('PF1-C-', ''): m for m in pf1_c}
    
    overlap = set(a_sizes.keys()) & set(c_sizes.keys())
    only_a = set(a_sizes.keys()) - set(c_sizes.keys())
    only_c = set(c_sizes.keys()) - set(a_sizes.keys())
    
    print(f"\nOverlap (both A and C): {len(overlap)}")
    print(f"Only in A: {sorted(only_a)}")
    print(f"Only in C: {sorted(only_c)}")
    
    # Check price coverage in C
    c_with_prices = sum(1 for m in pf1_c.values() if m.price_inr)
    print(f"\nPF1-C with prices: {c_with_prices}/{len(pf1_c)}")
    
    # Check spec completeness
    print("\n" + "-" * 60)
    print("SPEC COMPARISON (A vs C for overlapping models)")
    print("-" * 60)
    
    for size in sorted(overlap):
        a_model = pf1_a[f'PF1-A-{size}']
        c_model = pf1_c[f'PF1-C-{size}']
        
        a_fields = sum(1 for f in [a_model.heater_power_kw, a_model.vacuum_pump_capacity, 
                                    a_model.max_sheet_thickness_mm] if f)
        c_fields = sum(1 for f in [c_model.heater_power_kw, c_model.vacuum_pump_capacity,
                                    c_model.max_sheet_thickness_mm] if f)
        
        price_source = "C" if c_model.price_inr else ("A" if a_model.price_inr else "NONE")
        
        print(f"  {size}: A specs={a_fields}/3, C specs={c_fields}/3, Price from {price_source}")
    
    return pf1_a, pf1_c, only_a, only_c


def generate_consolidated_code():
    """Generate consolidated PF1-C code."""
    pf1_a, pf1_c, only_a, only_c = analyze_models()
    
    print("\n" + "=" * 60)
    print("GENERATING CONSOLIDATED PF1-C ENTRIES")
    print("=" * 60)
    
    # Estimate prices for A-only models based on similar sized C models
    price_estimates = {
        '1309': 3600000,   # Between 1208 (3.5M) and 1510 (4M)
        '2412': 5500000,   # Between 2010 (5M) and 2515 (7M)
        '2520': 7200000,   # Between 2515 (7M) and 3020 (8M)
    }
    
    consolidated = []
    
    # First, process A-only models (need to be added to C)
    for size in sorted(only_a):
        a_model = pf1_a[f'PF1-A-{size}']
        price = price_estimates.get(size, None)
        
        entry = f'''    "PF1-C-{size}": MachineSpec(
        model="PF1-C-{size}",
        series="PF1",
        variant="C (pneumatic)",
        price_inr={price},
        forming_area_mm="{a_model.forming_area_mm}",
        forming_area_raw={a_model.forming_area_raw},
        max_tool_height_mm={a_model.max_tool_height_mm},
        max_sheet_thickness_mm={a_model.max_sheet_thickness_mm},
        heater_power_kw={a_model.heater_power_kw},
        heater_type="{a_model.heater_type}",
        vacuum_pump_capacity="{a_model.vacuum_pump_capacity}",
        vacuum_tank_size="{a_model.vacuum_tank_size}",
        power_supply="{a_model.power_supply}",
        features={a_model.features},
        applications={a_model.applications if a_model.applications else []},
        source_documents=["Print PF1-A Machinecraft Catalogue (1).pdf", "Consolidated"]
    ),'''
        
        consolidated.append(entry)
        print(f"  Added PF1-C-{size} (from A, price ₹{price:,})")
    
    print("\n" + "-" * 60)
    print("MODELS TO ADD TO PF1-C SECTION:")
    print("-" * 60)
    
    for entry in consolidated:
        print(entry)
    
    return consolidated


def main():
    """Run consolidation analysis."""
    print("\n" + "=" * 60)
    print("PF1 MODEL CONSOLIDATION")
    print("=" * 60)
    print("Goal: Merge PF1-A into PF1-C (they're the same machines)")
    print()
    
    # Analyze
    generate_consolidated_code()
    
    print("\n" + "=" * 60)
    print("RECOMMENDED ACTIONS:")
    print("=" * 60)
    print("""
1. ADD these 3 models to PF1-C section in machine_database.py:
   - PF1-C-1309 (1300 x 900, ₹3,600,000)
   - PF1-C-2412 (2400 x 1200, ₹5,500,000)
   - PF1-C-2520 (2500 x 2000, ₹7,200,000)

2. REMOVE entire PF1-A section (lines ~394-595)

3. VERIFY normalize_model_name() handles PF1-A → PF1-C mapping

4. RUN tests to ensure no breakage
""")


if __name__ == "__main__":
    main()
