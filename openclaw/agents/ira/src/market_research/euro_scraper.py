#!/usr/bin/env python3
"""European site scraper with direct requests."""

import os
import sys
import json
import time
import re
import requests
import psycopg2
import psycopg2.extras
from concurrent.futures import ThreadPoolExecutor, as_completed
from openai import OpenAI
from urllib.parse import urlparse
from pathlib import Path
from bs4 import BeautifulSoup
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
    DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://ira:ira_password@localhost:5432/ira_db')

DB_URL = DATABASE_URL
client = OpenAI()

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9,de;q=0.8',
}

# Thermoforming keywords in multiple languages
KEYWORDS = [
    'thermoform', 'vacuum form', 'vakuum', 'tiefzieh', 'kunststoff',
    'plastic', 'forming', 'mold', 'blister', 'tray', 'packaging',
    'ABS', 'HDPE', 'PP', 'PS', 'PVC', 'PETG', 'polycarbonate',
    'automotive', 'medical', 'industrial', 'packaging'
]

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

def scrape_site(url, timeout=15):
    """Direct scraping with requests."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout, verify=False, allow_redirects=True)
        if r.status_code == 200:
            soup = BeautifulSoup(r.content, 'html.parser')
            # Remove scripts and styles
            for tag in soup(['script', 'style', 'nav', 'footer', 'header']):
                tag.decompose()
            text = soup.get_text(separator=' ', strip=True)
            # Clean up
            text = re.sub(r'\s+', ' ', text)
            return text[:20000]
    except (requests.RequestException, Exception):
        pass
    return ""

def scrape_multiple_pages(website):
    """Scrape main site + common pages."""
    content = []
    
    domain = urlparse(website).netloc
    base = f"https://{domain}"
    
    pages = [
        website,
        f"{base}/",
        f"{base}/about",
        f"{base}/services", 
        f"{base}/products",
        f"{base}/thermoforming",
        f"{base}/leistungen",  # German: services
        f"{base}/produkte",   # German: products
        f"{base}/unternehmen", # German: company
    ]
    
    for url in pages[:5]:
        text = scrape_site(url)
        if text and len(text) > 200:
            content.append(text)
        time.sleep(0.2)
    
    return " ".join(content)[:40000]

def has_relevant_keywords(content):
    """Check if content has relevant keywords."""
    content_lower = content.lower()
    found = sum(1 for kw in KEYWORDS if kw.lower() in content_lower)
    return found >= 2

def extract_data(content, company_name):
    """Aggressive extraction - accept ANY plastic/forming info."""
    if len(content) < 300:
        return None
    
    # Check for keywords first
    if not has_relevant_keywords(content):
        return None
    
    prompt = f"""Analyze this content about "{company_name}". Extract ANY plastics or forming information.

This company may be European - look for German terms like:
- Tiefziehen = thermoforming
- Vakuumformen = vacuum forming  
- Kunststoff = plastic
- Verpackung = packaging
- Leistungen = services

Return JSON:
{{
    "services": ["list ANY plastic forming services"],
    "materials": ["ANY plastics mentioned"],
    "industries": ["industries they serve"],
    "products": ["products they make"],
    "description": "what the company does",
    "confidence": 0.3-1.0
}}

Be GENEROUS - if they mention plastics or forming at all, include it.
Even just "plastic packaging" or "industrial parts" is valuable.

Content:
{content[:25000]}"""

    try:
        r = client.chat.completions.create(
            model="gpt-4o-mini",  # Faster
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=1000,
            response_format={"type": "json_object"}
        )
        data = json.loads(r.choices[0].message.content)
        
        # Accept if ANY data found
        if any([data.get('services'), data.get('materials'), data.get('industries')]):
            if not data.get('services'):
                data['services'] = ['plastic processing']
            if data.get('confidence', 0) < 0.3:
                data['confidence'] = 0.35
            return data
        return None
    except (json.JSONDecodeError, Exception):
        return None

def save(company_id, data):
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    cur.execute("""
        UPDATE market_research.companies SET
            thermoforming_services = %s::jsonb,
            materials = %s::jsonb,
            industries = %s::jsonb,
            applications = %s::jsonb,
            research_summary = %s,
            research_confidence = %s,
            last_researched = NOW()
        WHERE company_id = %s
    """, (
        json.dumps(data.get('services', [])),
        json.dumps(data.get('materials', [])),
        json.dumps(data.get('industries', [])),
        json.dumps(data.get('products', [])),
        data.get('description'),
        data.get('confidence', 0.3),
        company_id
    ))
    conn.commit()
    conn.close()

def research_one(company):
    name = company['name']
    website = company['website']
    
    # Scrape
    content = scrape_multiple_pages(website)
    if not content or len(content) < 300:
        return False, name, 0
    
    # Extract
    data = extract_data(content, name)
    if data:
        save(company['company_id'], data)
        return True, name, data.get('confidence', 0.3)
    
    return False, name, 0

def main():
    companies = get_companies()
    print(f"Euro Scraper: {len(companies)} companies")
    print("=" * 60)
    
    success = 0
    
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(research_one, c): c for c in companies}
        
        for i, future in enumerate(as_completed(futures), 1):
            try:
                ok, name, conf = future.result()
                if ok:
                    success += 1
                    print(f"[{i}/{len(companies)}] ✓ {name[:35]:35} {conf:.0%}")
                else:
                    print(f"[{i}/{len(companies)}] · {name[:35]}")
            except Exception as e:
                print(f"[{i}] ERR: {e}")
    
    # Stats
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
