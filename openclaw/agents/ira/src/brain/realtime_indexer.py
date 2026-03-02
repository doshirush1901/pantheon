#!/usr/bin/env python3
"""
Real-time Email/Document Indexer
================================

Indexes new emails and documents into optimized Qdrant collections
as they arrive. Called from email_handler.py and document ingestion.

Usage:
    from realtime_indexer import index_new_email, index_new_document
    
    # Index a new email
    index_new_email(email_id, subject, body, from_email, date, thread_key, ...)
    
    # Index a new document
    index_new_document(doc_id, filename, text, doc_type, ...)
"""

import logging
import os
import re
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

# Import from centralized config
BRAIN_DIR = Path(__file__).parent
SKILLS_DIR = BRAIN_DIR.parent
AGENT_DIR = SKILLS_DIR.parent
sys.path.insert(0, str(AGENT_DIR))

try:
    from config import (
        DATABASE_URL, QDRANT_URL, VOYAGE_API_KEY, COLLECTIONS,
    )
except ImportError:
    PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent.parent
    env_file = PROJECT_ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if line.strip() and not line.startswith('#') and '=' in line:
                key, _, value = line.partition('=')
                os.environ.setdefault(key.strip(), value.strip().strip('"'))
    DATABASE_URL = os.environ.get("DATABASE_URL", "")
    QDRANT_URL = os.environ.get("QDRANT_URL", "http://localhost:6333")
    VOYAGE_API_KEY = os.environ.get("VOYAGE_API_KEY")
    COLLECTIONS = {
        "emails_voyage": "ira_emails_voyage_v2",
        "chunks_voyage": "ira_chunks_v4_voyage",
    }

# Voyage-3 embedding configuration (consistent with all Ira components)
EMBEDDING_MODEL = "voyage-3"
EMBEDDING_DIMENSION = 1024

# Collections - Use Voyage for consistency
EMAIL_COLLECTION = COLLECTIONS.get("emails_voyage", "ira_emails_voyage_v2")
DOC_COLLECTION = COLLECTIONS.get("chunks_voyage", "ira_chunks_v4_voyage")

# Entity patterns
MACHINE_PATTERNS = [
    r'\bPF[-\s]?[12][-\s]?[XCSPRA]?[-\s]?\d*',
    r'\bAM[-\s]?[MVP][-\s]?\d*',
    r'\bFCS[-\s]?\d+',
    r'\bATF[-\s]?\d+',
    r'\bIMG[-\s]?\d+',
]

PRICE_PATTERN = r'[\$€₹]\s*[\d,]+(?:\.\d{2})?|USD\s*[\d,]+|EUR\s*[\d,]+|\d{1,3}(?:,\d{3})+\s*(?:USD|EUR|INR)'


def _get_voyage():
    """Get Voyage client for embeddings using centralized config."""
    try:
        from config import get_voyage_client
        return get_voyage_client()
    except ImportError:
        import voyageai
        return voyageai.Client(api_key=VOYAGE_API_KEY)


def _get_qdrant():
    """Get Qdrant client using centralized config."""
    try:
        from config import get_qdrant_client
        return get_qdrant_client()
    except ImportError:
        from qdrant_client import QdrantClient
        return QdrantClient(url=QDRANT_URL)


def _extract_machines(text: str) -> List[str]:
    """Extract machine model references."""
    machines = []
    for pattern in MACHINE_PATTERNS:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            machine = match.group(0).upper().replace(' ', '-')
            if machine not in machines:
                machines.append(machine)
    return machines


def _has_price(text: str) -> bool:
    """Check if text contains price info."""
    return bool(re.search(PRICE_PATTERN, text))


def _smart_chunk(text: str, target_size: int = 1200, max_size: int = 2000) -> List[str]:
    """Split text into optimal chunks."""
    if len(text) <= target_size:
        return [text]
    
    # Try sentence split
    sentences = re.split(r'(?<=[.!?])\s+', text)
    chunks = []
    current = ""
    
    for sentence in sentences:
        if len(current) + len(sentence) > target_size and current:
            chunks.append(current.strip())
            current = sentence
        else:
            current = current + " " + sentence if current else sentence
    
    if current.strip():
        chunks.append(current.strip())
    
    return chunks if chunks else [text]


def _embed_text(text: str) -> List[float]:
    """Get embedding for text using Voyage-3 (consistent with all Ira retrieval)."""
    voyage = _get_voyage()
    result = voyage.embed([text[:8000]], model=EMBEDDING_MODEL, input_type="document")
    return result.embeddings[0]


def _collection_exists(collection_name: str) -> bool:
    """Check if Qdrant collection exists and has data."""
    try:
        qdrant = _get_qdrant()
        info = qdrant.get_collection(collection_name)
        return info.points_count > 0
    except Exception:
        return False


def index_new_email(
    email_id: int,
    subject: str,
    body: str,
    from_email: str,
    to_email: str = "",
    date: Optional[datetime] = None,
    thread_key: str = "",
    company_domain: str = "",
    direction: str = "inbound",
    is_reply: bool = False,
    has_attachment: bool = False,
) -> Dict[str, Any]:
    """
    Index a new email into optimized Qdrant collections.
    
    Args:
        email_id: Database email ID
        subject: Email subject
        body: Email body text
        from_email: Sender email
        to_email: Recipient email
        date: Email timestamp
        thread_key: Thread identifier
        company_domain: Extracted company domain
        direction: "inbound" or "outbound"
        is_reply: Whether this is a reply
        has_attachment: Whether email has attachments
        
    Returns:
        Dict with status and chunk count
    """
    from qdrant_client.models import PointStruct
    
    if not body or len(body.strip()) < 50:
        return {"status": "skipped", "reason": "too_short", "chunks": 0}
    
    # Chunk the email if needed
    chunks = _smart_chunk(body)
    
    # Extract entities
    full_text = f"{subject}\n\n{body}"
    machines = _extract_machines(full_text)
    has_price_info = _has_price(full_text)
    
    # Prepare points for Voyage collection
    points = []
    
    for chunk_text in chunks:
        chunk_id = str(uuid.uuid4())
        
        # Build payload
        payload = {
            "chunk_id": chunk_id,
            "email_id": email_id,
            "subject": subject,
            "from_email": from_email,
            "to_email": to_email,
            "date": date.isoformat() if date else None,
            "thread_key": thread_key,
            "company_domain": company_domain,
            "direction": direction,
            "machines": machines,
            "has_price": has_price_info,
            "is_reply": is_reply,
            "has_attachment": has_attachment,
            "char_count": len(chunk_text),
            "raw_text": chunk_text,  # Store text for retrieval display
        }
        
        # Generate Voyage embedding
        combined_text = f"Subject: {subject}\n\n{chunk_text}" if subject else chunk_text
        
        try:
            embedding = _embed_text(combined_text)
            points.append(PointStruct(id=chunk_id, vector=embedding, payload=payload))
        except Exception as e:
            logger.error(f"Voyage embedding failed: {e}")
    
    # Upsert to Voyage collection
    qdrant = _get_qdrant()
    indexed = 0
    
    if points and _collection_exists(EMAIL_COLLECTION):
        try:
            qdrant.upsert(collection_name=EMAIL_COLLECTION, points=points)
            indexed = len(points)
            logger.info(f"Indexed {indexed} email chunks to {EMAIL_COLLECTION}")
        except Exception as e:
            logger.error(f"Failed to upsert to {EMAIL_COLLECTION}: {e}")
    
    return {
        "status": "indexed",
        "chunks": len(chunks),
        "points_indexed": indexed,
        "machines_found": machines,
        "has_price": has_price_info,
    }


def index_new_document(
    doc_id: str,
    filename: str,
    text: str,
    doc_type: str = "document",
    page: Optional[int] = None,
    sheet: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Index a new document into optimized Qdrant collections.
    
    Args:
        doc_id: Document identifier
        filename: Original filename
        text: Document text content
        doc_type: Type (pdf, excel, etc.)
        page: Page number if applicable
        sheet: Sheet name if Excel
        
    Returns:
        Dict with status and chunk count
    """
    from qdrant_client.models import PointStruct
    
    if not text or len(text.strip()) < 50:
        return {"status": "skipped", "reason": "too_short", "chunks": 0}
    
    # Chunk the document
    chunks = _smart_chunk(text)
    
    # Extract entities
    machines = _extract_machines(text)
    has_price_info = _has_price(text)
    
    points = []
    
    for chunk_text in chunks:
        chunk_id = str(uuid.uuid4())
        
        payload = {
            "chunk_id": chunk_id,
            "doc_id": doc_id,
            "filename": filename,
            "doc_type": doc_type,
            "page": page,
            "sheet": sheet,
            "machines": machines,
            "has_price": has_price_info,
            "char_count": len(chunk_text),
            "raw_text": chunk_text,  # Store text for retrieval display
        }
        
        try:
            embedding = _embed_text(chunk_text)
            points.append(PointStruct(id=chunk_id, vector=embedding, payload=payload))
        except Exception as e:
            logger.error(f"Voyage embedding failed: {e}")
    
    # Upsert to Voyage collection
    qdrant = _get_qdrant()
    indexed = 0
    
    if points and _collection_exists(DOC_COLLECTION):
        try:
            qdrant.upsert(collection_name=DOC_COLLECTION, points=points)
            indexed = len(points)
            print(f"[realtime_indexer] Indexed {indexed} doc chunks to {DOC_COLLECTION}")
        except Exception as e:
            print(f"[realtime_indexer] Failed to upsert to {DOC_COLLECTION}: {e}")
    
    return {
        "status": "indexed",
        "chunks": len(chunks),
        "points_indexed": indexed,
        "machines_found": machines,
        "has_price": has_price_info,
    }


if __name__ == "__main__":
    # Test
    print("Testing real-time email indexer...")
    
    result = index_new_email(
        email_id=99999,
        subject="Test: PF1 Quote Request",
        body="Hi, we are interested in PF1-C-1520 for our automotive application. What is the price? Best regards, Test Customer",
        from_email="test@example.com",
        date=datetime.now(),
        thread_key="test_thread",
        company_domain="example.com",
    )
    
    print(f"Result: {result}")
