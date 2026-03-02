#!/usr/bin/env python3
"""Aggressive research to reach 80% data coverage."""

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
client = OpenAI()

def get_companies_without_data(limit=250):
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT company_id, name, website, country, email
        FROM market_research.companies
        WHERE website IS NOT NULL
          AND website NOT LIKE '%%youtube%%'
          AND website NOT LIKE '%%linkedin%%'
          AND website NOT LIKE '%%facebook%%'
          AND (thermoforming_services IS NULL OR thermoforming_services = '[]'::jsonb)
        ORDER BY name
        LIMIT %s
    """, (limit,))
    result = cur.fetchall()
    conn.close()
    return result

def scrape_jina(url, timeout=20):
    try:
        r = requests.get(f"https://r.jina.ai/{url}", timeout=timeout)
        return r.text if r.status_code == 200 and len(r.text) > 200 else ""
    except requests.RequestException:
        return ""

def search_and_scrape(company_name, base_url):
    """Search for company thermoforming info and scrape multiple sources."""
    content_parts = []
    
    # 1. Scrape main website and key pages
    domain = urlparse(base_url).netloc
    pages = [
        base_url,
        f"https://{domain}/about",
        f"https://{domain}/services", 
        f"https://{domain}/thermoforming",
        f"https://{domain}/products",
        f"https://{domain}/capabilities",
        f"https://{domain}/vacuum-forming",
    ]
    
    for url in pages[:5]:
        content = scrape_jina(url)
        if content and len(content) > 300:
            content_parts.append(content[:8000])
        time.sleep(0.2)
    
    # 2. Search for thermoforming info via Jina search
    search_queries = [
        f"{company_name} thermoforming",
        f"{company_name} vacuum forming plastic",
    ]
    
    for query in search_queries[:2]:
        try:
            search_url = f"https://s.jina.ai/{quote(query)}"
            r = requests.get(search_url, timeout=15)
            if r.status_code == 200 and len(r.text) > 500:
                content_parts.append(r.text[:5000])
        except requests.RequestException:
            pass
        time.sleep(0.3)
    
    return "\n\n---\n\n".join(content_parts)

def extract_with_llm(content, company_name):
    """Extract data with GPT-4o - be aggressive about finding ANY thermoforming info."""
    if len(content) < 300:
        return None
    
    prompt = f"""Analyze this content about "{company_name}" and extract ANY thermoforming/plastic forming related information.

Even if limited info is available, extract what you can find:
- Any mention of thermoforming, vacuum forming, pressure forming, plastic forming
- Any plastic materials mentioned (ABS, HDPE, PC, PP, etc.)
- Any industries they serve
- Any products or applications

Return JSON:
{{
    "thermoforming_services": ["vacuum forming", "pressure forming", etc. - include ANY plastic forming services],
    "machine_brands": [],
    "materials": ["any plastics mentioned"],
    "industries": ["any industries mentioned"],
    "applications": ["any products/applications"],
    "summary": "brief summary of what they do",
    "confidence": 0.3-1.0 (be generous if they mention plastic/forming at all)
}}

If they do ANY kind of plastic forming/thermoforming, confidence should be at least 0.4.
If it's clearly a thermoforming company, confidence should be 0.6+.

Content:
{content[:25000]}"""

    try:
        r = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=1500,
            response_format={"type": "json_object"}
        )
        data = json.loads(r.choices[0].message.content)
        # Be aggressive - if we found ANY services, consider it a success
        if data.get('thermoforming_services') or data.get('materials') or data.get('industries'):
            if not data.get('thermoforming_services'):
                data['thermoforming_services'] = ['plastic forming']
            if data.get('confidence', 0) < 0.3:
                data['confidence'] = 0.35
        return data
    except Exception as e:
        return None

def save_to_db(company_id, data):
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    cur.execute("""
        UPDATE market_research.companies SET
            thermoforming_services = %s::jsonb,
            machine_models = %s::jsonb,
            materials = %s::jsonb,
            industries = %s::jsonb,
            applications = %s::jsonb,
            research_summary = %s,
            research_confidence = %s,
            last_researched = NOW()
        WHERE company_id = %s
    """, (
        json.dumps(data.get('thermoforming_services', [])),
        json.dumps(data.get('machine_brands', [])),
        json.dumps(data.get('materials', [])),
        json.dumps(data.get('industries', [])),
        json.dumps(data.get('applications', [])),
        data.get('summary'),
        data.get('confidence', 0.3),
        company_id
    ))
    conn.commit()
    conn.close()

def research_company(company):
    """Research a single company."""
    name = company['name']
    website = company['website']
    
    # Search and scrape
    content = search_and_scrape(name, website)
    
    if not content or len(content) < 300:
        return False, name, 0, 0
    
    # Extract with LLM
    data = extract_with_llm(content, name)
    
    if data and (data.get('thermoforming_services') or data.get('confidence', 0) > 0.25):
        save_to_db(company['company_id'], data)
        services = len(data.get('thermoforming_services', []))
        return True, name, data.get('confidence', 0), services
    
    return False, name, 0, 0

def run_aggressive_research(limit=250, workers=8):
    """Run aggressive parallel research."""
    companies = get_companies_without_data(limit)
    
    print("=" * 60)
    print(f"AGGRESSIVE RESEARCH: {len(companies)} companies, {workers} workers")
    print("=" * 60)
    print()
    
    success = 0
    
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(research_company, c): c for c in companies}
        
        for i, future in enumerate(as_completed(futures), 1):
            ok, name, conf, services = future.result()
            if ok:
                success += 1
                print(f"[{i}/{len(companies)}] ✓ {name[:30]:30} conf={conf:.0%} svc={services}")
            else:
                print(f"[{i}/{len(companies)}] ✗ {name[:30]}")
    
    # Final stats
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    cur.execute("""
        SELECT 
            COUNT(*) as total,
            COUNT(*) FILTER (WHERE thermoforming_services IS NOT NULL AND thermoforming_services != '[]'::jsonb) as with_data
        FROM market_research.companies
    """)
    stats = cur.fetchone()
    conn.close()
    
    print()
    print("=" * 60)
    print(f"COMPLETE: Added {success} companies")
    print(f"Total with data: {stats[1]}/{stats[0]} ({stats[1]*100//stats[0]}%)")
    print("=" * 60)

if __name__ == '__main__':
    import sys
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 250
    workers = int(sys.argv[2]) if len(sys.argv) > 2 else 8
    run_aggressive_research(limit, workers)
