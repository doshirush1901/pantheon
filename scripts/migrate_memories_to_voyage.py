#!/usr/bin/env python3
"""
Migrate Memory Embeddings from OpenAI to Voyage-3

This script migrates existing user and entity memories from OpenAI embeddings
(text-embedding-3-small, 1536d) to Voyage-3 embeddings (1024d) for consistency
with the rest of Ira's retrieval system.

Collections:
- OLD: ira_user_memories (1536d), ira_entity_memories (1536d)
- NEW: ira_user_memories_v2 (1024d), ira_entity_memories_v2 (1024d)

Usage:
    python scripts/migrate_memories_to_voyage.py --dry-run  # Preview changes
    python scripts/migrate_memories_to_voyage.py            # Execute migration
    python scripts/migrate_memories_to_voyage.py --verify   # Verify migration
"""

import argparse
import os
import sys
import uuid
from pathlib import Path

# Setup imports
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "openclaw" / "agents" / "ira"))

# Load environment
env_file = PROJECT_ROOT / ".env"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        if line.strip() and not line.startswith('#') and '=' in line:
            key, _, value = line.partition('=')
            os.environ.setdefault(key.strip(), value.strip().strip('"'))

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://ira:ira_password@localhost:5432/ira_db")
QDRANT_URL = os.environ.get("QDRANT_URL", "http://localhost:6333")
VOYAGE_API_KEY = os.environ.get("VOYAGE_API_KEY")

# Collection names
OLD_USER_COLLECTION = "ira_user_memories"
OLD_ENTITY_COLLECTION = "ira_entity_memories"
NEW_USER_COLLECTION = "ira_user_memories_v2"
NEW_ENTITY_COLLECTION = "ira_entity_memories_v2"

EMBEDDING_MODEL = "voyage-3"
EMBEDDING_DIMENSION = 1024


def get_voyage():
    import voyageai
    return voyageai.Client(api_key=VOYAGE_API_KEY)


def get_qdrant():
    from qdrant_client import QdrantClient
    return QdrantClient(url=QDRANT_URL)


def get_db():
    import psycopg2
    return psycopg2.connect(DATABASE_URL)


def ensure_collection(qdrant, collection_name: str):
    """Create collection if it doesn't exist."""
    from qdrant_client.models import Distance, VectorParams
    
    collections = [c.name for c in qdrant.get_collections().collections]
    if collection_name not in collections:
        qdrant.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=EMBEDDING_DIMENSION, distance=Distance.COSINE)
        )
        print(f"Created collection: {collection_name}")
        return True
    return False


def get_old_collection_count(qdrant, collection_name: str) -> int:
    """Get point count from old collection."""
    try:
        info = qdrant.get_collection(collection_name)
        return info.points_count
    except Exception:
        return 0


def migrate_user_memories(dry_run: bool = False):
    """Migrate user memories to Voyage embeddings."""
    print("\n" + "=" * 60)
    print("MIGRATING USER MEMORIES")
    print("=" * 60)
    
    conn = get_db()
    cursor = conn.cursor()
    voyage = get_voyage()
    qdrant = get_qdrant()
    
    # Get all active user memories
    cursor.execute("""
        SELECT id, identity_id, memory_text, memory_type, embedding_id
        FROM ira_memory.user_memories
        WHERE is_active = TRUE
    """)
    
    memories = cursor.fetchall()
    print(f"Found {len(memories)} active user memories to migrate")
    
    if dry_run:
        print("[DRY RUN] Would migrate these memories:")
        for m in memories[:5]:
            print(f"  - ID {m[0]}: {m[2][:50]}...")
        if len(memories) > 5:
            print(f"  ... and {len(memories) - 5} more")
        return
    
    # Ensure new collection exists
    ensure_collection(qdrant, NEW_USER_COLLECTION)
    
    # Batch embed and upsert
    from qdrant_client.models import PointStruct
    
    batch_size = 50
    migrated = 0
    
    for i in range(0, len(memories), batch_size):
        batch = memories[i:i + batch_size]
        texts = [m[2] for m in batch]
        
        # Get Voyage embeddings
        result = voyage.embed(texts, model=EMBEDDING_MODEL, input_type="document")
        embeddings = result.embeddings
        
        # Create points
        points = []
        for j, (mem_id, identity_id, memory_text, memory_type, old_emb_id) in enumerate(batch):
            point_id = str(uuid.uuid4())
            points.append(PointStruct(
                id=point_id,
                vector=embeddings[j],
                payload={
                    "memory_id": mem_id,
                    "identity_id": identity_id,
                    "memory_text": memory_text,
                    "memory_type": memory_type,
                }
            ))
            
            # Update database with new embedding ID
            cursor.execute("""
                UPDATE ira_memory.user_memories
                SET embedding_id = %s
                WHERE id = %s
            """, (point_id, mem_id))
        
        # Upsert to new collection
        qdrant.upsert(collection_name=NEW_USER_COLLECTION, points=points)
        migrated += len(points)
        print(f"  Migrated {migrated}/{len(memories)} user memories...")
    
    conn.commit()
    print(f"Successfully migrated {migrated} user memories to Voyage-3")


def migrate_entity_memories(dry_run: bool = False):
    """Migrate entity memories to Voyage embeddings."""
    print("\n" + "=" * 60)
    print("MIGRATING ENTITY MEMORIES")
    print("=" * 60)
    
    conn = get_db()
    cursor = conn.cursor()
    voyage = get_voyage()
    qdrant = get_qdrant()
    
    # Get all active entity memories
    cursor.execute("""
        SELECT id, entity_type, entity_name, normalized_name, memory_text, embedding_id
        FROM ira_memory.entity_memories
        WHERE is_active = TRUE
    """)
    
    memories = cursor.fetchall()
    print(f"Found {len(memories)} active entity memories to migrate")
    
    if dry_run:
        print("[DRY RUN] Would migrate these memories:")
        for m in memories[:5]:
            print(f"  - ID {m[0]} [{m[1]}:{m[2]}]: {m[4][:50]}...")
        if len(memories) > 5:
            print(f"  ... and {len(memories) - 5} more")
        return
    
    # Ensure new collection exists
    ensure_collection(qdrant, NEW_ENTITY_COLLECTION)
    
    from qdrant_client.models import PointStruct
    
    batch_size = 50
    migrated = 0
    
    for i in range(0, len(memories), batch_size):
        batch = memories[i:i + batch_size]
        # Format text for embedding (same as original)
        texts = [f"{m[1]}: {m[3]} - {m[4]}" for m in batch]
        
        result = voyage.embed(texts, model=EMBEDDING_MODEL, input_type="document")
        embeddings = result.embeddings
        
        points = []
        for j, (mem_id, entity_type, entity_name, normalized_name, memory_text, old_emb_id) in enumerate(batch):
            point_id = str(uuid.uuid4())
            points.append(PointStruct(
                id=point_id,
                vector=embeddings[j],
                payload={
                    "memory_id": mem_id,
                    "entity_type": entity_type,
                    "entity_name": entity_name,
                    "normalized_name": normalized_name,
                    "memory_text": memory_text,
                }
            ))
            
            cursor.execute("""
                UPDATE ira_memory.entity_memories
                SET embedding_id = %s
                WHERE id = %s
            """, (point_id, mem_id))
        
        qdrant.upsert(collection_name=NEW_ENTITY_COLLECTION, points=points)
        migrated += len(points)
        print(f"  Migrated {migrated}/{len(memories)} entity memories...")
    
    conn.commit()
    print(f"Successfully migrated {migrated} entity memories to Voyage-3")


def verify_migration():
    """Verify migration completed successfully."""
    print("\n" + "=" * 60)
    print("VERIFYING MIGRATION")
    print("=" * 60)
    
    conn = get_db()
    cursor = conn.cursor()
    qdrant = get_qdrant()
    
    # Count DB records
    cursor.execute("SELECT COUNT(*) FROM ira_memory.user_memories WHERE is_active = TRUE")
    db_user_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM ira_memory.entity_memories WHERE is_active = TRUE")
    db_entity_count = cursor.fetchone()[0]
    
    # Count Qdrant points
    old_user_count = get_old_collection_count(qdrant, OLD_USER_COLLECTION)
    new_user_count = get_old_collection_count(qdrant, NEW_USER_COLLECTION)
    old_entity_count = get_old_collection_count(qdrant, OLD_ENTITY_COLLECTION)
    new_entity_count = get_old_collection_count(qdrant, NEW_ENTITY_COLLECTION)
    
    print(f"\nUser Memories:")
    print(f"  Database (active): {db_user_count}")
    print(f"  Old collection ({OLD_USER_COLLECTION}): {old_user_count}")
    print(f"  New collection ({NEW_USER_COLLECTION}): {new_user_count}")
    
    print(f"\nEntity Memories:")
    print(f"  Database (active): {db_entity_count}")
    print(f"  Old collection ({OLD_ENTITY_COLLECTION}): {old_entity_count}")
    print(f"  New collection ({NEW_ENTITY_COLLECTION}): {new_entity_count}")
    
    # Check migration status
    if new_user_count >= db_user_count and new_entity_count >= db_entity_count:
        print("\n✓ Migration appears complete!")
        print("  You can safely delete old collections with:")
        print(f"    qdrant.delete_collection('{OLD_USER_COLLECTION}')")
        print(f"    qdrant.delete_collection('{OLD_ENTITY_COLLECTION}')")
    else:
        print("\n⚠ Migration may be incomplete. Run migration script without --dry-run.")


def main():
    parser = argparse.ArgumentParser(description="Migrate memories from OpenAI to Voyage-3 embeddings")
    parser.add_argument("--dry-run", action="store_true", help="Preview without making changes")
    parser.add_argument("--verify", action="store_true", help="Verify migration status")
    parser.add_argument("--user-only", action="store_true", help="Only migrate user memories")
    parser.add_argument("--entity-only", action="store_true", help="Only migrate entity memories")
    
    args = parser.parse_args()
    
    if not VOYAGE_API_KEY:
        print("ERROR: VOYAGE_API_KEY not set")
        sys.exit(1)
    
    print("=" * 60)
    print("MEMORY MIGRATION: OpenAI -> Voyage-3")
    print("=" * 60)
    print(f"Voyage API Key: {VOYAGE_API_KEY[:15]}...")
    print(f"Qdrant URL: {QDRANT_URL}")
    print(f"Database: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else DATABASE_URL}")
    
    if args.verify:
        verify_migration()
        return
    
    if args.dry_run:
        print("\n[DRY RUN MODE - No changes will be made]")
    
    try:
        if not args.entity_only:
            migrate_user_memories(dry_run=args.dry_run)
        
        if not args.user_only:
            migrate_entity_memories(dry_run=args.dry_run)
        
        if not args.dry_run:
            print("\n" + "=" * 60)
            print("MIGRATION COMPLETE")
            print("=" * 60)
            print("Run with --verify to confirm migration status")
            
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
