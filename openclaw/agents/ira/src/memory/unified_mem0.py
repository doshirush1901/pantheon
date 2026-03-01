#!/usr/bin/env python3
"""
UNIFIED MEM0 MEMORY SYSTEM - Single Source of Truth

╔════════════════════════════════════════════════════════════════════════════╗
║  This replaces PostgreSQL as the primary memory store.                     ║
║  All memory operations go through Mem0 with relationship tracking.         ║
║                                                                            ║
║  Features:                                                                 ║
║  1. Graph-like relationships via metadata linking                          ║
║  2. Unified identity resolution (single canonical ID per person)           ║
║  3. User memories + Entity memories + Relationships                        ║
║  4. Automatic consolidation and deduplication                              ║
╚════════════════════════════════════════════════════════════════════════════╝
"""

import os
import json
import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Set
from collections import defaultdict

# Load environment
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent.parent
env_file = PROJECT_ROOT / ".env"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        if line.strip() and not line.startswith('#') and '=' in line:
            key, _, value = line.partition('=')
            os.environ.setdefault(key.strip(), value.strip().strip('"'))


# =============================================================================
# UNIFIED IDENTITY
# =============================================================================

@dataclass
class UnifiedIdentity:
    """Single canonical identity for a person across all channels."""
    canonical_id: str  # The primary ID used everywhere
    name: Optional[str] = None
    email: Optional[str] = None
    telegram_id: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    aliases: List[str] = field(default_factory=list)  # Other IDs that map to this
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "canonical_id": self.canonical_id,
            "name": self.name,
            "email": self.email,
            "telegram_id": self.telegram_id,
            "phone": self.phone,
            "company": self.company,
            "aliases": self.aliases,
            "metadata": self.metadata,
        }


class IdentityResolver:
    """
    Resolves any identifier to a canonical ID.
    
    Maps: email, telegram_id, phone, name -> canonical_id
    """
    
    def __init__(self):
        self._identity_file = PROJECT_ROOT / "data" / "identities.json"
        self._identities: Dict[str, UnifiedIdentity] = {}
        self._alias_map: Dict[str, str] = {}  # alias -> canonical_id
        self._load()
    
    def _load(self):
        """Load identity mappings from file."""
        if self._identity_file.exists():
            try:
                data = json.loads(self._identity_file.read_text())
                for id_data in data.get("identities", []):
                    identity = UnifiedIdentity(**id_data)
                    self._identities[identity.canonical_id] = identity
                    # Build alias map
                    for alias in identity.aliases:
                        self._alias_map[alias.lower()] = identity.canonical_id
                    if identity.email:
                        self._alias_map[identity.email.lower()] = identity.canonical_id
                    if identity.telegram_id:
                        self._alias_map[identity.telegram_id] = identity.canonical_id
            except Exception as e:
                print(f"[identity] Load error: {e}")
    
    def _save(self):
        """Save identity mappings to file."""
        self._identity_file.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "identities": [i.to_dict() for i in self._identities.values()],
            "updated_at": datetime.now().isoformat()
        }
        self._identity_file.write_text(json.dumps(data, indent=2))
    
    def resolve(self, identifier: str) -> str:
        """
        Resolve any identifier to canonical ID.
        Creates new identity if not found.
        """
        if not identifier:
            return "unknown"
        
        key = identifier.lower().strip()
        
        # Check alias map
        if key in self._alias_map:
            return self._alias_map[key]
        
        # Check if it's already a canonical ID
        if identifier in self._identities:
            return identifier
        
        # Create new identity
        canonical_id = self._generate_canonical_id(identifier)
        identity = UnifiedIdentity(
            canonical_id=canonical_id,
            aliases=[identifier]
        )
        
        # Try to determine identity type
        if "@" in identifier:
            identity.email = identifier
        elif identifier.isdigit() and len(identifier) > 8:
            identity.telegram_id = identifier
        
        self._identities[canonical_id] = identity
        self._alias_map[key] = canonical_id
        self._save()
        
        return canonical_id
    
    def _generate_canonical_id(self, identifier: str) -> str:
        """Generate a stable canonical ID."""
        hash_input = identifier.lower().strip()
        return f"id_{hashlib.sha256(hash_input.encode()).hexdigest()[:12]}"
    
    def link(self, identifier1: str, identifier2: str) -> str:
        """Link two identifiers to the same canonical identity."""
        id1 = self.resolve(identifier1)
        id2 = self.resolve(identifier2)
        
        if id1 == id2:
            return id1
        
        # Merge into id1 (keep the older one)
        identity1 = self._identities[id1]
        identity2 = self._identities.get(id2)
        
        if identity2:
            # Merge aliases
            identity1.aliases.extend(identity2.aliases)
            identity1.aliases.append(id2)
            identity1.aliases = list(set(identity1.aliases))
            
            # Merge fields (prefer non-null)
            if not identity1.email and identity2.email:
                identity1.email = identity2.email
            if not identity1.telegram_id and identity2.telegram_id:
                identity1.telegram_id = identity2.telegram_id
            if not identity1.name and identity2.name:
                identity1.name = identity2.name
            
            # Update alias map
            for alias in identity2.aliases:
                self._alias_map[alias.lower()] = id1
            self._alias_map[id2] = id1
            
            # Remove merged identity
            del self._identities[id2]
        
        self._alias_map[identifier2.lower()] = id1
        self._save()
        
        return id1
    
    def update(self, identifier: str, **kwargs) -> UnifiedIdentity:
        """Update identity fields."""
        canonical_id = self.resolve(identifier)
        identity = self._identities[canonical_id]
        
        for key, value in kwargs.items():
            if hasattr(identity, key) and value:
                setattr(identity, key, value)
        
        self._save()
        return identity
    
    def get(self, identifier: str) -> Optional[UnifiedIdentity]:
        """Get full identity info."""
        canonical_id = self.resolve(identifier)
        return self._identities.get(canonical_id)


# =============================================================================
# RELATIONSHIP GRAPH (via Mem0 metadata)
# =============================================================================

@dataclass
class Relationship:
    """A relationship between two entities."""
    source: str
    relation: str  # works_at, knows, interested_in, etc.
    target: str
    confidence: float = 1.0
    source_memory_id: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "source": self.source,
            "relation": self.relation,
            "target": self.target,
            "confidence": self.confidence,
        }


class RelationshipExtractor:
    """Extract relationships from memory text."""
    
    PATTERNS = [
        # Person -> Company
        (r"(\w+)\s+works?\s+at\s+(\w+)", "works_at"),
        (r"(\w+)\s+is\s+from\s+(\w+)", "works_at"),
        (r"(\w+)\s+at\s+(\w+)\s+Corp", "works_at"),
        # Person -> Product interest
        (r"(\w+)\s+(?:interested|asking)\s+(?:in|about)\s+(\w+)", "interested_in"),
        (r"(\w+)\s+wants?\s+to\s+buy\s+(\w+)", "interested_in"),
        # Company -> Product
        (r"(\w+)\s+(?:makes?|produces?|manufactures?)\s+(\w+)", "makes"),
        (r"(\w+)\s+(?:uses?|bought|ordered)\s+(\w+)", "uses"),
    ]
    
    def extract(self, text: str) -> List[Relationship]:
        """Extract relationships from text."""
        import re
        relationships = []
        
        for pattern, relation_type in self.PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                source = match.group(1)
                target = match.group(2)
                relationships.append(Relationship(
                    source=source,
                    relation=relation_type,
                    target=target,
                    confidence=0.8
                ))
        
        return relationships


# =============================================================================
# UNIFIED MEM0 SERVICE
# =============================================================================

class UnifiedMem0Service:
    """
    Single memory service that handles everything:
    - User memories (conversations)
    - Entity memories (facts about companies/products)
    - Relationships (graph-like connections)
    - Identity resolution
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("MEM0_API_KEY")
        
        if not self.api_key:
            raise ValueError("MEM0_API_KEY not found")
        
        from mem0 import MemoryClient
        self.client = MemoryClient(api_key=self.api_key)
        
        self.identity = IdentityResolver()
        self.relationship_extractor = RelationshipExtractor()
        self._relationships: Dict[str, List[Relationship]] = defaultdict(list)
    
    # =========================================================================
    # CORE MEMORY OPERATIONS
    # =========================================================================
    
    def remember(
        self,
        user_message: str,
        assistant_response: str,
        user_id: str,
        channel: str = "telegram",
        extract_relationships: bool = True,
    ) -> Dict[str, Any]:
        """
        Store a conversation exchange.
        
        - Resolves user_id to canonical ID
        - Extracts and stores relationships
        - Returns memory stats
        """
        # Resolve to canonical ID
        canonical_id = self.identity.resolve(user_id)
        
        # Store conversation
        messages = [
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": assistant_response},
        ]
        
        result = self.client.add(
            messages=messages,
            user_id=canonical_id,
            metadata={
                "channel": channel,
                "original_id": user_id,
                "timestamp": datetime.now().isoformat(),
            }
        )
        
        # Extract relationships
        if extract_relationships:
            combined = f"{user_message} {assistant_response}"
            relationships = self.relationship_extractor.extract(combined)
            for rel in relationships:
                self._store_relationship(canonical_id, rel)
        
        return {
            "canonical_id": canonical_id,
            "memories_added": len(result.get("results", [])),
            "relationships_found": len(relationships) if extract_relationships else 0,
        }
    
    def search(
        self,
        query: str,
        user_id: str,
        limit: int = 10,
        include_relationships: bool = True,
    ) -> Dict[str, Any]:
        """
        Search memories with relationship expansion.
        """
        canonical_id = self.identity.resolve(user_id)
        
        # Search user memories
        try:
            results = self.client.search(
                query=query,
                version="v2",
                filters={"user_id": canonical_id},
                top_k=limit,
            )
            memories = results.get("results", results.get("memories", []))
        except Exception as e:
            print(f"[mem0] Search error: {e}")
            memories = []
        
        # Get related entities via relationships
        related = []
        if include_relationships:
            related = self._get_related_memories(query, canonical_id, limit=3)
        
        return {
            "memories": memories,
            "related": related,
            "canonical_id": canonical_id,
        }
    
    def search_entities(
        self,
        query: str,
        limit: int = 10,
    ) -> List[Dict]:
        """Search entity memories (products, companies)."""
        try:
            results = self.client.search(
                query=query,
                version="v2",
                filters={"agent_id": "*"},  # All entities
                top_k=limit,
            )
            return results.get("results", results.get("memories", []))
        except Exception as e:
            print(f"[mem0] Entity search error: {e}")
            return []
    
    def get_all(self, user_id: str) -> List[Dict]:
        """Get all memories for a user."""
        canonical_id = self.identity.resolve(user_id)
        
        try:
            results = self.client.get_all(
                version="v2",
                filters={"user_id": canonical_id}
            )
            return results.get("results", results.get("memories", []))
        except Exception as e:
            print(f"[mem0] Get all error: {e}")
            return []
    
    # =========================================================================
    # RELATIONSHIP OPERATIONS
    # =========================================================================
    
    def _store_relationship(self, user_id: str, relationship: Relationship):
        """Store a relationship for later traversal."""
        key = f"{relationship.source}:{relationship.relation}"
        self._relationships[key].append(relationship)
        
        # Also store in Mem0 as entity memory for searchability
        fact = f"{relationship.source} {relationship.relation.replace('_', ' ')} {relationship.target}"
        
        try:
            self.client.add(
                messages=[{"role": "user", "content": fact}],
                agent_id=f"rel_{relationship.source.lower()}",
                metadata={
                    "type": "relationship",
                    "relation": relationship.relation,
                    "source": relationship.source,
                    "target": relationship.target,
                    "learned_from": user_id,
                }
            )
        except Exception as e:
            print(f"[mem0] Relationship store error: {e}")
    
    def _get_related_memories(
        self,
        query: str,
        user_id: str,
        limit: int = 3
    ) -> List[Dict]:
        """Get memories related via relationships."""
        related = []
        
        # Extract entities from query
        import re
        words = re.findall(r'\b[A-Z][a-z]+\b|\b[A-Z]+\b', query)
        
        for word in words[:3]:  # Check top 3 capitalized words
            key_prefix = f"{word}:"
            for key, rels in self._relationships.items():
                if key.startswith(key_prefix):
                    for rel in rels[:2]:
                        related.append({
                            "type": "relationship",
                            "fact": f"{rel.source} {rel.relation} {rel.target}",
                            "confidence": rel.confidence,
                        })
        
        return related[:limit]
    
    def get_relationships(self, entity: str) -> List[Relationship]:
        """Get all relationships for an entity."""
        results = []
        for key, rels in self._relationships.items():
            if key.startswith(f"{entity}:"):
                results.extend(rels)
            for rel in rels:
                if rel.target.lower() == entity.lower():
                    results.append(rel)
        return results
    
    # =========================================================================
    # IDENTITY OPERATIONS
    # =========================================================================
    
    def link_identity(self, id1: str, id2: str) -> str:
        """Link two identifiers to the same person."""
        return self.identity.link(id1, id2)
    
    def get_identity(self, identifier: str) -> Optional[UnifiedIdentity]:
        """Get full identity information."""
        return self.identity.get(identifier)
    
    def update_identity(self, identifier: str, **kwargs) -> UnifiedIdentity:
        """Update identity fields (name, email, etc.)"""
        return self.identity.update(identifier, **kwargs)
    
    # =========================================================================
    # CONVENIENCE METHODS
    # =========================================================================
    
    def get_context_for_prompt(
        self,
        query: str,
        user_id: str,
        limit: int = 5,
    ) -> str:
        """Get formatted context for LLM prompt."""
        result = self.search(query, user_id, limit=limit)
        
        lines = []
        
        if result["memories"]:
            lines.append("## What I Remember:")
            for m in result["memories"][:limit]:
                lines.append(f"- {m.get('memory', '')}")
        
        if result["related"]:
            lines.append("\n## Related Information:")
            for r in result["related"]:
                lines.append(f"- {r.get('fact', '')}")
        
        return "\n".join(lines) if lines else ""
    
    def get_stats(self) -> Dict[str, Any]:
        """Get memory statistics."""
        return {
            "identities": len(self.identity._identities),
            "relationships": sum(len(r) for r in self._relationships.values()),
            "status": "connected",
        }


# =============================================================================
# SINGLETON
# =============================================================================

_unified_service: Optional[UnifiedMem0Service] = None


def get_unified_mem0() -> UnifiedMem0Service:
    """Get or create the unified memory service."""
    global _unified_service
    if _unified_service is None:
        _unified_service = UnifiedMem0Service()
    return _unified_service


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    import sys
    
    service = get_unified_mem0()
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python unified_mem0.py search <user_id> <query>")
        print("  python unified_mem0.py identity <identifier>")
        print("  python unified_mem0.py link <id1> <id2>")
        print("  python unified_mem0.py stats")
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == "stats":
        print(service.get_stats())
    
    elif cmd == "identity" and len(sys.argv) >= 3:
        identity = service.get_identity(sys.argv[2])
        if identity:
            print(json.dumps(identity.to_dict(), indent=2))
        else:
            print("Not found")
    
    elif cmd == "link" and len(sys.argv) >= 4:
        canonical = service.link_identity(sys.argv[2], sys.argv[3])
        print(f"Linked to: {canonical}")
    
    elif cmd == "search" and len(sys.argv) >= 4:
        result = service.search(sys.argv[3], sys.argv[2])
        print(json.dumps(result, indent=2, default=str))
