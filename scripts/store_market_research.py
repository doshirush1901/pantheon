#!/usr/bin/env python3
"""Store market research data in Ira's knowledge base for RAG retrieval."""

import os
import sys
import json
import hashlib
import psycopg2
import psycopg2.extras
from pathlib import Path

# Import from centralized config
SCRIPTS_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPTS_DIR.parent
AGENT_DIR = PROJECT_ROOT / "openclaw" / "agents" / "ira"
sys.path.insert(0, str(AGENT_DIR))

try:
    from config import (
        DATABASE_URL, QDRANT_URL, VOYAGE_API_KEY,
        COLLECTIONS, EMBEDDING_MODEL_VOYAGE,
    )
    CONFIG_LOADED = True
except ImportError:
    CONFIG_LOADED = False
    # Fallback to direct env loading
    env_file = PROJECT_ROOT / '.env'
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if line.strip() and not line.startswith('#') and '=' in line:
                key, _, value = line.partition('=')
                os.environ.setdefault(key.strip(), value.strip().strip('"'))
    
    DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://ira:ira_password@localhost:5432/ira_db")
    QDRANT_URL = os.getenv('QDRANT_URL', 'http://localhost:6333')
    VOYAGE_API_KEY = os.getenv('VOYAGE_API_KEY')
    COLLECTIONS = {"market_research": "ira_market_research_voyage"}
    EMBEDDING_MODEL_VOYAGE = "voyage-3"

from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, VectorParams, Distance
import voyageai

# Use centralized config values
DB_URL = DATABASE_URL
voyage_client = voyageai.Client(api_key=VOYAGE_API_KEY)
qdrant = QdrantClient(url=QDRANT_URL)

COLLECTION_NAME = COLLECTIONS.get("market_research", "ira_market_research_voyage")
EMBEDDING_DIM = 1024

def get_embedding(text: str) -> list:
    """Get embedding using Voyage AI."""
    result = voyage_client.embed([text[:8000]], model="voyage-3")
    return result.embeddings[0]

def get_market_research_data():
    """Get all market research data."""
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT 
            company_id, name, website, country, email,
            thermoforming_services, materials, industries, applications,
            research_summary, research_confidence
        FROM market_research.companies
        WHERE is_valid = TRUE
          AND thermoforming_services IS NOT NULL 
          AND thermoforming_services != '[]'::jsonb
    """)
    companies = cur.fetchall()
    conn.close()
    return companies

def format_company_text(company: dict) -> str:
    """Format company data as searchable text."""
    def json_to_list(val):
        if isinstance(val, list):
            return val
        if isinstance(val, str):
            try:
                return json.loads(val)
            except:
                return []
        return []
    
    services = json_to_list(company.get('thermoforming_services', []))
    materials = json_to_list(company.get('materials', []))
    industries = json_to_list(company.get('industries', []))
    products = json_to_list(company.get('applications', []))
    
    text = f"""Company: {company['name']}
Website: {company.get('website', 'N/A')}
Country: {company.get('country', 'N/A')}
Email: {company.get('email', 'N/A')}

Thermoforming Services: {', '.join(services) if services else 'N/A'}
Materials: {', '.join(materials) if materials else 'N/A'}
Industries Served: {', '.join(industries) if industries else 'N/A'}
Products/Applications: {', '.join(products) if products else 'N/A'}

Summary: {company.get('research_summary') or 'N/A'}
"""
    return text.strip()

def ensure_collection():
    """Ensure Qdrant collection exists."""
    collections = [c.name for c in qdrant.get_collections().collections]
    if COLLECTION_NAME not in collections:
        qdrant.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=EMBEDDING_DIM, distance=Distance.COSINE)
        )
        print(f"Created collection: {COLLECTION_NAME}")
    else:
        print(f"Collection exists: {COLLECTION_NAME}")

def store_in_knowledge_base():
    """Store market research in Ira's knowledge base using Voyage AI."""
    companies = get_market_research_data()
    print(f"Storing {len(companies)} companies in Ira's knowledge base...")
    print(f"Using Voyage AI for embeddings (1024 dimensions)")
    
    # Ensure Qdrant collection
    ensure_collection()
    
    # Store each company
    points = []
    
    for i, company in enumerate(companies):
        text = format_company_text(company)
        # Use hash of company_id for Qdrant point ID
        chunk_id = abs(hash(str(company['company_id']))) % (10**9)
        
        # Get embedding
        try:
            embedding = get_embedding(text)
            
            # Get services/industries as lists
            services = company.get('thermoforming_services', [])
            if isinstance(services, str):
                services = json.loads(services) if services else []
            industries = company.get('industries', [])
            if isinstance(industries, str):
                industries = json.loads(industries) if industries else []
            
            points.append(PointStruct(
                id=chunk_id,
                vector=embedding,
                payload={
                    "source": "market_research",
                    "chunk_type": "company_profile",
                    "company_id": company['company_id'],
                    "company_name": company['name'],
                    "website": company.get('website', ''),
                    "country": company.get('country', ''),
                    "content": text,
                    "services": services,
                    "industries": industries,
                }
            ))
        except Exception as e:
            print(f"  Error {company['name']}: {e}")
            continue
        
        if (i + 1) % 20 == 0:
            print(f"  Embedded {i + 1}/{len(companies)}")
    
    # Upload to Qdrant in batches
    print(f"\nUploading {len(points)} vectors to Qdrant...")
    batch_size = 50
    for i in range(0, len(points), batch_size):
        batch = points[i:i+batch_size]
        try:
            qdrant.upsert(collection_name=COLLECTION_NAME, points=batch)
        except Exception as e:
            print(f"  Qdrant error: {e}")
    
    print(f"\n{'='*60}")
    print(f"Done! {len(points)} companies stored in Ira's RAG")
    print(f"Collection: {COLLECTION_NAME}")
    print(f"{'='*60}")
    print("\nIra can now semantically search for:")
    print("  - 'Which companies do vacuum forming?'")
    print("  - 'Find thermoforming companies in Germany'")
    print("  - 'Who serves the automotive industry?'")

if __name__ == '__main__':
    store_in_knowledge_base()
