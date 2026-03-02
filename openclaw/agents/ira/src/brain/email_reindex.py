#!/usr/bin/env python3
"""
Email Quality Reindex - Fixes oversized email chunks (37% of all emails!)
=========================================================================

Issues being fixed:
- 9,539 oversized chunks (>3000 chars) → SPLIT into optimal size
- Creates 3 new optimized collections with full coverage

Usage:
    python email_reindex.py                    # Full reindex
    python email_reindex.py --dry-run          # Preview changes
"""

import argparse
import json
import logging
import os
import re
import sys
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Import from centralized config
BRAIN_DIR = Path(__file__).parent
SKILLS_DIR = BRAIN_DIR.parent
AGENT_DIR = SKILLS_DIR.parent
sys.path.insert(0, str(AGENT_DIR))

try:
    from config import (
        DATABASE_URL, QDRANT_URL, OPENAI_API_KEY, VOYAGE_API_KEY, COLLECTIONS,
    )
except ImportError:
    DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://ira:ira_password@localhost:5432/ira_db")
    QDRANT_URL = os.environ.get("QDRANT_URL", "http://localhost:6333")
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
    VOYAGE_API_KEY = os.environ.get("VOYAGE_API_KEY")
    COLLECTIONS = {
        "emails_voyage": "ira_emails_voyage_v2",
        "emails_openai_large": "ira_emails_v4_openai_large",
        "emails_openai_small": "ira_emails_openai_small_v3",
    }

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Chunk size targets
MIN_CHUNK_SIZE = 100
TARGET_CHUNK_SIZE = 1200
MAX_CHUNK_SIZE = 2000
OVERLAP_SIZE = 100

# Collections (from config)
VOYAGE_COLLECTION = COLLECTIONS.get("emails_voyage", "ira_emails_voyage_v2")
OPENAI_LARGE_COLLECTION = COLLECTIONS.get("emails_openai_large", "ira_emails_openai_large_v3")
OPENAI_SMALL_COLLECTION = COLLECTIONS.get("emails_openai_small", "ira_emails_openai_small_v3")

# Machinecraft patterns
MACHINE_PATTERNS = [
    r'\bPF[-\s]?[12][-\s]?[XCSPRA]?[-\s]?\d*',
    r'\bAM[-\s]?[MVP][-\s]?\d*',
    r'\bFCS[-\s]?\d+',
    r'\bATF[-\s]?\d+',
    r'\bIMG[-\s]?\d+',
]

PRICE_PATTERN = r'[\$€₹]\s*[\d,]+(?:\.\d{2})?|USD\s*[\d,]+|EUR\s*[\d,]+|\d{1,3}(?:,\d{3})+\s*(?:USD|EUR|INR)'


@dataclass
class ProcessedEmailChunk:
    chunk_id: str
    email_id: int
    text: str
    char_count: int
    subject: str
    from_email: str
    to_email: str
    date: Optional[datetime]
    direction: str
    thread_key: str
    company_domain: str
    machines: List[str] = field(default_factory=list)
    has_price: bool = False
    has_quote: bool = False
    has_attachment: bool = False
    is_reply: bool = False
    
    def to_payload(self) -> Dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "email_id": self.email_id,
            "subject": self.subject,
            "from_email": self.from_email,
            "to_email": self.to_email,
            "date": self.date.isoformat() if self.date else None,
            "direction": self.direction,
            "thread_key": self.thread_key,
            "company_domain": self.company_domain,
            "machines": self.machines,
            "has_price": self.has_price,
            "has_quote": self.has_quote,
            "has_attachment": self.has_attachment,
            "is_reply": self.is_reply,
            "char_count": self.char_count,
        }


def get_db_connection():
    """Get database connection using centralized config."""
    try:
        from config import get_db_connection as _get_db_connection
        return _get_db_connection()
    except ImportError:
        import psycopg2
        from contextlib import contextmanager
        
        @contextmanager
        def _fallback_conn():
            conn = psycopg2.connect(DATABASE_URL)
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()
        
        return _fallback_conn()


def get_qdrant_client():
    """Get Qdrant client using centralized config."""
    try:
        from config import get_qdrant_client as _get_qdrant_client
        return _get_qdrant_client()
    except ImportError:
        from qdrant_client import QdrantClient
        return QdrantClient(url=QDRANT_URL)


def extract_machines(text: str) -> List[str]:
    machines = []
    for pattern in MACHINE_PATTERNS:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            machine = match.group(0).upper().replace(' ', '-')
            if machine not in machines:
                machines.append(machine)
    return machines


def has_price_info(text: str) -> bool:
    return bool(re.search(PRICE_PATTERN, text))


def smart_split_email(text: str, target_size: int = TARGET_CHUNK_SIZE, max_size: int = MAX_CHUNK_SIZE) -> List[str]:
    """Split email text at semantic boundaries."""
    if len(text) <= target_size:
        return [text]
    
    # Clean up email artifacts
    text = re.sub(r'^>+\s*', '', text, flags=re.MULTILINE)
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # Try paragraph split first
    paragraphs = re.split(r'\n\s*\n', text)
    if len(paragraphs) > 1:
        chunks = []
        current = ""
        
        for para in paragraphs:
            para = para.strip()
            if not para or len(para) < 20:
                continue
            
            if len(current) + len(para) > target_size and current:
                chunks.append(current.strip())
                overlap = current[-OVERLAP_SIZE:] if len(current) > OVERLAP_SIZE else ""
                current = overlap + "\n\n" + para
            else:
                current = current + "\n\n" + para if current else para
        
        if current.strip() and len(current.strip()) >= MIN_CHUNK_SIZE:
            chunks.append(current.strip())
        
        if chunks and all(len(c) <= max_size for c in chunks):
            return chunks
    
    # Try sentence split
    sentences = re.split(r'(?<=[.!?])\s+', text)
    chunks = []
    current = ""
    
    for sentence in sentences:
        if len(current) + len(sentence) > target_size and current:
            chunks.append(current.strip())
            overlap = current[-OVERLAP_SIZE:] if len(current) > OVERLAP_SIZE else ""
            current = overlap + " " + sentence
        else:
            current = current + " " + sentence if current else sentence
    
    if current.strip() and len(current.strip()) >= MIN_CHUNK_SIZE:
        chunks.append(current.strip())
    
    if chunks and all(len(c) <= max_size for c in chunks):
        return chunks
    
    # Force split at word boundaries
    final_chunks = []
    for chunk in (chunks if chunks else [text]):
        if len(chunk) <= max_size:
            final_chunks.append(chunk)
        else:
            words = chunk.split()
            current = ""
            for word in words:
                if len(current) + len(word) + 1 > target_size and current:
                    final_chunks.append(current.strip())
                    overlap_words = current.split()[-15:]
                    current = " ".join(overlap_words) + " " + word
                else:
                    current = current + " " + word if current else word
            if current.strip():
                final_chunks.append(current.strip())
    
    return final_chunks if final_chunks else [text]


def process_email_chunks(batch_size: int = 2000) -> List[ProcessedEmailChunk]:
    """Load, clean, and process all email chunks."""
    logger.info("LOADING EMAIL CHUNKS FROM POSTGRESQL")
    logger.info("-" * 50)
    
    with get_db_connection() as conn:
        cur = conn.cursor()
        
        cur.execute("SELECT COUNT(*) FROM ira_emails.email_chunks_v2")
        total = cur.fetchone()[0]
        logger.info("  Total email chunks: %s", f"{total:,}")
        
        cur.execute("SELECT COUNT(*) FROM ira_emails.email_chunks_v2 WHERE char_count < 50")
        noise = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM ira_emails.email_chunks_v2 WHERE char_count > 3000")
        oversized = cur.fetchone()[0]
        
        logger.info("  Noise (<50 chars): %s → REMOVE", f"{noise:,}")
        logger.info("  Oversized (>3000 chars): %s → SPLIT", f"{oversized:,}")
    
    processed = []
    offset = 0
    
    logger.info("PROCESSING EMAIL CHUNKS")
    logger.info("-" * 50)
    
    while offset < total:
        with get_db_connection() as conn:
            cur = conn.cursor()
            
            cur.execute("""
                SELECT chunk_id, email_id, raw_text, char_count, subject, from_email, 
                       to_email, date, direction, thread_key, company_domain,
                       machines, has_quote, has_attachment, is_reply
                FROM ira_emails.email_chunks_v2
                ORDER BY email_id, chunk_id
                LIMIT %s OFFSET %s
            """, (batch_size, offset))
            
            rows = cur.fetchall()
        
        if not rows:
            break
        
        for row in rows:
            (chunk_id, email_id, text, char_count, subject, from_email, 
             to_email, date, direction, thread_key, company_domain,
             machines_arr, has_quote, has_attachment, is_reply) = row
            
            if not text or char_count < 50:
                continue
            
            # Handle oversized chunks - SPLIT
            if char_count > MAX_CHUNK_SIZE * 1.5:
                sub_texts = smart_split_email(text, TARGET_CHUNK_SIZE, MAX_CHUNK_SIZE)
                for sub_text in sub_texts:
                    machines = extract_machines(sub_text)
                    processed.append(ProcessedEmailChunk(
                        chunk_id=str(uuid.uuid4()),
                        email_id=email_id,
                        text=sub_text,
                        char_count=len(sub_text),
                        subject=subject or "",
                        from_email=from_email or "",
                        to_email=to_email or "",
                        date=date,
                        direction=direction or "",
                        thread_key=thread_key or "",
                        company_domain=company_domain or "",
                        machines=machines,
                        has_price=has_price_info(sub_text),
                        has_quote=has_quote or False,
                        has_attachment=has_attachment or False,
                        is_reply=is_reply or False,
                    ))
            else:
                machines = machines_arr if machines_arr else extract_machines(text)
                processed.append(ProcessedEmailChunk(
                    chunk_id=str(uuid.uuid4()),
                    email_id=email_id,
                    text=text,
                    char_count=len(text),
                    subject=subject or "",
                    from_email=from_email or "",
                    to_email=to_email or "",
                    date=date,
                    direction=direction or "",
                    thread_key=thread_key or "",
                    company_domain=company_domain or "",
                    machines=machines if isinstance(machines, list) else [],
                    has_price=has_price_info(text),
                    has_quote=has_quote or False,
                    has_attachment=has_attachment or False,
                    is_reply=is_reply or False,
                ))
        
        offset += batch_size
        logger.info("  Processed %s/%s (%s%%)", f"{min(offset, total):,}", f"{total:,}", f"{min(offset, total)*100/total:.0f}")
    
    logger.info("Total processed: %s", f"{len(processed):,}")
    optimal = sum(1 for c in processed if 800 <= c.char_count <= 1500)
    logger.info("  Optimal size (800-1500): %s (%s%%)", f"{optimal:,}", f"{optimal*100/len(processed):.0f}")
    
    return processed


def save_to_postgres(chunks: List[ProcessedEmailChunk]):
    """Save processed chunks to PostgreSQL."""
    logger.info("SAVING TO POSTGRESQL")
    logger.info("-" * 50)
    
    with get_db_connection() as conn:
        cur = conn.cursor()
        
        cur.execute("""
            DROP TABLE IF EXISTS ira_emails.email_chunks_clean CASCADE;
            CREATE TABLE ira_emails.email_chunks_clean (
                chunk_id TEXT PRIMARY KEY,
                email_id INT NOT NULL,
                raw_text TEXT NOT NULL,
                char_count INT,
                subject TEXT,
                from_email TEXT,
                to_email TEXT,
                date TIMESTAMPTZ,
                direction TEXT,
                thread_key TEXT,
                company_domain TEXT,
                machines TEXT[],
                has_price BOOLEAN DEFAULT FALSE,
                has_quote BOOLEAN DEFAULT FALSE,
                has_attachment BOOLEAN DEFAULT FALSE,
                is_reply BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMPTZ DEFAULT NOW()
            );
        """)
        
        batch_size = 1000
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            for chunk in batch:
                cur.execute("""
                    INSERT INTO ira_emails.email_chunks_clean 
                    (chunk_id, email_id, raw_text, char_count, subject, from_email,
                     to_email, date, direction, thread_key, company_domain,
                     machines, has_price, has_quote, has_attachment, is_reply)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    chunk.chunk_id, chunk.email_id, chunk.text, chunk.char_count,
                    chunk.subject, chunk.from_email, chunk.to_email, chunk.date,
                    chunk.direction, chunk.thread_key, chunk.company_domain,
                    chunk.machines, chunk.has_price, chunk.has_quote,
                    chunk.has_attachment, chunk.is_reply,
                ))
            
            if (i // batch_size) % 10 == 0:
                logger.info("  Inserted %s/%s", f"{min(i + batch_size, len(chunks)):,}", f"{len(chunks):,}")
        
        cur.execute("""
            CREATE INDEX idx_email_clean_email ON ira_emails.email_chunks_clean(email_id);
            CREATE INDEX idx_email_clean_thread ON ira_emails.email_chunks_clean(thread_key);
            CREATE INDEX idx_email_clean_domain ON ira_emails.email_chunks_clean(company_domain);
            CREATE INDEX idx_email_clean_machines ON ira_emails.email_chunks_clean USING GIN(machines);
        """)
    
    logger.info("  Saved %s chunks to ira_emails.email_chunks_clean", f"{len(chunks):,}")


def embed_with_openai_small(chunks: List[ProcessedEmailChunk], batch_size: int = 100):
    """Embed with OpenAI text-embedding-3-small (1536d)."""
    logger.info("EMBEDDING WITH OPENAI SMALL (1536d)")
    logger.info("-" * 50)
    
    import openai
    from qdrant_client.models import Distance, VectorParams, PointStruct
    
    client = get_qdrant_client()
    openai_client = openai.OpenAI(api_key=OPENAI_API_KEY)
    
    try:
        client.delete_collection(OPENAI_SMALL_COLLECTION)
    except Exception:
        pass
    
    client.create_collection(
        collection_name=OPENAI_SMALL_COLLECTION,
        vectors_config=VectorParams(size=1536, distance=Distance.COSINE)
    )
    
    logger.info("  Created collection: %s", OPENAI_SMALL_COLLECTION)
    
    embedded = 0
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        texts = [f"Subject: {c.subject}\n\n{c.text}"[:8000] if c.subject else c.text[:8000] for c in batch]
        
        try:
            response = openai_client.embeddings.create(model="text-embedding-3-small", input=texts)
            embeddings = [item.embedding for item in response.data]
            
            points = [PointStruct(id=c.chunk_id, vector=emb, payload=c.to_payload()) for c, emb in zip(batch, embeddings)]
            client.upsert(collection_name=OPENAI_SMALL_COLLECTION, points=points)
            embedded += len(points)
            
            if (i // batch_size) % 50 == 0:
                logger.info("  Progress: %s/%s (%s%%)", f"{embedded:,}", f"{len(chunks):,}", f"{embedded*100/len(chunks):.0f}")
        except Exception as e:
            logger.warning("  Batch %s error: %s", i, e)
            time.sleep(2)
    
    logger.info("  Embedded %s chunks", f"{embedded:,}")


def embed_with_openai_large(chunks: List[ProcessedEmailChunk], batch_size: int = 50):
    """Embed with OpenAI text-embedding-3-large (3072d)."""
    logger.info("EMBEDDING WITH OPENAI LARGE (3072d)")
    logger.info("-" * 50)
    
    import openai
    from qdrant_client.models import Distance, VectorParams, PointStruct
    
    client = get_qdrant_client()
    openai_client = openai.OpenAI(api_key=OPENAI_API_KEY)
    
    try:
        client.delete_collection(OPENAI_LARGE_COLLECTION)
    except Exception:
        pass
    
    client.create_collection(
        collection_name=OPENAI_LARGE_COLLECTION,
        vectors_config=VectorParams(size=3072, distance=Distance.COSINE)
    )
    
    logger.info("  Created collection: %s", OPENAI_LARGE_COLLECTION)
    
    embedded = 0
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        texts = [f"Subject: {c.subject}\n\n{c.text}"[:8000] if c.subject else c.text[:8000] for c in batch]
        
        try:
            response = openai_client.embeddings.create(model="text-embedding-3-large", input=texts)
            embeddings = [item.embedding for item in response.data]
            
            points = [PointStruct(id=c.chunk_id, vector=emb, payload=c.to_payload()) for c, emb in zip(batch, embeddings)]
            client.upsert(collection_name=OPENAI_LARGE_COLLECTION, points=points)
            embedded += len(points)
            
            if (i // batch_size) % 20 == 0:
                logger.info("  Progress: %s/%s (%s%%)", f"{embedded:,}", f"{len(chunks):,}", f"{embedded*100/len(chunks):.0f}")
        except Exception as e:
            logger.warning("  Batch %s error: %s", i, e)
            time.sleep(2)
    
    logger.info("  Embedded %s chunks", f"{embedded:,}")


def embed_with_voyage(chunks: List[ProcessedEmailChunk], batch_size: int = 100):
    """Embed with Voyage AI voyage-3 (1024d)."""
    logger.info("EMBEDDING WITH VOYAGE AI (1024d)")
    logger.info("-" * 50)
    
    if not VOYAGE_API_KEY:
        logger.warning("  VOYAGE_API_KEY not set, skipping")
        return
    
    import voyageai
    from qdrant_client.models import Distance, VectorParams, PointStruct
    
    client = get_qdrant_client()
    voyage_client = voyageai.Client(api_key=VOYAGE_API_KEY)
    
    try:
        client.delete_collection(VOYAGE_COLLECTION)
    except Exception:
        pass
    
    client.create_collection(
        collection_name=VOYAGE_COLLECTION,
        vectors_config=VectorParams(size=1024, distance=Distance.COSINE)
    )
    
    logger.info("  Created collection: %s", VOYAGE_COLLECTION)
    
    embedded = 0
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        texts = [f"Subject: {c.subject}\n\n{c.text}"[:16000] if c.subject else c.text[:16000] for c in batch]
        
        try:
            result = voyage_client.embed(texts, model="voyage-3", input_type="document")
            embeddings = result.embeddings
            
            points = [PointStruct(id=c.chunk_id, vector=emb, payload=c.to_payload()) for c, emb in zip(batch, embeddings)]
            client.upsert(collection_name=VOYAGE_COLLECTION, points=points)
            embedded += len(points)
            
            if (i // batch_size) % 50 == 0:
                logger.info("  Progress: %s/%s (%s%%)", f"{embedded:,}", f"{len(chunks):,}", f"{embedded*100/len(chunks):.0f}")
        except Exception as e:
            logger.warning("  Batch %s error: %s", i, e)
            time.sleep(2)
    
    logger.info("  Embedded %s chunks", f"{embedded:,}")


def print_final_report(chunks: List[ProcessedEmailChunk]):
    """Print final quality report."""
    logger.info("=" * 70)
    logger.info("  EMAIL REINDEX - FINAL REPORT")
    logger.info("=" * 70)
    
    optimal = sum(1 for c in chunks if 800 <= c.char_count <= 1500)
    oversized = sum(1 for c in chunks if c.char_count > 3000)
    with_machines = sum(1 for c in chunks if c.machines)
    with_price = sum(1 for c in chunks if c.has_price)
    
    logger.info("SIZE DISTRIBUTION")
    logger.info("   Optimal (800-1500): %s (%s%%)", f"{optimal:,}", f"{optimal*100/len(chunks):.0f}")
    logger.info("   Oversized (>3000): %s", f"{oversized:,}")
    
    logger.info("ENTITY COVERAGE")
    logger.info("   With machine refs: %s (%s%%)", f"{with_machines:,}", f"{with_machines*100/len(chunks):.1f}")
    logger.info("   With price info: %s (%s%%)", f"{with_price:,}", f"{with_price*100/len(chunks):.1f}")
    
    logger.info("QDRANT COLLECTIONS")
    client = get_qdrant_client()
    for coll in [OPENAI_SMALL_COLLECTION, OPENAI_LARGE_COLLECTION, VOYAGE_COLLECTION]:
        try:
            info = client.get_collection(coll)
            logger.info("   %s: %s pts (%sd)", coll, f"{info.points_count:,}", info.config.params.vectors.size)
        except Exception:
            logger.info("   %s: not created", coll)
    
    logger.info("=" * 70)


def main():
    parser = argparse.ArgumentParser(description="Email Quality Reindex")
    parser.add_argument('--dry-run', action='store_true', help='Preview changes')
    parser.add_argument('--skip-voyage', action='store_true', help='Skip Voyage embeddings')
    parser.add_argument('--skip-openai-large', action='store_true', help='Skip OpenAI large')
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("  EMAIL QUALITY REINDEX")
    print("  Fixing 9,539 oversized chunks (37% of emails)")
    print("=" * 70)
    
    start_time = time.time()
    
    chunks = process_email_chunks()
    
    if args.dry_run:
        print("\n[DRY RUN] Would process and embed these chunks")
        print_final_report(chunks)
        return
    
    save_to_postgres(chunks)
    embed_with_openai_small(chunks)
    
    if not args.skip_openai_large:
        embed_with_openai_large(chunks)
    
    if not args.skip_voyage:
        embed_with_voyage(chunks)
    
    elapsed = time.time() - start_time
    print_final_report(chunks)
    print(f"\n⏱️ Total time: {elapsed:.1f} seconds")
    print("\n✅ EMAIL REINDEX FINISHED")


if __name__ == "__main__":
    main()
