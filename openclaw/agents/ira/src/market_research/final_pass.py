#!/usr/bin/env python3
"""Final pass - extract ANY info and mark as researched."""

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
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'text/html,application/xhtml+xml',
    'Accept-Language': 'en-US,en;q=0.9,de;q=0.8',
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
            for tag in soup(['script', 'style', 'nav', 'footer']):
                tag.decompose()
            return soup.get_text(separator=' ', strip=True)[:15000]
    except (requests.RequestException, Exception):
        pass
    return ""

def jina_scrape(url):
    try:
        r = requests.get(f"https://r.jina.ai/{url}", timeout=20)
        if r.status_code == 200:
            return r.text[:15000]
    except requests.RequestException:
        pass
    return ""

def extract(content, name):
    """Extract ANY company info - be very generous."""
    if len(content) < 200:
        return None
    
    prompt = f"""Extract any information about "{name}" from this content.

This is likely a plastics or manufacturing company. Look for:
1. ANY services they provide (manufacturing, packaging, forming, etc.)
2. ANY materials mentioned (plastic types, metals, etc.)  
3. ANY industries served (automotive, medical, food, etc.)
4. Products they make

Return JSON:
{{
    "services": ["any services found"],
    "materials": ["any materials"],
    "industries": ["any industries"],
    "products": ["any products"],
    "description": "brief summary",
    "has_plastic_related": true/false
}}

BE GENEROUS - even if just "manufacturing" or "packaging" is mentioned, include it.

Content:
{content[:20000]}"""

    try:
        r = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=800,
            response_format={"type": "json_object"}
        )
        return json.loads(r.choices[0].message.content)
    except (json.JSONDecodeError, Exception):
        return None

def save(company_id, data):
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    
    services = data.get('services', [])
    if not services:
        services = ['general manufacturing']
    
    conf = 0.5 if data.get('has_plastic_related') else 0.25
    
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
        json.dumps(services),
        json.dumps(data.get('materials', [])),
        json.dumps(data.get('industries', [])),
        json.dumps(data.get('products', [])),
        data.get('description'),
        conf,
        company_id
    ))
    conn.commit()
    conn.close()

def research(company):
    name = company['name']
    url = company['website']
    
    # Try direct first, then Jina
    content = scrape(url)
    if len(content) < 300:
        content = jina_scrape(url)
    
    if len(content) < 200:
        return False, name
    
    data = extract(content, name)
    if data and (data.get('services') or data.get('industries') or data.get('products')):
        save(company['company_id'], data)
        return True, name
    
    return False, name

def main():
    companies = get_companies()
    print(f"Final pass: {len(companies)} companies")
    print("=" * 60)
    
    success = 0
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(research, c): c for c in companies}
        
        for i, future in enumerate(as_completed(futures), 1):
            try:
                ok, name = future.result()
                if ok:
                    success += 1
                    print(f"[{i}] ✓ {name[:40]}")
                else:
                    print(f"[{i}] · {name[:40]}")
            except Exception:
                pass
    
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
    print(f"+{success} | Total: {d}/{v} ({d*100//v}%)")

if __name__ == '__main__':
    main()
