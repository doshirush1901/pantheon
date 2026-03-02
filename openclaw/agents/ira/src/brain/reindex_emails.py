#!/usr/bin/env python3
"""
Email Re-Indexer - Voyage AI
=============================

Re-indexes email chunks with Voyage AI embeddings.

Usage:
    python reindex_emails.py
    python reindex_emails.py --dry-run
"""

import logging
import os
import sys
import time
import uuid
from pathlib import Path
from typing import Dict, List

import warnings
warnings.filterwarnings("ignore")

# Import from centralized config
BRAIN_DIR = Path(__file__).parent
SKILLS_DIR = BRAIN_DIR.parent
AGENT_DIR = SKILLS_DIR.parent
sys.path.insert(0, str(AGENT_DIR))

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

try:
    from config import (
        QDRANT_URL, DATABASE_URL, VOYAGE_API_KEY,
        COLLECTIONS, EMBEDDING_MODEL_VOYAGE,
    )
except ImportError:
    PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent.parent
    env_file = PROJECT_ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if line.strip() and not line.startswith('#') and '=' in line:
                key, _, value = line.partition('=')
                os.environ.setdefault(key.strip(), value.strip().strip('"'))
    QDRANT_URL = os.environ.get("QDRANT_URL", "http://localhost:6333")
    DATABASE_URL = os.environ.get("DATABASE_URL")
    VOYAGE_API_KEY = os.environ.get("VOYAGE_API_KEY")
    COLLECTIONS = {"emails_voyage": "ira_emails_voyage_v2"}
    EMBEDDING_MODEL_VOYAGE = "voyage-3"

COLLECTION_NAME = COLLECTIONS.get("emails_voyage", "ira_emails_voyage_v2")
EMBEDDING_DIM = 1024
VOYAGE_MODEL = EMBEDDING_MODEL_VOYAGE


class EmailReindexer:
    def __init__(self, batch_size: int = 128):
        self.batch_size = batch_size
        self._qdrant = None
        self._voyage = None
    
    def _get_qdrant(self):
        """Get Qdrant client using centralized config."""
        if self._qdrant is None:
            try:
                from config import get_qdrant_client
                self._qdrant = get_qdrant_client()
            except ImportError:
                from qdrant_client import QdrantClient
                self._qdrant = QdrantClient(url=QDRANT_URL)
        return self._qdrant
    
    def _get_voyage(self):
        """Get Voyage client using centralized config."""
        if self._voyage is None:
            try:
                from config import get_voyage_client
                self._voyage = get_voyage_client()
            except ImportError:
                import voyageai
                self._voyage = voyageai.Client(api_key=VOYAGE_API_KEY)
        return self._voyage
    
    def _get_db_connection(self):
        """Get database connection context manager."""
        try:
            from config import get_db_connection
            return get_db_connection()
        except ImportError:
            import psycopg2
            from contextlib import contextmanager
            
            @contextmanager
            def _fallback():
                conn = psycopg2.connect(DATABASE_URL)
                try:
                    yield conn
                    conn.commit()
                except Exception:
                    conn.rollback()
                    raise
                finally:
                    conn.close()
            
            return _fallback()
    
    def ensure_collection(self):
        """Create Qdrant collection if needed."""
        from qdrant_client.models import Distance, VectorParams
        
        qdrant = self._get_qdrant()
        
        try:
            qdrant.get_collection(COLLECTION_NAME)
            count = qdrant.count(COLLECTION_NAME).count
            logger.info(f"Collection {COLLECTION_NAME} exists with {count} vectors")
            return count
        except Exception:
            logger.info(f"Creating collection {COLLECTION_NAME}")
            qdrant.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(size=EMBEDDING_DIM, distance=Distance.COSINE)
            )
            return 0
    
    def get_email_chunks(self, offset: int = 0, limit: int = 1000) -> List[Dict]:
        """Fetch email chunks from PostgreSQL."""
        with self._get_db_connection() as conn:
            cur = conn.cursor()
            
            cur.execute("""
                SELECT chunk_id, email_id, raw_text, contextualized_text,
                       subject, from_email, to_email, date, direction,
                       thread_key, company_domain, machines, has_quote, has_price
                FROM ira_emails.email_chunks_v2
                ORDER BY email_id
                OFFSET %s LIMIT %s
            """, (offset, limit))
            
            chunks = []
            for row in cur.fetchall():
                chunks.append({
                    "chunk_id": row[0],
                    "email_id": row[1],
                    "raw_text": row[2] or "",
                    "contextualized_text": row[3] or "",
                    "subject": row[4] or "",
                    "from_email": row[5] or "",
                    "to_email": row[6] or "",
                    "date": row[7].isoformat() if row[7] else None,
                    "direction": row[8] or "",
                    "thread_key": row[9] or "",
                    "company_domain": row[10] or "",
                    "machines": row[11] or [],
                    "has_quote": row[12] or False,
                    "has_price": row[13] or False,
                })
            
            return chunks
    
    def get_total_chunks(self) -> int:
        """Get total email chunks count."""
        with self._get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM ira_emails.email_chunks_v2")
            return cur.fetchone()[0]
    
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generate Voyage AI embeddings."""
        voyage = self._get_voyage()
        
        clean_texts = []
        for t in texts:
            t = t.replace('\x00', '').strip()
            if not t:
                t = "empty"
            clean_texts.append(t[:16000])
        
        result = voyage.embed(clean_texts, model=VOYAGE_MODEL, input_type="document")
        return result.embeddings
    
    def store_vectors(self, chunks: List[Dict], embeddings: List[List[float]]):
        """Store vectors in Qdrant."""
        from qdrant_client.models import PointStruct
        
        qdrant = self._get_qdrant()
        
        def make_uuid(chunk_id: str) -> str:
            return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"email_{chunk_id}"))
        
        points = [
            PointStruct(
                id=make_uuid(c["chunk_id"]),
                vector=emb,
                payload={
                    "chunk_id": c["chunk_id"],
                    "email_id": c["email_id"],
                    "raw_text": c["raw_text"][:1000],
                    "subject": c["subject"],
                    "from_email": c["from_email"],
                    "to_email": c["to_email"],
                    "date": c["date"],
                    "direction": c["direction"],
                    "thread_key": c["thread_key"],
                    "company_domain": c["company_domain"],
                    "machines": c["machines"],
                    "has_quote": c["has_quote"],
                    "has_price": c["has_price"],
                    "source": "email",
                }
            )
            for c, emb in zip(chunks, embeddings)
        ]
        
        for i in range(0, len(points), 100):
            batch = points[i:i+100]
            qdrant.upsert(collection_name=COLLECTION_NAME, points=batch)
    
    def reindex_all(self, dry_run: bool = False):
        """Re-index all email chunks."""
        total = self.get_total_chunks()
        logger.info(f"Total email chunks: {total}")
        
        if dry_run:
            logger.info("DRY RUN - no changes")
            return
        
        if total == 0:
            logger.warning("No email chunks found - run email ingestion first")
            return
        
        self.ensure_collection()
        
        processed = 0
        start_time = time.time()
        
        while processed < total:
            chunks = self.get_email_chunks(offset=processed, limit=self.batch_size)
            if not chunks:
                break
            
            texts = [c["contextualized_text"] or c["raw_text"] for c in chunks]
            embeddings = self.embed_texts(texts)
            
            self.store_vectors(chunks, embeddings)
            
            processed += len(chunks)
            elapsed = time.time() - start_time
            rate = processed / elapsed if elapsed > 0 else 0
            eta = (total - processed) / rate if rate > 0 else 0
            
            logger.info(f"Progress: {processed}/{total} ({100*processed/total:.1f}%) - ETA: {eta/60:.1f}min")
        
        elapsed = time.time() - start_time
        logger.info(f"Complete! {processed} emails in {elapsed:.1f}s")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Re-index emails with Voyage AI")
    parser.add_argument("--dry-run", action="store_true", help="Don't make changes")
    parser.add_argument("--batch-size", type=int, default=128, help="Batch size")
    args = parser.parse_args()
    
    if not VOYAGE_API_KEY:
        print("ERROR: VOYAGE_API_KEY not set")
        sys.exit(1)
    
    if not DATABASE_URL:
        print("ERROR: DATABASE_URL not set")
        sys.exit(1)
    
    print("=" * 60)
    print("  EMAIL RE-INDEXER (Voyage AI)")
    print("=" * 60)
    print(f"Collection: {COLLECTION_NAME}")
    print(f"Dimensions: {EMBEDDING_DIM}")
    print()
    
    reindexer = EmailReindexer(batch_size=args.batch_size)
    reindexer.reindex_all(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
