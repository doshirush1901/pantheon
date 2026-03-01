#!/usr/bin/env python3
"""
Ingest Machinecraft Ascent Presentation Copy.pdf knowledge.

Source: data/imports/Machinecraft Ascent Presentation Copy.pdf
Contains mobility/transportation thermoforming applications by industry segment.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "openclaw" / "agents" / "ira" / "skills" / "brain"))

from knowledge_ingestor import KnowledgeIngestor, KnowledgeItem

SOURCE_FILE = "Machinecraft Ascent Presentation Copy.pdf"


def create_knowledge_items() -> list[KnowledgeItem]:
    """Extract structured knowledge from Ascent mobility presentation."""
    items = []
    
    # Automotive applications
    items.append(KnowledgeItem(
        text="""Thermoforming Applications - AUTOMOTIVE Industry:

Parts produced via thermoforming for passenger cars:
- 3D Car Mats (floor mats with formed edges and contours)
- Instrument Panels / Dashboards
- Water Shields (door moisture barriers)
- Door Panels (interior trim)
- A-Pillars and B-Pillars (interior trim covers)

Key advantages for automotive:
- Cost-effective tooling vs injection molding
- Fast design iteration cycles
- Suitable for low-to-medium volume production
- Premium surface finishes achievable
- Weight reduction vs metal alternatives

Target customers: Automotive OEMs, Tier 1 suppliers, interior trim specialists.""",
        knowledge_type="application",
        source_file=SOURCE_FILE,
        entity="Automotive Applications",
        summary="Automotive thermoforming: 3D mats, instrument panels, water shields, door panels, A/B pillars",
        metadata={
            "industry": "automotive",
            "parts": ["3d_car_mats", "instrument_panel", "water_shield", "door_panel", "a_pillar", "b_pillar"]
        }
    ))
    
    # Specialty vehicles
    items.append(KnowledgeItem(
        text="""Thermoforming Applications - SPECIALTY VEHICLES:

Parts produced via thermoforming for specialty/emergency vehicles:
- Fire Trucks: Body panels, equipment housings
- RVs (Recreational Vehicles): Interior panels, exterior body parts
- Ambulances: Interior trim, equipment housings, body panels

Specialty vehicle advantages of thermoforming:
- Low volume production economically viable
- Custom designs for each application
- Lightweight body panels
- Through-colored parts eliminate painting
- Durable exterior-grade materials available

Target customers: Fire truck manufacturers, RV builders, ambulance converters,
specialty vehicle upfitters.""",
        knowledge_type="application",
        source_file=SOURCE_FILE,
        entity="Specialty Vehicle Applications",
        summary="Specialty vehicles: fire trucks, RVs, ambulances - low volume custom thermoformed parts",
        metadata={
            "industry": "specialty_vehicles",
            "parts": ["body_panels", "interior_trim", "equipment_housings"],
            "vehicle_types": ["fire_truck", "rv", "ambulance"]
        }
    ))
    
    # Commercial vehicles
    items.append(KnowledgeItem(
        text="""Thermoforming Applications - COMMERCIAL VEHICLES (Trucks):

Parts produced via thermoforming for trucks and commercial vehicles:
- Fenders (wheel arch covers)
- Instrument Panels / Dashboards
- Air Channels (HVAC ducting)
- Door Panels (interior trim)
- A-Pillars and B-Pillars (interior trim)
- Back Shell of Seats (seat back covers)

Commercial vehicle benefits:
- Durable materials withstand commercial use
- Easy cleaning surfaces
- Replacement parts readily producible
- Cost-effective for medium volumes
- Customizable for different cab configurations

Target customers: Truck OEMs (Tata, Ashok Leyland, Daimler, etc.), 
truck interior suppliers, seat manufacturers.""",
        knowledge_type="application",
        source_file=SOURCE_FILE,
        entity="Commercial Vehicle Applications",
        summary="Commercial vehicles: fenders, dashboards, air channels, door panels, seat backs for trucks",
        metadata={
            "industry": "commercial_vehicles",
            "parts": ["fender", "instrument_panel", "air_channel", "door_panel", "a_pillar", "b_pillar", "seat_back"]
        }
    ))
    
    # Mass transit
    items.append(KnowledgeItem(
        text="""Thermoforming Applications - MASS TRANSIT (Bus & Rail):

Parts produced via thermoforming for buses and railways:
- Electric Bus Parts: Interior panels, exterior components
- Railway Interiors: Wall panels, ceiling panels, seat components

Mass transit thermoforming advantages:
- Fire-retardant materials available (EN 45545 compliant)
- Large panel sizes possible (XL/XXL machines)
- Low smoke/toxicity materials for passenger safety
- Vandal-resistant surfaces
- Easy maintenance and cleaning
- Consistent appearance across fleet

Target customers: Bus manufacturers (Volvo, BYD, Tata), 
railway coach builders, metro/train interior suppliers.

Note: Railway applications require specific fire safety certifications.""",
        knowledge_type="application",
        source_file=SOURCE_FILE,
        entity="Mass Transit Applications",
        summary="Mass transit: electric bus parts, railway interiors - fire-retardant, large panels",
        metadata={
            "industry": "mass_transit",
            "parts": ["bus_interior", "bus_exterior", "railway_wall_panel", "railway_ceiling", "seat_component"],
            "vehicle_types": ["electric_bus", "railway"]
        }
    ))
    
    # Agriculture equipment
    items.append(KnowledgeItem(
        text="""Thermoforming Applications - AGRICULTURE EQUIPMENT:

Parts produced via thermoforming for agricultural machinery:
- Engine Hoods / Bonnets
- Fenders (wheel/track covers)
- Cabins (roof panels, side panels)
- Door Panels
- Construction Equipment parts (similar applications)

Agriculture equipment benefits of thermoforming:
- UV-resistant materials for outdoor use
- Impact-resistant for field conditions
- Large panel sizes for big equipment
- Through-colored (no paint to chip/fade)
- Chemical resistant options available
- Cost-effective for seasonal production volumes

Target customers: Tractor manufacturers (John Deere, Mahindra, TAFE),
harvester makers, construction equipment OEMs (JCB, Caterpillar, CASE).""",
        knowledge_type="application",
        source_file=SOURCE_FILE,
        entity="Agriculture Equipment Applications",
        summary="Agriculture: engine hoods, fenders, cabins, door panels - UV/impact resistant for outdoor use",
        metadata={
            "industry": "agriculture",
            "parts": ["engine_hood", "fender", "cabin_panel", "door_panel"],
            "also_applies": "construction_equipment"
        }
    ))
    
    # Electric mobility
    items.append(KnowledgeItem(
        text="""Thermoforming Applications - ELECTRIC MOBILITY:

Parts produced via thermoforming for electric vehicles:
- 3-Wheelers (auto-rickshaws): Body panels, interior trim
- Closed Pedal Bikes: Fairings, body enclosures
- Electric Pods: Complete body shells, interior panels
- Electric LCV (Light Commercial Vehicles): Body panels, cargo area liners

Electric mobility advantages of thermoforming:
- Lightweight parts extend battery range
- Fast prototyping for EV startups
- Low tooling cost for new vehicle designs
- Aerodynamic shapes achievable
- Suitable for low initial production volumes
- Quick design iterations as products evolve

Target customers: EV startups, e-rickshaw manufacturers, 
last-mile delivery vehicle makers, electric pod developers.

This is a HIGH GROWTH segment with many new entrants needing machinery.""",
        knowledge_type="application",
        source_file=SOURCE_FILE,
        entity="Electric Mobility Applications",
        summary="Electric mobility: 3-wheelers, e-bikes, pods, LCVs - lightweight, fast prototyping for EV startups",
        metadata={
            "industry": "electric_mobility",
            "parts": ["body_panel", "fairing", "body_shell", "cargo_liner"],
            "vehicle_types": ["3_wheeler", "pedal_bike", "electric_pod", "electric_lcv"],
            "growth": "high"
        }
    ))
    
    # Complete mobility applications summary
    items.append(KnowledgeItem(
        text="""PF1 Machine Applications - Complete Mobility Industry Summary:

INDUSTRY SEGMENTS SERVED:
1. Automotive: Mats, dashboards, door panels, pillars, water shields
2. Specialty Vehicles: Fire trucks, RVs, ambulances
3. Commercial Vehicles: Truck fenders, panels, seat backs
4. Mass Transit: Bus interiors/exteriors, railway panels
5. Agriculture Equipment: Hoods, fenders, cabins
6. Electric Mobility: E-rickshaws, pods, LCVs, e-bikes

COMMON THERMOFORMED PARTS ACROSS MOBILITY:
- Interior panels (door, pillar, dashboard)
- Exterior panels (fenders, hoods, body)
- Structural covers (wheel arches, engine bay)
- Functional parts (air channels, water shields)
- Seating components (seat backs, armrests)

WHY THERMOFORMING FOR MOBILITY:
- Lower tooling investment than injection molding
- Faster time-to-market for new models
- Economical for volumes 100 to 20,000 units
- Large parts possible (bus panels, truck hoods)
- Weight savings vs metal
- Through-color eliminates painting line

Machinecraft PF1 machines are ideal for mobility applications across all these segments.""",
        knowledge_type="application",
        source_file=SOURCE_FILE,
        entity="Mobility Applications Summary",
        summary="PF1 mobility applications: automotive, specialty, commercial, transit, agriculture, EV - complete overview",
        metadata={
            "industry": "mobility_all",
            "segments": ["automotive", "specialty_vehicles", "commercial_vehicles", "mass_transit", "agriculture", "electric_mobility"]
        }
    ))
    
    # Facility data
    items.append(KnowledgeItem(
        text="""Machinecraft Facility Data (2018 baseline):

MANUFACTURING FACILITY:
- Total Area: 12,000 sqm
- Built-Up Area: 4,000 sqm (as of 2018)
- Location: 3 hours drive north of Mumbai city

PRODUCTION CAPACITY:
- Number of machines per year: 25
- Number of employees: 100

Note: This was 2018 data from Ascent Foundation interview.
Current capacity has expanded (see 2024 presentations for updates).""",
        knowledge_type="general",
        source_file=SOURCE_FILE,
        entity="Machinecraft",
        summary="Machinecraft facility (2018): 12,000sqm total, 4,000sqm built-up, 25 machines/year, 100 employees",
        metadata={
            "topic": "facility",
            "year": 2018,
            "total_area_sqm": 12000,
            "built_area_sqm": 4000,
            "machines_per_year": 25,
            "employees": 100
        }
    ))
    
    return items


def main():
    print("=" * 60)
    print("Ingesting Machinecraft Ascent Mobility Applications")
    print("=" * 60)
    print(f"\nSource: {SOURCE_FILE}")
    
    items = create_knowledge_items()
    print(f"Extracted {len(items)} knowledge items\n")
    
    for i, item in enumerate(items, 1):
        print(f"  {i}. [{item.knowledge_type}] {item.entity}: {item.summary[:50]}...")
    
    print("\n" + "-" * 60)
    print("Starting ingestion...")
    
    ingestor = KnowledgeIngestor(verbose=True)
    result = ingestor.ingest_batch(items)
    
    print("\n" + "=" * 60)
    print(f"RESULT: {result}")
    print("=" * 60)
    
    if result.success:
        print("\n✓ Knowledge ingested successfully!")
        print(f"  - Items ingested: {result.items_ingested}")
        print(f"  - Qdrant main: {result.qdrant_main}")
        print(f"  - Qdrant discovered: {result.qdrant_discovered}")
        print(f"  - Mem0: {result.mem0}")
        print(f"  - JSON backup: {result.json_backup}")
    else:
        print("\n✗ Ingestion failed")
        if result.errors:
            print(f"  Errors: {result.errors}")
    
    return 0 if result.success else 1


if __name__ == "__main__":
    sys.exit(main())
