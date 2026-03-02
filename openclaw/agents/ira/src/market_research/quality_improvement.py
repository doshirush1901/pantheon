#!/usr/bin/env python3
"""
Quality Improvement Pass - Fix URLs, re-research low confidence, add enrichment.
"""

import os
import sys
import json
import re
import time
import asyncio
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse, urljoin
from pathlib import Path
import warnings

import requests
import psycopg2
import psycopg2.extras
from openai import OpenAI

warnings.filterwarnings('ignore')

# Import from centralized config
MARKET_RESEARCH_DIR = Path(__file__).parent
SKILLS_DIR = MARKET_RESEARCH_DIR.parent
AGENT_DIR = SKILLS_DIR.parent
sys.path.insert(0, str(AGENT_DIR))

try:
    from config import DATABASE_URL, OPENAI_API_KEY
except ImportError:
    DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://ira:ira_password@localhost:5432/ira_db')
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

PROXYCURL_API_KEY = os.getenv('PROXYCURL_API_KEY', '')

class QualityImprover:
    """Improve research quality through multiple strategies."""
    
    def __init__(self):
        self.conn = psycopg2.connect(DATABASE_URL)
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
    
    def get_companies_needing_improvement(self) -> Dict[str, List[Dict]]:
        """Categorize companies by what they need."""
        cur = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Bad URLs (youtube, linkedin, facebook, email domains)
        cur.execute("""
            SELECT company_id, name, website, email, country
            FROM market_research.companies
            WHERE website LIKE '%%youtube%%' 
               OR website LIKE '%%linkedin%%'
               OR website LIKE '%%facebook%%'
               OR website LIKE '%%hotmail%%'
               OR website LIKE '%%gmail%%'
               OR website LIKE '%%aol.com%%'
               OR website LIKE '%%yahoo%%'
        """)
        bad_urls = cur.fetchall()
        
        # No website
        cur.execute("""
            SELECT company_id, name, email, country
            FROM market_research.companies
            WHERE website IS NULL
        """)
        no_website = cur.fetchall()
        
        # Low confidence (researched but poor results)
        cur.execute("""
            SELECT company_id, name, website, country
            FROM market_research.companies
            WHERE last_researched IS NOT NULL
              AND (research_confidence < 0.3 
                   OR (thermoforming_services IS NULL OR thermoforming_services = '[]'::jsonb))
              AND website IS NOT NULL
              AND website NOT LIKE '%%youtube%%'
              AND website NOT LIKE '%%linkedin%%'
        """)
        low_confidence = cur.fetchall()
        
        return {
            'bad_urls': bad_urls,
            'no_website': no_website,
            'low_confidence': low_confidence
        }
    
    def search_company_website(self, company_name: str, country: str = None, email: str = None) -> Optional[str]:
        """Search for a company's real website using multiple strategies."""
        
        # Strategy 1: Extract domain from email
        if email and '@' in email:
            domain = email.split('@')[1]
            if domain not in ['gmail.com', 'yahoo.com', 'hotmail.com', 'aol.com', 'outlook.com']:
                test_url = f"https://www.{domain}"
                if self._is_valid_website(test_url):
                    return test_url
                test_url = f"https://{domain}"
                if self._is_valid_website(test_url):
                    return test_url
        
        # Strategy 2: DuckDuckGo search
        search_queries = [
            f"{company_name} thermoforming",
            f"{company_name} vacuum forming company",
            f"{company_name} plastics {country}" if country else f"{company_name} plastics",
        ]
        
        for query in search_queries:
            url = self._duckduckgo_search(query)
            if url:
                return url
        
        # Strategy 3: Direct domain guessing
        clean_name = re.sub(r'[^a-zA-Z0-9]', '', company_name.lower())
        guesses = [
            f"https://www.{clean_name}.com",
            f"https://www.{clean_name}.de",
            f"https://www.{clean_name}.co.uk",
            f"https://{clean_name}.com",
        ]
        
        for guess in guesses:
            if self._is_valid_website(guess):
                return guess
        
        return None
    
    def _duckduckgo_search(self, query: str) -> Optional[str]:
        """Search DuckDuckGo and return first relevant result."""
        try:
            # Use DuckDuckGo HTML version
            resp = self.session.get(
                'https://html.duckduckgo.com/html/',
                params={'q': query},
                timeout=10
            )
            
            if resp.status_code == 200:
                # Extract URLs from results
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(resp.text, 'html.parser')
                
                for link in soup.select('a.result__a'):
                    href = link.get('href', '')
                    # DuckDuckGo wraps URLs
                    if 'uddg=' in href:
                        import urllib.parse
                        parsed = urllib.parse.parse_qs(urllib.parse.urlparse(href).query)
                        if 'uddg' in parsed:
                            url = parsed['uddg'][0]
                            # Filter out bad results
                            if not any(bad in url.lower() for bad in ['youtube', 'linkedin', 'facebook', 'wikipedia', 'amazon']):
                                if self._is_valid_website(url):
                                    return url
        except Exception as e:
            pass
        
        return None
    
    def _is_valid_website(self, url: str) -> bool:
        """Check if URL is a valid, accessible website."""
        try:
            resp = self.session.head(url, timeout=5, allow_redirects=True)
            return resp.status_code < 400
        except (requests.RequestException, Exception):
            return False
    
    def deep_research_with_search(self, company: Dict) -> Dict[str, Any]:
        """Research a company using targeted search queries."""
        name = company['name']
        website = company.get('website')
        
        # Scrape with Jina
        content_parts = []
        sources = []
        
        # If we have a website, scrape it
        if website:
            content, success = self._jina_read(website)
            if success:
                content_parts.append(f"=== MAIN WEBSITE ===\n{content}")
                sources.append(website)
            
            # Try common subpages
            for suffix in ['/about', '/services', '/thermoforming', '/products', '/capabilities']:
                base = urlparse(website)
                subpage = f"{base.scheme}://{base.netloc}{suffix}"
                content, success = self._jina_read(subpage)
                if success and len(content) > 500:
                    content_parts.append(f"=== {suffix.upper()} PAGE ===\n{content}")
                    sources.append(subpage)
                time.sleep(0.3)
        
        # Search for additional info
        search_queries = [
            f"{name} thermoforming machines equipment",
            f"{name} vacuum forming capabilities",
        ]
        
        for query in search_queries:
            search_url = f"https://r.jina.ai/https://html.duckduckgo.com/html/?q={requests.utils.quote(query)}"
            try:
                resp = self.session.get(search_url, timeout=15)
                if resp.status_code == 200 and len(resp.text) > 500:
                    content_parts.append(f"=== SEARCH: {query} ===\n{resp.text[:5000]}")
            except requests.RequestException:
                pass
            time.sleep(0.5)
        
        if not content_parts:
            return {'success': False}
        
        # Extract with LLM
        combined_content = "\n\n".join(content_parts)[:40000]
        extracted = self._extract_with_llm(combined_content, name)
        
        if extracted:
            extracted['sources'] = sources
            extracted['success'] = True
            return extracted
        
        return {'success': False}
    
    def _jina_read(self, url: str) -> Tuple[str, bool]:
        """Read URL with Jina Reader."""
        try:
            resp = self.session.get(f"https://r.jina.ai/{url}", timeout=20)
            if resp.status_code == 200 and len(resp.text) > 200:
                return resp.text, True
        except requests.RequestException:
            pass
        return "", False
    
    def _extract_with_llm(self, content: str, company_name: str) -> Optional[Dict]:
        """Extract structured data with GPT-4o."""
        prompt = """Extract thermoforming company information. Be thorough and extract ALL mentioned details.

Return JSON:
{
    "thermoforming_services": ["list ALL services: vacuum forming, pressure forming, twin-sheet, etc."],
    "machine_brands": ["Kiefel", "Illig", "Geiss", "Brown", etc. - list ALL mentioned"],
    "machine_models": ["specific model numbers/names"],
    "machine_count": number or null,
    "max_sheet_size": "dimensions if mentioned",
    "materials": ["ABS", "HDPE", "PC", etc.],
    "industries": ["automotive", "medical", "aerospace", etc.],
    "applications": ["specific products they make"],
    "employees": number or null,
    "established_year": number or null,
    "certifications": ["ISO", "FDA", etc.],
    "summary": "2-3 sentence company summary focusing on thermoforming capabilities",
    "confidence": 0.0-1.0
}

Company: {company_name}

Content:
{content}"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "Extract factual information only. Be thorough."},
                    {"role": "user", "content": prompt.format(company_name=company_name, content=content)}
                ],
                temperature=0.1,
                max_tokens=2000,
                response_format={"type": "json_object"}
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            print(f"  LLM error: {e}")
            return None
    
    def update_company(self, company_id: str, data: Dict):
        """Update company with new research data."""
        cur = self.conn.cursor()
        
        services = data.get('thermoforming_services', [])
        machines = data.get('machine_brands', []) + data.get('machine_models', [])
        
        cur.execute("""
            UPDATE market_research.companies SET
                thermoforming_services = %s::jsonb,
                machine_models = %s::jsonb,
                machine_count = COALESCE(%s, machine_count),
                max_part_size = COALESCE(%s, max_part_size),
                materials = %s::jsonb,
                industries = %s::jsonb,
                applications = %s::jsonb,
                employees = COALESCE(%s, employees),
                established_year = COALESCE(%s, established_year),
                research_summary = COALESCE(%s, research_summary),
                research_confidence = GREATEST(COALESCE(research_confidence, 0), %s),
                research_sources = %s::jsonb,
                last_researched = NOW(),
                updated_at = NOW()
            WHERE company_id = %s
        """, (
            json.dumps(services),
            json.dumps(machines),
            data.get('machine_count'),
            data.get('max_sheet_size'),
            json.dumps(data.get('materials', [])),
            json.dumps(data.get('industries', [])),
            json.dumps(data.get('applications', [])),
            data.get('employees'),
            data.get('established_year'),
            data.get('summary'),
            data.get('confidence', 0),
            json.dumps(data.get('sources', [])),
            company_id
        ))
        self.conn.commit()
    
    def update_website(self, company_id: str, new_website: str):
        """Update company website."""
        cur = self.conn.cursor()
        cur.execute("""
            UPDATE market_research.companies 
            SET website = %s, updated_at = NOW()
            WHERE company_id = %s
        """, (new_website, company_id))
        self.conn.commit()
    
    def run_improvement_pass(self):
        """Run full quality improvement."""
        print("\n" + "="*60)
        print("QUALITY IMPROVEMENT PASS")
        print("="*60 + "\n")
        
        categories = self.get_companies_needing_improvement()
        
        print(f"Companies needing improvement:")
        print(f"  - Bad URLs: {len(categories['bad_urls'])}")
        print(f"  - No website: {len(categories['no_website'])}")
        print(f"  - Low confidence: {len(categories['low_confidence'])}")
        print()
        
        # Phase 1: Fix bad URLs
        print("PHASE 1: Fixing bad URLs...")
        fixed_urls = 0
        for company in categories['bad_urls']:
            print(f"  Finding website for: {company['name']}")
            new_url = self.search_company_website(
                company['name'], 
                company.get('country'),
                company.get('email')
            )
            if new_url:
                self.update_website(company['company_id'], new_url)
                print(f"    ✓ Found: {new_url}")
                fixed_urls += 1
            else:
                print(f"    ✗ Not found")
            time.sleep(1)
        
        print(f"\n  Fixed {fixed_urls}/{len(categories['bad_urls'])} URLs\n")
        
        # Phase 2: Find websites for companies without
        print("PHASE 2: Finding missing websites...")
        found_websites = 0
        for company in categories['no_website'][:50]:  # Limit to 50
            # Skip weird entries
            if len(company['name']) > 100 or 'verify' in company['name'].lower():
                continue
            print(f"  Searching for: {company['name']}")
            new_url = self.search_company_website(
                company['name'],
                company.get('country'),
                company.get('email')
            )
            if new_url and len(new_url) < 400:
                self.update_website(company['company_id'], new_url)
                print(f"    ✓ Found: {new_url}")
                found_websites += 1
            else:
                print(f"    ✗ Not found")
            time.sleep(1)
        
        print(f"\n  Found {found_websites}/{len(categories['no_website'])} websites\n")
        
        # Phase 3: Re-research low confidence with better strategies
        print("PHASE 3: Re-researching low confidence companies...")
        improved = 0
        
        def research_single(company):
            result = self.deep_research_with_search(company)
            if result.get('success') and result.get('confidence', 0) > 0.3:
                self.update_company(company['company_id'], result)
                return True, company['name'], result.get('confidence', 0)
            return False, company['name'], 0
        
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {executor.submit(research_single, c): c for c in categories['low_confidence'][:100]}
            
            for i, future in enumerate(as_completed(futures), 1):
                success, name, conf = future.result()
                if success:
                    improved += 1
                    print(f"  [{i}] ✓ {name} (confidence: {conf:.0%})")
                else:
                    print(f"  [{i}] ✗ {name}")
        
        print(f"\n  Improved {improved}/{len(categories['low_confidence'][:100])} companies\n")
        
        # Final stats
        cur = self.conn.cursor()
        cur.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE last_researched IS NOT NULL) as researched,
                COUNT(*) FILTER (WHERE research_confidence > 0.5) as high_conf,
                COUNT(*) FILTER (WHERE thermoforming_services IS NOT NULL AND thermoforming_services != '[]'::jsonb) as with_data
            FROM market_research.companies
        """)
        stats = cur.fetchone()
        
        print("="*60)
        print("IMPROVEMENT COMPLETE")
        print("="*60)
        print(f"  Total Companies:     {stats[0]}")
        print(f"  Researched:          {stats[1]}")
        print(f"  High Confidence:     {stats[2]}")
        print(f"  With Data:           {stats[3]}")
        print("="*60 + "\n")


def get_linkedin_data(company_name: str, website: str = None) -> Dict:
    """Get LinkedIn company data via Proxycurl."""
    if not PROXYCURL_API_KEY:
        return {}
    
    try:
        # First find LinkedIn URL
        headers = {'Authorization': f'Bearer {PROXYCURL_API_KEY}'}
        
        # Search for company
        resp = requests.get(
            'https://nubela.co/proxycurl/api/linkedin/company/resolve',
            params={'company_domain': urlparse(website).netloc if website else None, 'company_name': company_name},
            headers=headers,
            timeout=10
        )
        
        if resp.status_code == 200:
            linkedin_url = resp.json().get('url')
            if linkedin_url:
                # Get company data
                resp2 = requests.get(
                    'https://nubela.co/proxycurl/api/linkedin/company',
                    params={'url': linkedin_url},
                    headers=headers,
                    timeout=10
                )
                if resp2.status_code == 200:
                    data = resp2.json()
                    return {
                        'employees': data.get('company_size_on_linkedin'),
                        'industry': data.get('industry'),
                        'founded_year': data.get('founded_year'),
                        'linkedin_url': linkedin_url
                    }
    except (requests.RequestException, json.JSONDecodeError, KeyError):
        pass
    
    return {}


if __name__ == '__main__':
    improver = QualityImprover()
    improver.run_improvement_pass()
