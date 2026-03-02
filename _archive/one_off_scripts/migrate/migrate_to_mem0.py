#!/usr/bin/env python3
"""
Migrate existing PostgreSQL memories to Mem0.

This script:
1. Reads all user memories from PostgreSQL
2. Adds them to Mem0 with proper user_id mapping
3. Reports migration stats
"""

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "openclaw" / "agents" / "ira" / "skills" / "memory"))

# Load env
env_file = PROJECT_ROOT / ".env"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        if line.strip() and not line.startswith('#') and '=' in line:
            key, _, value = line.partition('=')
            os.environ.setdefault(key.strip(), value.strip().strip('"'))


def migrate_memories():
    """Migrate PostgreSQL memories to Mem0."""
    import sys
    print("=" * 60, flush=True)
    print("MIGRATING POSTGRESQL MEMORIES TO MEM0", flush=True)
    print("=" * 60, flush=True)
    
    # Initialize Mem0
    try:
        from mem0_memory import get_mem0_service
        mem0 = get_mem0_service()
        print("✅ Mem0 connected")
    except Exception as e:
        print(f"❌ Mem0 connection failed: {e}")
        return
    
    # Connect to PostgreSQL
    try:
        import psycopg2
        db_url = os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL")
        if not db_url:
            print("❌ No DATABASE_URL found")
            return
        
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()
        print("✅ PostgreSQL connected")
    except Exception as e:
        print(f"❌ PostgreSQL connection failed: {e}")
        return
    
    # Get all user memories
    try:
        cursor.execute("""
            SELECT identity_id, memory_text, memory_type, source_channel, confidence, created_at
            FROM ira_memory.user_memories
            WHERE is_active = true
            ORDER BY created_at DESC
        """)
        user_memories = cursor.fetchall()
        print(f"\n📚 Found {len(user_memories)} user memories in PostgreSQL")
    except Exception as e:
        print(f"❌ Failed to fetch user memories: {e}")
        user_memories = []
    
    # Get all entity memories
    try:
        cursor.execute("""
            SELECT entity_type, entity_name, memory_text, memory_type, confidence, created_at
            FROM ira_memory.entity_memories
            WHERE is_active = true
            ORDER BY created_at DESC
        """)
        entity_memories = cursor.fetchall()
        print(f"📚 Found {len(entity_memories)} entity memories in PostgreSQL")
    except Exception as e:
        print(f"❌ Failed to fetch entity memories: {e}")
        entity_memories = []
    
    # Migrate user memories
    print("\n" + "-" * 40)
    print("MIGRATING USER MEMORIES")
    print("-" * 40)
    
    migrated = 0
    failed = 0
    skipped = 0
    
    for identity_id, memory_text, memory_type, source_channel, confidence, created_at in user_memories:
        if not memory_text or len(memory_text.strip()) < 5:
            skipped += 1
            continue
        
        try:
            # Add to Mem0
            result = mem0.add_memory(
                text=memory_text,
                user_id=identity_id,
                metadata={
                    "memory_type": memory_type,
                    "source_channel": source_channel or "migration",
                    "confidence": confidence,
                    "migrated_from": "postgresql",
                    "original_created_at": str(created_at) if created_at else None,
                }
            )
            
            if result:
                migrated += 1
                if migrated % 50 == 0:
                    print(f"  Migrated {migrated} memories...")
            else:
                failed += 1
                
        except Exception as e:
            failed += 1
            if failed <= 5:
                print(f"  ⚠️ Failed: {str(e)[:50]}")
    
    print(f"\n✅ User memories migrated: {migrated}")
    print(f"❌ Failed: {failed}")
    print(f"⏭️ Skipped (empty): {skipped}")
    
    # Migrate entity memories as agent memories
    print("\n" + "-" * 40)
    print("MIGRATING ENTITY MEMORIES")
    print("-" * 40)
    
    entity_migrated = 0
    entity_failed = 0
    
    for entity_type, entity_name, memory_text, memory_type, confidence, created_at in entity_memories:
        if not memory_text or len(memory_text.strip()) < 5:
            continue
        
        try:
            result = mem0.add_entity_memory(
                entity_type=entity_type,
                entity_name=entity_name,
                memory_text=memory_text,
                source_user_id="migration",
            )
            
            if result:
                entity_migrated += 1
                if entity_migrated % 50 == 0:
                    print(f"  Migrated {entity_migrated} entity memories...")
            else:
                entity_failed += 1
                
        except Exception as e:
            entity_failed += 1
            if entity_failed <= 5:
                print(f"  ⚠️ Failed: {str(e)[:50]}")
    
    print(f"\n✅ Entity memories migrated: {entity_migrated}")
    print(f"❌ Failed: {entity_failed}")
    
    # Summary
    print("\n" + "=" * 60)
    print("MIGRATION COMPLETE")
    print("=" * 60)
    print(f"Total user memories migrated: {migrated}")
    print(f"Total entity memories migrated: {entity_migrated}")
    print(f"Total: {migrated + entity_migrated}")
    print("\nCheck Mem0 dashboard: https://app.mem0.ai/dashboard")
    
    conn.close()


if __name__ == "__main__":
    migrate_memories()
