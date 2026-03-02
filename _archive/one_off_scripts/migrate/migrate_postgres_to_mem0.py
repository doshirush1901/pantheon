#!/usr/bin/env python3
"""
POSTGRESQL TO MEM0 MIGRATION SCRIPT

Migrates existing PostgreSQL data to Mem0 + JSON storage.

Data migrated:
1. ira_memory.episodes → Mem0 + episodes.json
2. ira_memory.procedures → Mem0 + procedures.json  
3. ira_memory.entity_memories → Mem0 entity memories
4. ira_memory.user_memories → Mem0 user memories

Usage:
    python scripts/migrate_postgres_to_mem0.py --dry-run   # Preview
    python scripts/migrate_postgres_to_mem0.py --migrate   # Execute
    python scripts/migrate_postgres_to_mem0.py --status    # Check status
"""

import os
import sys
import json
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

# Project setup
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Load env
env_file = PROJECT_ROOT / ".env"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        if line.strip() and not line.startswith('#') and '=' in line:
            key, _, value = line.partition('=')
            os.environ.setdefault(key.strip(), value.strip().strip('"'))

DATABASE_URL = os.environ.get("DATABASE_URL", "")
MEM0_API_KEY = os.environ.get("MEM0_API_KEY", "")

# Output directories
DATA_DIR = PROJECT_ROOT / "data" / "mem0_storage"
MIGRATION_LOG = DATA_DIR / "migration_log.json"


class PostgresMigrator:
    """Migrates PostgreSQL data to Mem0."""
    
    def __init__(self):
        self._pg_conn = None
        self._mem0 = None
        self.stats = {
            "episodes_migrated": 0,
            "procedures_migrated": 0,
            "entity_memories_migrated": 0,
            "user_memories_migrated": 0,
            "errors": [],
        }
    
    def _get_pg(self):
        """Get PostgreSQL connection."""
        if self._pg_conn is None and DATABASE_URL:
            try:
                import psycopg2
                import psycopg2.extras
                self._pg_conn = psycopg2.connect(DATABASE_URL)
                psycopg2.extras.register_uuid()
            except Exception as e:
                print(f"[migrate] PostgreSQL unavailable: {e}")
        return self._pg_conn
    
    def _get_mem0(self):
        """Get Mem0 client."""
        if self._mem0 is None and MEM0_API_KEY:
            try:
                from mem0 import MemoryClient
                self._mem0 = MemoryClient(api_key=MEM0_API_KEY)
            except Exception as e:
                print(f"[migrate] Mem0 unavailable: {e}")
        return self._mem0
    
    def check_postgres_tables(self) -> Dict[str, int]:
        """Check what tables exist and their row counts."""
        conn = self._get_pg()
        if not conn:
            return {"error": "No PostgreSQL connection"}
        
        tables = {}
        
        # Check episodes
        try:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM ira_memory.episodes")
            tables["ira_memory.episodes"] = cur.fetchone()[0]
            cur.close()
        except:
            tables["ira_memory.episodes"] = 0
        
        # Check procedures
        try:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM ira_memory.procedures")
            tables["ira_memory.procedures"] = cur.fetchone()[0]
            cur.close()
        except:
            tables["ira_memory.procedures"] = 0
        
        # Check entity memories
        try:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM ira_memory.entity_memories")
            tables["ira_memory.entity_memories"] = cur.fetchone()[0]
            cur.close()
        except:
            tables["ira_memory.entity_memories"] = 0
        
        # Check user memories
        try:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM ira_memory.user_memories")
            tables["ira_memory.user_memories"] = cur.fetchone()[0]
            cur.close()
        except:
            tables["ira_memory.user_memories"] = 0
        
        # Check market research
        try:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM companies")
            tables["companies"] = cur.fetchone()[0]
            cur.close()
        except:
            tables["companies"] = 0
        
        # Commit to release any locks
        conn.commit()
        
        return tables
    
    def migrate_episodes(self, dry_run: bool = True) -> int:
        """Migrate episodes from PostgreSQL to Mem0 + JSON."""
        conn = self._get_pg()
        if not conn:
            return 0
        
        cur = conn.cursor()
        try:
            cur.execute("""
                SELECT id, identity_id, timestamp, episode_type, summary,
                       key_topics, outcome, channel, emotional_valence, importance
                FROM ira_memory.episodes
                ORDER BY timestamp DESC
                LIMIT 1000
            """)
            rows = cur.fetchall()
        except Exception as e:
            self.stats["errors"].append(f"Episodes query failed: {e}")
            return 0
        
        if dry_run:
            print(f"[dry-run] Would migrate {len(rows)} episodes")
            return len(rows)
        
        # Migrate to JSON
        episodes_data = {}
        mem0 = self._get_mem0()
        
        for row in rows:
            ep_id, identity_id, timestamp, ep_type, summary, topics, outcome, channel, valence, importance = row
            
            # Store locally
            if identity_id not in episodes_data:
                episodes_data[identity_id] = {}
            
            episodes_data[identity_id][str(ep_id)] = {
                "id": str(ep_id),
                "identity_id": identity_id,
                "timestamp": timestamp.isoformat() if timestamp else "",
                "summary": summary or "",
                "topics": topics if isinstance(topics, list) else [],
                "outcome": outcome or "",
                "channel": channel or "unknown",
                "emotional_valence": valence or 0,
                "importance": importance or 0.5,
            }
            
            # Store in Mem0
            if mem0 and summary:
                try:
                    text = f"Episode {timestamp}: {summary}"
                    if outcome:
                        text += f" Outcome: {outcome}"
                    
                    mem0.add(
                        messages=[{"role": "user", "content": text}],
                        user_id=identity_id,
                        metadata={
                            "type": "episode",
                            "episode_id": str(ep_id),
                            "channel": channel,
                            "migrated_from": "postgresql",
                        }
                    )
                    self.stats["episodes_migrated"] += 1
                except Exception as e:
                    self.stats["errors"].append(f"Mem0 episode store failed: {e}")
        
        # Save to JSON
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        episodes_file = DATA_DIR / "episodes.json"
        
        # Merge with existing
        if episodes_file.exists():
            existing = json.loads(episodes_file.read_text())
            for identity_id, eps in episodes_data.items():
                if identity_id not in existing:
                    existing[identity_id] = {}
                existing[identity_id].update(eps)
            episodes_data = existing
        
        episodes_file.write_text(json.dumps(episodes_data, indent=2, default=str))
        
        return len(rows)
    
    def migrate_procedures(self, dry_run: bool = True) -> int:
        """Migrate procedures from PostgreSQL to Mem0 + JSON."""
        conn = self._get_pg()
        if not conn:
            return 0
        
        cur = conn.cursor()
        try:
            cur.execute("""
                SELECT id, name, trigger_patterns, steps, description,
                       success_count, failure_count, confidence, source
                FROM ira_memory.procedures
                WHERE is_active = TRUE OR is_active IS NULL
            """)
            rows = cur.fetchall()
        except Exception as e:
            self.stats["errors"].append(f"Procedures query failed: {e}")
            return 0
        
        if dry_run:
            print(f"[dry-run] Would migrate {len(rows)} procedures")
            return len(rows)
        
        procedures_data = {}
        mem0 = self._get_mem0()
        
        for row in rows:
            proc_id, name, triggers, steps, desc, success, failure, confidence, source = row
            
            procedures_data[str(proc_id)] = {
                "id": str(proc_id),
                "name": name,
                "trigger_patterns": triggers if isinstance(triggers, list) else [],
                "steps": steps if isinstance(steps, list) else [],
                "description": desc or "",
                "success_count": success or 0,
                "failure_count": failure or 0,
                "confidence": confidence or 0.5,
                "source": source or "learned",
            }
            
            # Store in Mem0
            if mem0 and name:
                try:
                    text = f"Procedure: {name}\nTriggers: {triggers}\nDescription: {desc}"
                    mem0.add(
                        messages=[{"role": "user", "content": text}],
                        agent_id="ira_procedures",
                        metadata={
                            "type": "procedure",
                            "procedure_id": str(proc_id),
                            "migrated_from": "postgresql",
                        }
                    )
                    self.stats["procedures_migrated"] += 1
                except Exception as e:
                    self.stats["errors"].append(f"Mem0 procedure store failed: {e}")
        
        # Save to JSON
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        procedures_file = DATA_DIR / "procedures.json"
        
        # Merge with existing
        if procedures_file.exists():
            existing = json.loads(procedures_file.read_text())
            existing.update(procedures_data)
            procedures_data = existing
        
        procedures_file.write_text(json.dumps(procedures_data, indent=2))
        
        return len(rows)
    
    def migrate_entity_memories(self, dry_run: bool = True) -> int:
        """Migrate entity memories to Mem0."""
        conn = self._get_pg()
        if not conn:
            return 0
        
        cur = conn.cursor()
        try:
            cur.execute("""
                SELECT id, entity_name, entity_type, memory_text, confidence, source_channel
                FROM ira_memory.entity_memories
                WHERE is_active = TRUE
                LIMIT 2000
            """)
            rows = cur.fetchall()
        except Exception as e:
            self.stats["errors"].append(f"Entity memories query failed: {e}")
            return 0
        
        if dry_run:
            print(f"[dry-run] Would migrate {len(rows)} entity memories")
            return len(rows)
        
        mem0 = self._get_mem0()
        if not mem0:
            return 0
        
        for row in rows:
            mem_id, entity_name, entity_type, text, confidence, source = row
            
            try:
                agent_id = f"entity_{entity_type}_{entity_name}".lower().replace(" ", "_")[:50]
                mem0.add(
                    messages=[{"role": "user", "content": text}],
                    agent_id=agent_id,
                    metadata={
                        "type": "entity_memory",
                        "entity_name": entity_name,
                        "entity_type": entity_type,
                        "confidence": confidence,
                        "migrated_from": "postgresql",
                    }
                )
                self.stats["entity_memories_migrated"] += 1
            except Exception as e:
                self.stats["errors"].append(f"Mem0 entity store failed: {e}")
        
        return len(rows)
    
    def migrate_user_memories(self, dry_run: bool = True) -> int:
        """Migrate user memories to Mem0."""
        conn = self._get_pg()
        if not conn:
            return 0
        
        cur = conn.cursor()
        try:
            cur.execute("""
                SELECT id, identity_id, memory_text, confidence, source_channel
                FROM ira_memory.user_memories
                WHERE is_active = TRUE
                LIMIT 500
            """)
            rows = cur.fetchall()
        except Exception as e:
            self.stats["errors"].append(f"User memories query failed: {e}")
            return 0
        
        if dry_run:
            print(f"[dry-run] Would migrate {len(rows)} user memories")
            return len(rows)
        
        mem0 = self._get_mem0()
        if not mem0:
            return 0
        
        for row in rows:
            mem_id, identity_id, text, confidence, source = row
            
            try:
                mem0.add(
                    messages=[{"role": "user", "content": text}],
                    user_id=identity_id,
                    metadata={
                        "type": "user_memory",
                        "confidence": confidence,
                        "source": source,
                        "migrated_from": "postgresql",
                    }
                )
                self.stats["user_memories_migrated"] += 1
            except Exception as e:
                self.stats["errors"].append(f"Mem0 user store failed: {e}")
        
        return len(rows)
    
    def run_migration(self, dry_run: bool = True):
        """Run full migration."""
        print("\n" + "=" * 60)
        print("POSTGRESQL TO MEM0 MIGRATION")
        print("=" * 60)
        
        if dry_run:
            print("\n⚠️  DRY RUN MODE - No data will be modified\n")
        
        # Check current state
        print("\n📊 Current PostgreSQL Data:")
        tables = self.check_postgres_tables()
        for table, count in tables.items():
            print(f"   {table}: {count} rows")
        
        if "error" in tables:
            print("\n❌ Cannot connect to PostgreSQL. Migration aborted.")
            return
        
        total_rows = sum(v for v in tables.values() if isinstance(v, int))
        if total_rows == 0:
            print("\n✅ No data to migrate (PostgreSQL tables are empty)")
            return
        
        # Run migration
        print(f"\n{'🔍 Preview' if dry_run else '🚀 Migrating'}:")
        
        episodes = self.migrate_episodes(dry_run)
        procedures = self.migrate_procedures(dry_run)
        entities = self.migrate_entity_memories(dry_run)
        users = self.migrate_user_memories(dry_run)
        
        # Summary
        print("\n" + "=" * 60)
        if dry_run:
            print("DRY RUN SUMMARY")
            print("=" * 60)
            print(f"   Episodes to migrate: {episodes}")
            print(f"   Procedures to migrate: {procedures}")
            print(f"   Entity memories to migrate: {entities}")
            print(f"   User memories to migrate: {users}")
            print(f"\n   Total: {episodes + procedures + entities + users} items")
            print("\n   Run with --migrate to execute")
        else:
            print("MIGRATION COMPLETE")
            print("=" * 60)
            print(f"   Episodes migrated: {self.stats['episodes_migrated']}")
            print(f"   Procedures migrated: {self.stats['procedures_migrated']}")
            print(f"   Entity memories migrated: {self.stats['entity_memories_migrated']}")
            print(f"   User memories migrated: {self.stats['user_memories_migrated']}")
            
            if self.stats["errors"]:
                print(f"\n   ⚠️  Errors: {len(self.stats['errors'])}")
                for err in self.stats["errors"][:5]:
                    print(f"      - {err}")
            
            # Save migration log
            MIGRATION_LOG.parent.mkdir(parents=True, exist_ok=True)
            log_data = {
                "migrated_at": datetime.now().isoformat(),
                "stats": self.stats,
            }
            MIGRATION_LOG.write_text(json.dumps(log_data, indent=2))
            print(f"\n   Log saved to: {MIGRATION_LOG}")


def main():
    parser = argparse.ArgumentParser(description="Migrate PostgreSQL to Mem0")
    parser.add_argument("--dry-run", action="store_true", help="Preview without migrating")
    parser.add_argument("--migrate", action="store_true", help="Execute migration")
    parser.add_argument("--status", action="store_true", help="Show current status")
    args = parser.parse_args()
    
    migrator = PostgresMigrator()
    
    if args.status:
        print("\n📊 PostgreSQL Tables:")
        tables = migrator.check_postgres_tables()
        for table, count in tables.items():
            print(f"   {table}: {count} rows")
        
        print("\n📁 Local JSON Storage:")
        for f in ["episodes.json", "procedures.json", "relationships.json"]:
            path = DATA_DIR / f
            if path.exists():
                data = json.loads(path.read_text())
                count = len(data) if isinstance(data, dict) else 0
                print(f"   {f}: {count} entries")
            else:
                print(f"   {f}: not created yet")
    
    elif args.migrate:
        migrator.run_migration(dry_run=False)
    
    else:
        # Default to dry-run
        migrator.run_migration(dry_run=True)


if __name__ == "__main__":
    main()
