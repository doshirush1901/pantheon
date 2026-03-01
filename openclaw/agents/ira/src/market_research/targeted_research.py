#!/usr/bin/env python3
"""Targeted research for remaining valid companies."""

import os
import sys
import json
import time
import requests
import psycopg2
import psycopg2.extras
from concurrent.futures import ThreadPoolExecutor, as_completed
from openai import OpenAI
from urllib.parse import quote, urlparse
from pathlib import Path
import warnings
warnings.filterwarnings("ignore")

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

def get_companies():
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT company_id, name, website, email
        FROM market_research.companies
        WHERE is_valid = TRUE
          AND website IS NOT NULL
          AND (thermoforming_services IS NULL OR thermoforming_services = '[]'::jsonb)
        ORDER BY name
    """)
    result = cur.fetchall()
    conn.close()
    return result

def jina_scrape(url, timeout=25):
    try:
        r = requests.get(f"https://r.jina.ai/{url}", timeout=timeout, headers={"Accept": "text/markdown"})
        if r.status_code == 200 and len(r.text) > 200:
            return r.text
    except requests.RequestException:
        pass
    return ""

def jina_search(query, timeout=20):
    try:
        r = requests.get(f"https://s.jina.ai/{quote(query)}", timeout=timeout)
        if r.status_code == 200 and len(r.text) > 300:
            return r.text
    except requests.RequestException:
        pass
    return ""

def deep_scrape(company_name, website):
    """Deep scraping with multiple page attempts."""
    content = []
    
    domain = urlparse(website).netloc.replace("www.", "")
    base = f"https://{domain}"
    
    # Key pages to check
    pages = [
        website,
        f"{base}/",
        f"{base}/thermoforming",
        f"{base}/services",
        f"{base}/products",
        f"{base}/about",
        f"{base}/capabilities",
        f"{base}/vakuumformen",  # German
        f"{base}/tiefziehen",    # German  
        f"{base}/leistungen",    # German services
    ]
    
    for url in pages[:6]:
        text = jina_scrape(url)
        if text and len(text) > 300:
            content.append(f"=== {url} ===\n{text[:10000]}")
            time.sleep(0.3)
    
    # Search for thermoforming info
    searches = [
        f'"{company_name}" thermoforming',
        f'{domain} thermoforming vacuum forming',
    ]
    
    for q in searches[:2]:
        result = jina_search(q)
        if result and len(result) > 500:
            content.append(f"=== SEARCH: {q} ===\n{result[:6000]}")
        time.sleep(0.3)
    
    return "\n\n".join(content)

def extract_data(content, company_name):
    """LLM extraction - generous with partial data."""
    if len(content) < 400:
        return None
    
    prompt = f"""Analyze content about "{company_name}" and extract thermoforming/plastic forming info.

Look for ANY of these:
- Thermoforming, vacuum forming, pressure forming, twin-sheet forming
- Plastic materials (ABS, HDPE, PS, PP, PVC, PETG, PC, etc.)
- Industries served (automotive, medical, packaging, aerospace, etc.)
- Products made (trays, covers, enclosures, housings, etc.)

Return JSON:
{{
    "services": ["list thermoforming services found"],
    "materials": ["plastics mentioned"],
    "industries": ["industries served"],
    "products": ["products/applications"],
    "description": "brief summary",
    "confidence": 0.1-1.0
}}

Be generous - if they do ANY plastic forming, include it. Even minimal info is valuable.
Set confidence >= 0.3 if they mention plastic forming/thermoforming at all.

Content:
{content[:30000]}"""

    try:
        r = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=1200,
            response_format={"type": "json_object"}
        )
        data = json.loads(r.choices[0].message.content)
        # Accept if we found ANY relevant info
        if any([data.get('services'), data.get('materials'), data.get('industries'), data.get('products')]):
            if not data.get('services'):
                data['services'] = ['plastic forming']
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
    
    content = deep_scrape(name, website)
    if not content:
        return False, name, 0
    
    data = extract_data(content, name)
    if data:
        save(company['company_id'], data)
        return True, name, data.get('confidence', 0.3)
    
    return False, name, 0

def main():
    companies = get_companies()
    print(f"Researching {len(companies)} companies...")
    print("=" * 60)
    
    success = 0
    
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {executor.submit(research_one, c): c for c in companies}
        
        for i, future in enumerate(as_completed(futures), 1):
            try:
                ok, name, conf = future.result()
                if ok:
                    success += 1
                    print(f"[{i}/{len(companies)}] ✓ {name[:35]:35} conf={conf:.0%}")
                else:
                    print(f"[{i}/{len(companies)}] · {name[:35]}")
            except Exception as e:
                print(f"[{i}] ERROR: {e}")
    
    # Final stats
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    cur.execute("""
        SELECT 
            COUNT(*) FILTER (WHERE is_valid) as valid,
            COUNT(*) FILTER (WHERE is_valid AND thermoforming_services IS NOT NULL AND thermoforming_services != '[]'::jsonb) as with_data
        FROM market_research.companies
    """)
    v, d = cur.fetchone()
    conn.close()
    
    print()
    print("=" * 60)
    print(f"SUCCESS: +{success} companies")
    print(f"TOTAL: {d}/{v} valid companies ({d*100//v}%)")
    print("=" * 60)

if __name__ == '__main__':
    main()
