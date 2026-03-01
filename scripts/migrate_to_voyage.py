#!/usr/bin/env python3
"""
MIGRATE QDRANT COLLECTIONS TO VOYAGE EMBEDDINGS
================================================

Migrates existing OpenAI-embedded data to Voyage embeddings.
Runs in batches to avoid memory issues and allow resumption.

Usage:
    python scripts/migrate_to_voyage.py --collection emails --batch-size 100
    python scripts/migrate_to_voyage.py --collection emails --resume
    python scripts/migrate_to_voyage.py --status
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
import time

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "openclaw" / "agents" / "ira"))

try:
    from config import VOYAGE_API_KEY, QDRANT_URL
except ImportError:
    try:
        from openclaw.agents.ira.config import VOYAGE_API_KEY, QDRANT_URL
    except ImportError:
        VOYAGE_API_KEY = os.environ.get("VOYAGE_API_KEY")
        QDRANT_URL = os.environ.get("QDRANT_URL", "http://localhost:6333")

# Collections mapping
MIGRATIONS = {
    "emails": {
        "source": "ira_emails_openai_large_v3",
        "target": "ira_emails_voyage_v2",
        "dimension": 1024,
    },
    "chunks": {
        "source": "ira_chunks_v4_openai_large",
        "target": "ira_chunks_v4_voyage",
        "dimension": 1024,
    },
    "emails_v4": {
        "source": "ira_emails_v4_openai_large",
        "target": "ira_emails_voyage_v2",
        "dimension": 1024,
    },
}

PROGRESS_FILE = PROJECT_ROOT / "data" / "migration_progress.json"
VOYAGE_MODEL = "voyage-3"
VOYAGE_BATCH_SIZE = 128  # Voyage API limit


def load_progress() -> Dict:
    """Load migration progress from file."""
    if PROGRESS_FILE.exists():
        return json.loads(PROGRESS_FILE.read_text())
    return {}


def save_progress(progress: Dict):
    """Save migration progress to file."""
    PROGRESS_FILE.parent.mkdir(parents=True, exist_ok=True)
    PROGRESS_FILE.write_text(json.dumps(progress, indent=2))


def get_collection_stats(qdrant, collection_name: str) -> Dict:
    """Get collection statistics."""
    try:
        info = qdrant.get_collection(collection_name)
        return {
            "name": collection_name,
            "points": info.points_count,
            "status": info.status.name,
        }
    except Exception as e:
        return {"name": collection_name, "points": 0, "status": "NOT_FOUND", "error": str(e)}


def show_status():
    """Show current migration status."""
    from qdrant_client import QdrantClient
    
    qdrant = QdrantClient(url=QDRANT_URL)
    progress = load_progress()
    
    print("=" * 70)
    print("QDRANT COLLECTIONS - MIGRATION STATUS")
    print("=" * 70)
    
    print("\n📦 Current Collections:\n")
    
    # OpenAI collections (source)
    print("OpenAI Embeddings (SOURCE - to migrate):")
    for name, config in MIGRATIONS.items():
        stats = get_collection_stats(qdrant, config["source"])
        migrated = progress.get(name, {}).get("migrated", 0)
        print(f"  • {config['source']}: {stats['points']:,} points")
        if migrated > 0:
            print(f"    └─ Migrated: {migrated:,} / {stats['points']:,}")
    
    print("\nVoyage Embeddings (TARGET):")
    voyage_collections = [
        "ira_emails_voyage_v2",
        "ira_chunks_v4_voyage", 
        "ira_discovered_knowledge",
        "ira_dream_knowledge_v1",
        "ira_market_research_voyage",
    ]
    for col in voyage_collections:
        stats = get_collection_stats(qdrant, col)
        print(f"  • {col}: {stats['points']:,} points")
    
    print("\n" + "=" * 70)


def ensure_collection_exists(qdrant, collection_name: str, dimension: int):
    """Ensure target collection exists with correct config."""
    from qdrant_client.models import VectorParams, Distance
    
    try:
        qdrant.get_collection(collection_name)
        print(f"  ✓ Collection {collection_name} exists")
    except Exception:
        print(f"  Creating collection {collection_name}...")
        qdrant.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=dimension, distance=Distance.COSINE),
        )
        print(f"  ✓ Created {collection_name}")


def migrate_collection(
    collection_key: str,
    batch_size: int = 100,
    resume: bool = True,
    max_batches: Optional[int] = None,
):
    """Migrate a collection from OpenAI to Voyage embeddings."""
    import voyageai
    from qdrant_client import QdrantClient
    from qdrant_client.models import PointStruct
    
    if collection_key not in MIGRATIONS:
        print(f"Unknown collection: {collection_key}")
        print(f"Available: {list(MIGRATIONS.keys())}")
        return
    
    config = MIGRATIONS[collection_key]
    source_col = config["source"]
    target_col = config["target"]
    dimension = config["dimension"]
    
    print(f"\n{'=' * 70}")
    print(f"MIGRATING: {source_col} → {target_col}")
    print(f"{'=' * 70}")
    
    # Initialize clients
    qdrant = QdrantClient(url=QDRANT_URL)
    voyage = voyageai.Client(api_key=VOYAGE_API_KEY)
    
    # Check source collection
    source_stats = get_collection_stats(qdrant, source_col)
    if source_stats["points"] == 0:
        print(f"Source collection {source_col} is empty or doesn't exist")
        return
    
    total_points = source_stats["points"]
    print(f"Source: {total_points:,} points to migrate")
    
    # Ensure target collection exists
    ensure_collection_exists(qdrant, target_col, dimension)
    
    # Load progress
    progress = load_progress()
    col_progress = progress.get(collection_key, {"migrated": 0, "offset": None, "started": None})
    
    if resume and col_progress["migrated"] > 0:
        print(f"Resuming from {col_progress['migrated']:,} migrated points")
        offset = col_progress.get("offset")
    else:
        col_progress = {"migrated": 0, "offset": None, "started": datetime.now().isoformat()}
        offset = None
    
    migrated = col_progress["migrated"]
    batch_num = 0
    
    print(f"\nMigrating in batches of {batch_size}...")
    print("-" * 50)
    
    while True:
        # Check batch limit
        if max_batches and batch_num >= max_batches:
            print(f"\nReached max batches ({max_batches}). Run again to continue.")
            break
        
        # Scroll source collection
        results, next_offset = qdrant.scroll(
            collection_name=source_col,
            limit=batch_size,
            offset=offset,
            with_payload=True,
            with_vectors=False,  # Don't need old vectors
        )
        
        if not results:
            print("\n✅ Migration complete!")
            break
        
        # Extract texts for embedding
        texts = []
        payloads = []
        point_ids = []
        
        for point in results:
            # Get text from payload
            text = (
                point.payload.get("text") or 
                point.payload.get("content") or 
                point.payload.get("body") or
                point.payload.get("chunk_text") or
                ""
            )
            
            if not text:
                # Try to construct from email fields
                subject = point.payload.get("subject", "")
                body = point.payload.get("body", point.payload.get("snippet", ""))
                text = f"{subject}\n\n{body}".strip()
            
            if text:
                texts.append(text[:8000])  # Voyage limit
                payloads.append(point.payload)
                point_ids.append(point.id)
        
        if not texts:
            offset = next_offset
            continue
        
        # Generate Voyage embeddings in sub-batches
        all_embeddings = []
        for i in range(0, len(texts), VOYAGE_BATCH_SIZE):
            sub_batch = texts[i:i + VOYAGE_BATCH_SIZE]
            try:
                result = voyage.embed(sub_batch, model=VOYAGE_MODEL, input_type="document")
                all_embeddings.extend(result.embeddings)
            except Exception as e:
                print(f"\n⚠ Voyage API error: {e}")
                print("Saving progress and exiting...")
                col_progress["offset"] = offset
                progress[collection_key] = col_progress
                save_progress(progress)
                return
            
            # Rate limiting
            time.sleep(0.1)
        
        # Create points for target collection
        points = []
        for i, (payload, embedding) in enumerate(zip(payloads, all_embeddings)):
            # Generate new point ID (hash-based to avoid collisions)
            import hashlib
            text_hash = hashlib.md5(texts[i][:200].encode()).hexdigest()
            new_id = int(text_hash[:15], 16) % (2**63)
            
            points.append(PointStruct(
                id=new_id,
                vector=embedding,
                payload={
                    **payload,
                    "migrated_from": source_col,
                    "migrated_at": datetime.now().isoformat(),
                }
            ))
        
        # Upsert to target
        qdrant.upsert(collection_name=target_col, points=points)
        
        migrated += len(points)
        batch_num += 1
        
        # Update progress
        col_progress["migrated"] = migrated
        col_progress["offset"] = next_offset
        col_progress["last_batch"] = datetime.now().isoformat()
        progress[collection_key] = col_progress
        save_progress(progress)
        
        # Progress output
        pct = (migrated / total_points) * 100
        print(f"  Batch {batch_num}: {migrated:,} / {total_points:,} ({pct:.1f}%)")
        
        offset = next_offset
        
        if next_offset is None:
            print("\n✅ Migration complete!")
            break
    
    # Final summary
    print(f"\n{'=' * 70}")
    print(f"MIGRATION SUMMARY")
    print(f"{'=' * 70}")
    print(f"  Source: {source_col}")
    print(f"  Target: {target_col}")
    print(f"  Migrated: {migrated:,} points")
    
    target_stats = get_collection_stats(qdrant, target_col)
    print(f"  Target now has: {target_stats['points']:,} points")


def main():
    parser = argparse.ArgumentParser(description="Migrate Qdrant collections to Voyage embeddings")
    parser.add_argument("--collection", "-c", choices=list(MIGRATIONS.keys()), help="Collection to migrate")
    parser.add_argument("--batch-size", "-b", type=int, default=100, help="Batch size (default: 100)")
    parser.add_argument("--resume", "-r", action="store_true", default=True, help="Resume from last position")
    parser.add_argument("--fresh", "-f", action="store_true", help="Start fresh (ignore progress)")
    parser.add_argument("--max-batches", "-m", type=int, help="Max batches to process (for testing)")
    parser.add_argument("--status", "-s", action="store_true", help="Show migration status")
    parser.add_argument("--all", "-a", action="store_true", help="Migrate all collections")
    
    args = parser.parse_args()
    
    if not VOYAGE_API_KEY:
        print("❌ VOYAGE_API_KEY not set")
        sys.exit(1)
    
    if args.status:
        show_status()
        return
    
    if args.all:
        for col_key in MIGRATIONS.keys():
            migrate_collection(
                col_key,
                batch_size=args.batch_size,
                resume=not args.fresh,
                max_batches=args.max_batches,
            )
        return
    
    if not args.collection:
        print("Please specify --collection or --status or --all")
        parser.print_help()
        return
    
    migrate_collection(
        args.collection,
        batch_size=args.batch_size,
        resume=not args.fresh,
        max_batches=args.max_batches,
    )


if __name__ == "__main__":
    main()
