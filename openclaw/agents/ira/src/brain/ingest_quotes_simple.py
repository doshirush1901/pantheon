#!/usr/bin/env python3
"""
SIMPLE QUOTES INGESTION - Direct to Qdrant
==========================================

Minimal memory footprint, direct ingestion without graph overhead.
"""

import os
import sys
import re
import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
import uuid

BRAIN_DIR = Path(__file__).parent
SKILLS_DIR = BRAIN_DIR.parent
AGENT_DIR = SKILLS_DIR.parent
PROJECT_ROOT = AGENT_DIR.parent.parent.parent

sys.path.insert(0, str(AGENT_DIR))
sys.path.insert(0, str(BRAIN_DIR))

# Import from centralized config
try:
    from config import QDRANT_URL, QDRANT_API_KEY, VOYAGE_API_KEY, get_logger
    CONFIG_AVAILABLE = True
except ImportError:
    CONFIG_AVAILABLE = False
    # Fallback: Load environment manually
    env_file = PROJECT_ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if line.strip() and not line.startswith('#') and '=' in line:
                key, _, value = line.partition('=')
                os.environ.setdefault(key.strip(), value.strip().strip('"'))
    QDRANT_URL = os.environ.get("QDRANT_URL", "")
    QDRANT_API_KEY = os.environ.get("QDRANT_API_KEY", "")
    VOYAGE_API_KEY = os.environ.get("VOYAGE_API_KEY", "")

from document_extractor import extract_pdf

QUOTES_DIR = PROJECT_ROOT / "data" / "imports" / "Quotes"
OUTPUT_JSON = PROJECT_ROOT / "data" / "quotes_knowledge.json"
HASH_FILE = PROJECT_ROOT / "data" / "quotes_ingested_hashes.json"
COLLECTION_NAME = "ira_discovered_knowledge"

MACHINE_PATTERNS = [
    r'PF1-[A-Z]?-?\d{4}',
    r'PF1-\d{4}',
    r'AM-[A-Z]?-?\d{4}',
    r'ATF-\d{4}',
    r'RT-\d[A-Z]-\d{4}',
    r'IMG-\d{4}',
]


def extract_machines(text: str) -> List[str]:
    machines = set()
    for pattern in MACHINE_PATTERNS:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            machines.add(match.upper())
    return list(machines)


def classify_document(filename: str) -> str:
    f = filename.lower()
    if 'gmail' in f:
        if 'inquiry' in f or 'enquiry' in f or 'request' in f:
            return 'customer_inquiry'
        elif 'offer' in f:
            return 'sales_offer'
        elif 'order' in f:
            return 'purchase_order'
        return 'email_conversation'
    elif 'quote' in f or 'quotation' in f or 'offer' in f:
        return 'machine_quote'
    elif 'price' in f:
        return 'price_list'
    return 'general_document'


def load_hashes() -> set:
    if HASH_FILE.exists():
        return set(json.loads(HASH_FILE.read_text()))
    return set()


def save_hashes(hashes: set):
    HASH_FILE.write_text(json.dumps(list(hashes), indent=2))


def get_embeddings(texts: List[str]) -> List[List[float]]:
    """Get embeddings from VoyageAI."""
    import voyageai
    
    client = voyageai.Client(api_key=VOYAGE_API_KEY)
    result = client.embed(texts, model="voyage-3", input_type="document")
    return result.embeddings


def store_to_qdrant(items: List[Dict]) -> int:
    """Store items directly to Qdrant."""
    from qdrant_client import QdrantClient
    from qdrant_client.models import PointStruct, VectorParams, Distance
    
    qdrant = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
    
    try:
        qdrant.get_collection(COLLECTION_NAME)
    except Exception:
        qdrant.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=1024, distance=Distance.COSINE),
        )
        print(f"  Created collection: {COLLECTION_NAME}", flush=True)
    
    points = []
    for item in items:
        point = PointStruct(
            id=str(uuid.uuid4()),
            vector=item["embedding"],
            payload={
                "text": item["text"][:5000],
                "raw_text": item["text"][:5000],
                "doc_type": item["doc_type"],
                "machines": item["machines"],
                "filename": item["filename"],
                "source_file": item["filename"],
                "knowledge_type": item["knowledge_type"],
                "indexed_at": datetime.now().isoformat(),
            }
        )
        points.append(point)
    
    if points:
        qdrant.upsert(collection_name=COLLECTION_NAME, points=points)
    
    return len(points)


def main():
    print("=" * 60, flush=True)
    print("SIMPLE QUOTES INGESTION", flush=True)
    print("=" * 60, flush=True)
    
    if not QUOTES_DIR.exists():
        print(f"✗ Directory not found: {QUOTES_DIR}", flush=True)
        return
    
    pdf_files = list(QUOTES_DIR.glob("*.pdf"))
    print(f"Found {len(pdf_files)} PDF files\n", flush=True)
    
    ingested_hashes = load_hashes()
    
    extracted_items = []
    skipped = 0
    failed = 0
    
    for idx, pdf_path in enumerate(pdf_files):
        print(f"[{idx+1}/{len(pdf_files)}] {pdf_path.name[:50]}...", flush=True)
        
        try:
            text = extract_pdf(pdf_path)
            if not text or len(text) < 50:
                print(f"  ⚠ No text extracted", flush=True)
                failed += 1
                continue
            
            content_hash = hashlib.sha256(text[:2000].encode()).hexdigest()[:16]
            if content_hash in ingested_hashes:
                print(f"  ○ Skipped (duplicate)", flush=True)
                skipped += 1
                continue
            
            doc_type = classify_document(pdf_path.name)
            machines = extract_machines(text)
            
            extracted_items.append({
                "text": text[:5000],
                "doc_type": doc_type,
                "machines": machines,
                "filename": pdf_path.name,
                "knowledge_type": "customer" if doc_type.startswith(("customer", "email", "sales", "purchase")) else "pricing",
                "hash": content_hash,
            })
            
            print(f"  ✓ Extracted ({doc_type}, {len(machines)} machines)", flush=True)
            
        except Exception as e:
            print(f"  ✗ Error: {e}", flush=True)
            failed += 1
    
    print(f"\n" + "-" * 60, flush=True)
    print(f"EXTRACTION COMPLETE", flush=True)
    print(f"Extracted: {len(extracted_items)}, Skipped: {skipped}, Failed: {failed}", flush=True)
    
    if not extracted_items:
        print("No new items to ingest.", flush=True)
        return
    
    print(f"\n" + "-" * 60, flush=True)
    print(f"GENERATING EMBEDDINGS (batched)...", flush=True)
    
    BATCH_SIZE = 10
    for i in range(0, len(extracted_items), BATCH_SIZE):
        batch = extracted_items[i:i+BATCH_SIZE]
        print(f"  Embedding batch {i//BATCH_SIZE + 1}/{(len(extracted_items)+BATCH_SIZE-1)//BATCH_SIZE}...", flush=True)
        
        texts = [item["text"][:3000] for item in batch]
        embeddings = get_embeddings(texts)
        
        for item, emb in zip(batch, embeddings):
            item["embedding"] = emb
    
    print(f"\n" + "-" * 60, flush=True)
    print(f"STORING TO QDRANT...", flush=True)
    
    stored = store_to_qdrant(extracted_items)
    print(f"  ✓ Stored {stored} items to {COLLECTION_NAME}", flush=True)
    
    for item in extracted_items:
        ingested_hashes.add(item["hash"])
    save_hashes(ingested_hashes)
    
    json_data = [{k: v for k, v in item.items() if k != "embedding"} for item in extracted_items]
    OUTPUT_JSON.write_text(json.dumps(json_data, indent=2))
    print(f"  ✓ Saved JSON backup: {OUTPUT_JSON.name}", flush=True)
    
    all_machines = set()
    for item in extracted_items:
        all_machines.update(item.get("machines", []))
    
    print(f"\n" + "=" * 60, flush=True)
    print(f"INGESTION COMPLETE", flush=True)
    print(f"=" * 60, flush=True)
    print(f"Items stored: {stored}", flush=True)
    print(f"Machine models found: {len(all_machines)}", flush=True)
    for m in sorted(all_machines)[:10]:
        print(f"  - {m}", flush=True)
    if len(all_machines) > 10:
        print(f"  ... and {len(all_machines) - 10} more", flush=True)


if __name__ == "__main__":
    main()
