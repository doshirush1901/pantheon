#!/usr/bin/env python3
"""Keyword-based extraction without LLM (for when API quota is exhausted)."""

import os
import sys
import re
import json
import requests
import psycopg2
import psycopg2.extras
from concurrent.futures import ThreadPoolExecutor, as_completed
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from pathlib import Path
import warnings
import urllib3
warnings.filterwarnings("ignore")
urllib3.disable_warnings()

# Import from centralized config
MARKET_RESEARCH_DIR = Path(__file__).parent
SKILLS_DIR = MARKET_RESEARCH_DIR.parent
AGENT_DIR = SKILLS_DIR.parent
sys.path.insert(0, str(AGENT_DIR))

try:
    from config import DATABASE_URL
except ImportError:
    DATABASE_URL = os.getenv('DATABASE_URL', '')

DB_URL = DATABASE_URL

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
}

# Service keywords (EN + DE)
SERVICE_KEYWORDS = {
    'thermoforming': ['thermoform', 'thermo-form', 'thermo form'],
    'vacuum forming': ['vacuum form', 'vakuumform', 'vakuum-form'],
    'pressure forming': ['pressure form', 'druckform'],
    'twin-sheet forming': ['twin-sheet', 'twin sheet', 'twinsheet'],
    'deep drawing': ['tiefzieh', 'deep draw', 'tiefziehen'],
    'plastic processing': ['kunststoffverarbeitung', 'kunststoff-verarbeitung'],
    'injection molding': ['injection mold', 'spritzguss', 'spritzgieß'],
    'blow molding': ['blow mold', 'blasform'],
    'packaging': ['packaging', 'verpackung'],
    'CNC machining': ['cnc', 'fräsen'],
}

# Material keywords
MATERIAL_KEYWORDS = {
    'ABS': ['abs ', 'abs,', 'abs.'],
    'HDPE': ['hdpe', 'pe-hd'],
    'LDPE': ['ldpe', 'pe-ld'],
    'PP': [' pp ', 'pp,', 'polypropyl'],
    'PS': [' ps ', 'polystyro', 'polystyre'],
    'PVC': ['pvc', 'polyvinyl'],
    'PETG': ['petg', 'pet-g'],
    'PET': [' pet ', 'pet,'],
    'PC': ['polycarbon', ' pc '],
    'PMMA': ['pmma', 'acryl', 'plexiglas'],
    'TPE': ['tpe', 'thermoplastic elastomer'],
    'PA': ['polyamid', ' pa ', 'nylon'],
    'HIPS': ['hips', 'high impact'],
    'ASA': ['asa ', 'asa,'],
}

# Industry keywords
INDUSTRY_KEYWORDS = {
    'automotive': ['automotive', 'fahrzeug', 'car', 'auto', 'vehicle', 'kfz'],
    'medical': ['medical', 'medizin', 'healthcare', 'hospital', 'health'],
    'packaging': ['packaging', 'verpackung', 'food packaging'],
    'aerospace': ['aerospace', 'aircraft', 'aviation', 'luftfahrt'],
    'construction': ['construction', 'building', 'bau', 'gebäude'],
    'electronics': ['electronic', 'elektro', 'appliance'],
    'agriculture': ['agriculture', 'farming', 'landwirtschaft', 'landmaschine'],
    'caravans': ['caravan', 'camper', 'wohnmobil', 'wohnwagen'],
    'HVAC': ['hvac', 'heating', 'cooling', 'climate', 'heizung', 'klima', 'lüftung'],
    'transportation': ['transport', 'logistics', 'nutzfahrzeug'],
}

def get_companies():
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT company_id, name, website
        FROM market_research.companies
        WHERE is_valid = TRUE
          AND website IS NOT NULL
          AND (thermoforming_services IS NULL OR thermoforming_services = '[]'::jsonb)
    """)
    result = cur.fetchall()
    conn.close()
    return result

def scrape(url, timeout=12):
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout, verify=False)
        if r.status_code == 200:
            soup = BeautifulSoup(r.content, 'html.parser')
            for tag in soup(['script', 'style']):
                tag.decompose()
            return soup.get_text(separator=' ', strip=True).lower()
    except (requests.RequestException, Exception):
        pass
    return ""

def extract_keywords(text, keyword_dict):
    """Extract matching keywords from text."""
    found = []
    for category, patterns in keyword_dict.items():
        for pattern in patterns:
            if pattern.lower() in text:
                found.append(category)
                break
    return list(set(found))

def save(company_id, services, materials, industries):
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    
    confidence = 0.3
    if len(services) >= 2:
        confidence = 0.5
    if any(s in ['thermoforming', 'vacuum forming', 'deep drawing'] for s in services):
        confidence = 0.6
    
    cur.execute("""
        UPDATE market_research.companies SET
            thermoforming_services = %s::jsonb,
            materials = %s::jsonb,
            industries = %s::jsonb,
            research_confidence = %s,
            last_researched = NOW()
        WHERE company_id = %s
    """, (
        json.dumps(services),
        json.dumps(materials),
        json.dumps(industries),
        confidence,
        company_id
    ))
    conn.commit()
    conn.close()

def research(company):
    name = company['name']
    url = company['website']
    
    # Scrape
    text = scrape(url)
    if len(text) < 200:
        return False, name, 0, 0, 0
    
    # Extract with keywords
    services = extract_keywords(text, SERVICE_KEYWORDS)
    materials = extract_keywords(text, MATERIAL_KEYWORDS)
    industries = extract_keywords(text, INDUSTRY_KEYWORDS)
    
    # Save if we found anything meaningful
    if services or materials or industries:
        if not services:
            services = ['plastic processing']
        save(company['company_id'], services, materials, industries)
        return True, name, len(services), len(materials), len(industries)
    
    return False, name, 0, 0, 0

def main():
    companies = get_companies()
    print(f"Keyword extraction: {len(companies)} companies")
    print("=" * 60)
    
    success = 0
    
    with ThreadPoolExecutor(max_workers=12) as executor:
        futures = {executor.submit(research, c): c for c in companies}
        
        for i, future in enumerate(as_completed(futures), 1):
            try:
                ok, name, svc, mat, ind = future.result()
                if ok:
                    success += 1
                    print(f"[{i}] ✓ {name[:35]:35} svc={svc} mat={mat} ind={ind}")
                else:
                    print(f"[{i}] · {name[:35]}")
            except Exception as e:
                print(f"[{i}] ERR: {e}")
    
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    cur.execute("""
        SELECT 
            COUNT(*) FILTER (WHERE is_valid) as valid,
            COUNT(*) FILTER (WHERE is_valid AND thermoforming_services IS NOT NULL AND thermoforming_services != '[]'::jsonb) as data
        FROM market_research.companies
    """)
    v, d = cur.fetchone()
    conn.close()
    
    print()
    print("=" * 60)
    print(f"+{success} companies | Total: {d}/{v} ({d*100//v}%)")

if __name__ == '__main__':
    main()
