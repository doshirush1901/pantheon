"""
Unified Identity Layer
======================

Single source of truth for contact identity across all systems.

Previously we had 3 separate identity stores:
1. relationship_store.py (SQLite) - contacts table
2. memory_service.py (JSON) - identity_links.json  
3. persistent_memory.py (PostgreSQL) - identity_id in user_memories

This module consolidates them into one canonical source.

Usage:
    from openclaw.agents.ira.src.identity import get_identity_service
    
    identity = get_identity_service()
    contact_id = identity.resolve("email", "john@example.com")
    identity.link("email", "john@example.com", "telegram", "123456")
"""

import os
import sys
import sqlite3
import json
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from contextlib import contextmanager

# Use centralized config
AGENT_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(AGENT_DIR))

try:
    from config import (
        ensure_schema, get_sqlite_connection, get_logger,
        setup_import_paths
    )
    setup_import_paths()
    CONFIG_AVAILABLE = True
    _logger = get_logger(__name__)
except ImportError:
    CONFIG_AVAILABLE = False
    import logging
    _logger = logging.getLogger(__name__)


@dataclass
class Contact:
    """Unified contact identity."""
    contact_id: str
    name: Optional[str] = None
    email: Optional[str] = None
    telegram_id: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    metadata: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "contact_id": self.contact_id,
            "name": self.name,
            "email": self.email,
            "telegram_id": self.telegram_id,
            "phone": self.phone,
            "company": self.company,
            "created_at": self.created_at,
            "metadata": self.metadata,
        }


class UnifiedIdentityService:
    """
    Canonical identity service that all systems should use.
    
    Stores identity data in SQLite for persistence.
    Provides simple resolve/link/merge operations.
    """
    
    # Schema version for migrations
    SCHEMA_VERSION = 1
    
    # Migrations by version number
    SCHEMA_MIGRATIONS = {
        1: [
            # Initial schema
            '''CREATE TABLE IF NOT EXISTS contacts (
                contact_id TEXT PRIMARY KEY,
                name TEXT,
                email TEXT,
                telegram_id TEXT,
                phone TEXT,
                company TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT DEFAULT '{}'
            )''',
            "CREATE INDEX IF NOT EXISTS idx_contacts_email ON contacts(email)",
            "CREATE INDEX IF NOT EXISTS idx_contacts_telegram ON contacts(telegram_id)",
            "CREATE INDEX IF NOT EXISTS idx_contacts_phone ON contacts(phone)",
            # Channel mappings for flexible identity resolution
            '''CREATE TABLE IF NOT EXISTS identity_mappings (
                channel TEXT,
                identifier TEXT,
                contact_id TEXT,
                confidence REAL DEFAULT 1.0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (channel, identifier),
                FOREIGN KEY (contact_id) REFERENCES contacts(contact_id)
            )''',
            "CREATE INDEX IF NOT EXISTS idx_mappings_contact ON identity_mappings(contact_id)",
            # Merge history (for audit trail)
            '''CREATE TABLE IF NOT EXISTS merge_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_contact_id TEXT,
                to_contact_id TEXT,
                reason TEXT,
                merged_at TEXT DEFAULT CURRENT_TIMESTAMP
            )''',
        ],
        # Future migrations go here:
        # 2: ["ALTER TABLE contacts ADD COLUMN ...", ...],
    }
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            base_dir = Path(__file__).parent.parent.parent.parent.parent.parent
            db_path = str(base_dir / "data" / "unified_identity.db")
        
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._ensure_db()
    
    def _ensure_db(self):
        """Create tables if they don't exist, applying migrations as needed."""
        if CONFIG_AVAILABLE:
            # Use centralized schema versioning
            self._conn = ensure_schema(
                self.db_path,
                "unified_identity",
                self.SCHEMA_VERSION,
                self.SCHEMA_MIGRATIONS,
            )
        else:
            # Fallback: Apply schema directly without versioning
            with self._get_conn() as conn:
                for statements in self.SCHEMA_MIGRATIONS.values():
                    for stmt in statements:
                        conn.execute(stmt)
                conn.commit()
    
    @contextmanager
    def _get_conn(self):
        """Get SQLite connection with row factory and WAL mode."""
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=30000")
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    # =========================================================================
    # CORE OPERATIONS
    # =========================================================================
    
    def resolve(
        self,
        channel: str,
        identifier: str,
        create_if_missing: bool = True,
        name: str = None,
    ) -> Optional[str]:
        """
        Resolve a channel:identifier to a contact_id.
        
        Args:
            channel: Channel type (email, telegram, phone, etc.)
            identifier: The identifier on that channel
            create_if_missing: Create a new contact if not found
            name: Optional name for new contacts
        
        Returns:
            contact_id or None
        """
        if not channel or not identifier:
            return None
        
        identifier = str(identifier).strip().lower()
        
        with self._get_conn() as conn:
            # Check mapping table first
            row = conn.execute("""
                SELECT contact_id FROM identity_mappings
                WHERE channel = ? AND identifier = ?
            """, (channel, identifier)).fetchone()
            
            if row:
                return row["contact_id"]
            
            # Check direct columns
            column_map = {
                "email": "email",
                "telegram": "telegram_id",
                "phone": "phone",
            }
            
            if channel in column_map:
                col = column_map[channel]
                row = conn.execute(f"""
                    SELECT contact_id FROM contacts
                    WHERE LOWER({col}) = ?
                """, (identifier,)).fetchone()
                
                if row:
                    # Add mapping for faster future lookups
                    conn.execute("""
                        INSERT OR IGNORE INTO identity_mappings (channel, identifier, contact_id)
                        VALUES (?, ?, ?)
                    """, (channel, identifier, row["contact_id"]))
                    return row["contact_id"]
            
            # Not found - create if requested
            if create_if_missing:
                return self._create_contact(
                    channel=channel,
                    identifier=identifier,
                    name=name,
                )
            
            return None
    
    def _create_contact(
        self,
        channel: str,
        identifier: str,
        name: str = None,
    ) -> str:
        """Create a new contact from channel:identifier."""
        import uuid
        
        contact_id = f"c_{uuid.uuid4().hex[:12]}"
        now = datetime.now().isoformat()
        
        # Determine which column to populate
        email = identifier if channel == "email" else None
        telegram_id = identifier if channel == "telegram" else None
        phone = identifier if channel == "phone" else None
        
        # Auto-generate name from email if not provided
        if not name and email:
            name = email.split("@")[0].replace(".", " ").replace("_", " ").title()
        
        with self._get_conn() as conn:
            conn.execute("""
                INSERT INTO contacts (contact_id, name, email, telegram_id, phone, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (contact_id, name, email, telegram_id, phone, now, now))
            
            # Add mapping
            conn.execute("""
                INSERT INTO identity_mappings (channel, identifier, contact_id)
                VALUES (?, ?, ?)
            """, (channel, identifier, contact_id))
        
        _logger.info("Created contact %s from %s:%s", contact_id, channel, identifier)
        return contact_id
    
    def link(
        self,
        channel1: str,
        identifier1: str,
        channel2: str,
        identifier2: str,
        confidence: float = 1.0,
    ) -> Optional[str]:
        """
        Link two identifiers to the same contact.
        
        If both exist as separate contacts, merges them.
        If one exists, adds the other to it.
        If neither exists, creates a new contact with both.
        
        Returns the unified contact_id.
        """
        id1 = str(identifier1).strip().lower()
        id2 = str(identifier2).strip().lower()
        
        # Resolve existing contacts
        contact1 = self.resolve(channel1, id1, create_if_missing=False)
        contact2 = self.resolve(channel2, id2, create_if_missing=False)
        
        with self._get_conn() as conn:
            if contact1 and contact2:
                if contact1 == contact2:
                    return contact1  # Already linked
                
                # Merge contact2 into contact1
                return self._merge_contacts(contact1, contact2)
            
            elif contact1:
                # Add identifier2 to contact1
                self._add_identifier(contact1, channel2, id2, confidence)
                return contact1
            
            elif contact2:
                # Add identifier1 to contact2
                self._add_identifier(contact2, channel1, id1, confidence)
                return contact2
            
            else:
                # Create new contact with both
                contact_id = self._create_contact(channel1, id1)
                self._add_identifier(contact_id, channel2, id2, confidence)
                return contact_id
    
    def _add_identifier(
        self,
        contact_id: str,
        channel: str,
        identifier: str,
        confidence: float = 1.0,
    ):
        """Add an identifier to an existing contact."""
        with self._get_conn() as conn:
            # Add mapping
            conn.execute("""
                INSERT OR REPLACE INTO identity_mappings (channel, identifier, contact_id, confidence)
                VALUES (?, ?, ?, ?)
            """, (channel, identifier, contact_id, confidence))
            
            # Update direct column if applicable
            column_map = {
                "email": "email",
                "telegram": "telegram_id", 
                "phone": "phone",
            }
            
            if channel in column_map:
                col = column_map[channel]
                conn.execute(f"""
                    UPDATE contacts SET {col} = ?, updated_at = ?
                    WHERE contact_id = ? AND ({col} IS NULL OR {col} = '')
                """, (identifier, datetime.now().isoformat(), contact_id))
        
        _logger.info("Added %s:%s to contact %s", channel, identifier, contact_id)
    
    def _merge_contacts(self, keep_id: str, merge_id: str) -> str:
        """Merge merge_id into keep_id."""
        with self._get_conn() as conn:
            # Get merge contact data
            merge_data = conn.execute("""
                SELECT * FROM contacts WHERE contact_id = ?
            """, (merge_id,)).fetchone()
            
            if merge_data:
                # Update keep contact with any missing data from merge
                updates = []
                params = []
                
                for col in ["name", "email", "telegram_id", "phone", "company"]:
                    if merge_data[col]:
                        updates.append(f"{col} = COALESCE(NULLIF({col}, ''), ?)")
                        params.append(merge_data[col])
                
                if updates:
                    params.append(datetime.now().isoformat())
                    params.append(keep_id)
                    conn.execute(f"""
                        UPDATE contacts SET {', '.join(updates)}, updated_at = ?
                        WHERE contact_id = ?
                    """, params)
            
            # Move all mappings from merge to keep
            conn.execute("""
                UPDATE identity_mappings SET contact_id = ?
                WHERE contact_id = ?
            """, (keep_id, merge_id))
            
            # Record merge history
            conn.execute("""
                INSERT INTO merge_history (from_contact_id, to_contact_id, reason)
                VALUES (?, ?, 'identity_link')
            """, (merge_id, keep_id))
            
            # Delete merged contact
            conn.execute("DELETE FROM contacts WHERE contact_id = ?", (merge_id,))
        
        _logger.info("Merged %s into %s", merge_id, keep_id)
        return keep_id
    
    # =========================================================================
    # QUERY OPERATIONS
    # =========================================================================
    
    def get_contact(self, contact_id: str) -> Optional[Contact]:
        """Get contact by ID."""
        with self._get_conn() as conn:
            row = conn.execute("""
                SELECT * FROM contacts WHERE contact_id = ?
            """, (contact_id,)).fetchone()
            
            if not row:
                return None
            
            return Contact(
                contact_id=row["contact_id"],
                name=row["name"],
                email=row["email"],
                telegram_id=row["telegram_id"],
                phone=row["phone"],
                company=row["company"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                metadata=json.loads(row["metadata"] or "{}"),
            )
    
    def update_contact(
        self,
        contact_id: str,
        name: str = None,
        company: str = None,
        metadata: Dict = None,
    ):
        """Update contact details."""
        updates = []
        params = []
        
        if name:
            updates.append("name = ?")
            params.append(name)
        if company:
            updates.append("company = ?")
            params.append(company)
        if metadata:
            updates.append("metadata = ?")
            params.append(json.dumps(metadata))
        
        if not updates:
            return
        
        updates.append("updated_at = ?")
        params.append(datetime.now().isoformat())
        params.append(contact_id)
        
        with self._get_conn() as conn:
            conn.execute(f"""
                UPDATE contacts SET {', '.join(updates)}
                WHERE contact_id = ?
            """, params)
    
    def get_all_identifiers(self, contact_id: str) -> List[Tuple[str, str]]:
        """Get all channel:identifier pairs for a contact."""
        with self._get_conn() as conn:
            rows = conn.execute("""
                SELECT channel, identifier FROM identity_mappings
                WHERE contact_id = ?
            """, (contact_id,)).fetchall()
            
            return [(row["channel"], row["identifier"]) for row in rows]
    
    def search_contacts(
        self,
        query: str,
        limit: int = 10,
    ) -> List[Contact]:
        """Search contacts by name, email, or company."""
        query_lower = f"%{query.lower()}%"
        
        with self._get_conn() as conn:
            rows = conn.execute("""
                SELECT * FROM contacts
                WHERE LOWER(name) LIKE ?
                   OR LOWER(email) LIKE ?
                   OR LOWER(company) LIKE ?
                ORDER BY updated_at DESC
                LIMIT ?
            """, (query_lower, query_lower, query_lower, limit)).fetchall()
            
            return [
                Contact(
                    contact_id=row["contact_id"],
                    name=row["name"],
                    email=row["email"],
                    telegram_id=row["telegram_id"],
                    phone=row["phone"],
                    company=row["company"],
                    created_at=row["created_at"],
                    metadata=json.loads(row["metadata"] or "{}"),
                )
                for row in rows
            ]
    
    def get_stats(self) -> Dict:
        """Get identity stats."""
        with self._get_conn() as conn:
            total = conn.execute("SELECT COUNT(*) as c FROM contacts").fetchone()["c"]
            with_email = conn.execute(
                "SELECT COUNT(*) as c FROM contacts WHERE email IS NOT NULL"
            ).fetchone()["c"]
            with_telegram = conn.execute(
                "SELECT COUNT(*) as c FROM contacts WHERE telegram_id IS NOT NULL"
            ).fetchone()["c"]
            multi_channel = conn.execute("""
                SELECT COUNT(*) as c FROM contacts
                WHERE (email IS NOT NULL) + (telegram_id IS NOT NULL) + (phone IS NOT NULL) > 1
            """).fetchone()["c"]
            
            return {
                "total_contacts": total,
                "with_email": with_email,
                "with_telegram": with_telegram,
                "multi_channel": multi_channel,
            }
    
    # =========================================================================
    # MIGRATION HELPERS
    # =========================================================================
    
    def import_from_memory_service(self, links_file: str) -> Dict[str, int]:
        """
        Import identities from memory_service's identity_links.json.
        
        Returns counts of imported/skipped.
        """
        try:
            with open(links_file) as f:
                links = json.load(f)
        except Exception as e:
            return {"imported": 0, "skipped": 0, "error": str(e)}
        
        imported = 0
        skipped = 0
        
        for key, identity_id in links.get("mappings", {}).items():
            try:
                channel, identifier = key.split(":", 1)
                existing = self.resolve(channel, identifier, create_if_missing=False)
                
                if not existing:
                    self.resolve(channel, identifier, create_if_missing=True)
                    imported += 1
                else:
                    skipped += 1
            except Exception:
                skipped += 1
        
        return {"imported": imported, "skipped": skipped}
    
    def import_from_relationship_store(self, db_path: str) -> Dict[str, int]:
        """
        Import contacts from relationship_store SQLite.
        
        Returns counts.
        """
        try:
            src_conn = sqlite3.connect(db_path)
            src_conn.row_factory = sqlite3.Row
            
            rows = src_conn.execute("SELECT * FROM contacts").fetchall()
            src_conn.close()
        except Exception as e:
            return {"imported": 0, "skipped": 0, "error": str(e)}
        
        imported = 0
        skipped = 0
        
        for row in rows:
            try:
                email = row["email"]
                telegram_id = row["telegram_id"]
                
                if email:
                    contact_id = self.resolve("email", email, create_if_missing=True, name=row["name"])
                    if telegram_id:
                        self.link("email", email, "telegram", telegram_id)
                    imported += 1
                elif telegram_id:
                    self.resolve("telegram", telegram_id, create_if_missing=True, name=row["name"])
                    imported += 1
                else:
                    skipped += 1
            except Exception:
                skipped += 1
        
        return {"imported": imported, "skipped": skipped}


# Module-level singleton
_service: Optional[UnifiedIdentityService] = None


def get_identity_service() -> UnifiedIdentityService:
    """Get or create the identity service singleton."""
    global _service
    if _service is None:
        _service = UnifiedIdentityService()
    return _service


def resolve_identity(
    channel: str,
    identifier: str,
    create_if_missing: bool = True,
    name: str = None,
) -> Optional[str]:
    """Convenience function to resolve identity."""
    return get_identity_service().resolve(channel, identifier, create_if_missing, name)


def link_identities(
    channel1: str,
    identifier1: str,
    channel2: str,
    identifier2: str,
) -> Optional[str]:
    """Convenience function to link identities."""
    return get_identity_service().link(channel1, identifier1, channel2, identifier2)


# =============================================================================
# CLI for OpenClaw skill
# =============================================================================

if __name__ == "__main__":
    import argparse
    import json
    
    parser = argparse.ArgumentParser(description="Unified Identity Skill")
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # Link command
    link_parser = subparsers.add_parser("link", help="Link identities across channels")
    link_parser.add_argument("--channel1", required=True, help="First channel (e.g., telegram)")
    link_parser.add_argument("--id1", required=True, help="First identifier")
    link_parser.add_argument("--channel2", required=True, help="Second channel (e.g., email)")
    link_parser.add_argument("--id2", required=True, help="Second identifier")
    
    # Resolve command
    resolve_parser = subparsers.add_parser("resolve", help="Resolve an identity")
    resolve_parser.add_argument("--channel", required=True, help="Channel to resolve")
    resolve_parser.add_argument("--identifier", required=True, help="Identifier to resolve")
    
    # Lookup command
    lookup_parser = subparsers.add_parser("lookup", help="Lookup contact info")
    lookup_parser.add_argument("--contact-id", required=True, help="Contact ID to lookup")
    
    args = parser.parse_args()
    service = get_identity_service()
    
    if args.command == "link":
        result = service.link(args.channel1, args.id1, args.channel2, args.id2)
        if result:
            print(json.dumps({"success": True, "contact_id": result}, indent=2))
        else:
            print(json.dumps({"success": False, "error": "Failed to link identities"}, indent=2))
    
    elif args.command == "resolve":
        contact_id = service.resolve(args.channel, args.identifier, create_if_missing=True)
        if contact_id:
            print(json.dumps({"contact_id": contact_id}, indent=2))
        else:
            print(json.dumps({"error": "Could not resolve identity"}, indent=2))
    
    elif args.command == "lookup":
        contact = service.get_contact(args.contact_id)
        if contact:
            print(json.dumps(contact.to_dict(), indent=2))
        else:
            print(json.dumps({"error": "Contact not found"}, indent=2))
