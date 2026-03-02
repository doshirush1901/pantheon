#!/usr/bin/env python3
"""
KNOWLEDGE BLASTER - Ki Blast Knowledge to Agents
=================================================

Like a Ki Blast from Dragon Ball Z, this module blasts relevant knowledge
from the unified brain to each agent before they make decisions.

Each agent has different knowledge needs:
- Athena (Chief of Staff): Customer context, workflow patterns, priorities
- Clio (Researcher): All knowledge access, deep retrieval capabilities
- Calliope (Writer): Communication style, branding, past emails, templates
- Vera (Fact-Checker): Machine specs, pricing facts, verified data
- Sophia (Reflector): Interaction patterns, lessons learned, corrections

The Knowledge Blaster:
1. Analyzes the incoming task/query
2. Extracts relevant entities (machines, customers, topics)
3. Queries Neo4j for relationship-aware context
4. Queries Qdrant for semantic matches
5. Creates an agent-specific "Brain Pack" with relevant knowledge

Usage:
    from knowledge_blaster import KnowledgeBlaster, blast_knowledge_to_agent
    
    blaster = KnowledgeBlaster()
    
    # Blast knowledge to an agent
    brain_pack = blaster.blast(
        agent_type="researcher",
        query="What PF1 machine for automotive ABS parts?",
        context={"customer": "Toyota", "channel": "email"}
    )
    
    # Use in agent execution
    agent.execute(task, brain_pack=brain_pack)
"""

import logging
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from enum import Enum
import re

logger = logging.getLogger("ira.knowledge_blaster")

BRAIN_DIR = Path(__file__).parent
AGENT_DIR = BRAIN_DIR.parent.parent
PROJECT_ROOT = AGENT_DIR.parent.parent.parent

sys.path.insert(0, str(AGENT_DIR))

# Import knowledge sources
try:
    from src.brain.neo4j_store import get_neo4j_store, Neo4jStore
    NEO4J_AVAILABLE = True
except ImportError:
    NEO4J_AVAILABLE = False
    logger.warning("Neo4j not available for Knowledge Blaster")

try:
    from src.brain.unified_retriever import UnifiedRetriever
    RETRIEVER_AVAILABLE = True
except ImportError:
    RETRIEVER_AVAILABLE = False
    logger.warning("UnifiedRetriever not available")


class AgentType(Enum):
    """Types of agents that can receive knowledge blasts."""
    CHIEF_OF_STAFF = "chief_of_staff"  # Athena
    RESEARCHER = "researcher"           # Clio
    WRITER = "writer"                   # Calliope
    FACT_CHECKER = "fact_checker"       # Vera
    REFLECTOR = "reflector"             # Sophia


@dataclass
class KnowledgeItem:
    """A single piece of knowledge in a brain pack."""
    text: str
    source: str
    knowledge_type: str
    relevance_score: float
    entity: str = ""
    relationships: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BrainPack:
    """
    A package of relevant knowledge "blasted" to an agent.
    
    Contains everything an agent needs to make informed decisions.
    """
    agent_type: AgentType
    query: str
    timestamp: datetime
    
    # Core knowledge
    facts: List[KnowledgeItem] = field(default_factory=list)
    context: List[KnowledgeItem] = field(default_factory=list)
    
    # Entity-specific knowledge
    entities_found: List[str] = field(default_factory=list)
    entity_relationships: Dict[str, List[str]] = field(default_factory=dict)
    
    # Agent-specific extras
    communication_style: str = ""  # For Writer
    verification_data: List[Dict] = field(default_factory=list)  # For Fact-Checker
    lessons_learned: List[str] = field(default_factory=list)  # For Reflector
    workflow_context: str = ""  # For Chief of Staff
    
    # Metadata
    sources_queried: List[str] = field(default_factory=list)
    blast_duration_ms: float = 0.0
    
    def to_context_string(self, max_items: int = 10) -> str:
        """Convert brain pack to a context string for LLM prompts."""
        parts = []
        
        if self.facts:
            parts.append("## Relevant Facts")
            for item in self.facts[:max_items]:
                parts.append(f"- {item.text[:500]}")
        
        if self.context:
            parts.append("\n## Additional Context")
            for item in self.context[:max_items // 2]:
                parts.append(f"- {item.text[:300]}")
        
        if self.entity_relationships:
            parts.append("\n## Entity Relationships")
            for entity, relations in list(self.entity_relationships.items())[:5]:
                parts.append(f"- {entity}: {', '.join(relations[:5])}")
        
        if self.communication_style:
            parts.append(f"\n## Communication Style\n{self.communication_style}")
        
        if self.lessons_learned:
            parts.append("\n## Lessons Learned")
            for lesson in self.lessons_learned[:5]:
                parts.append(f"- {lesson}")
        
        return "\n".join(parts)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "agent_type": self.agent_type.value,
            "query": self.query,
            "timestamp": self.timestamp.isoformat(),
            "facts_count": len(self.facts),
            "context_count": len(self.context),
            "entities_found": self.entities_found,
            "sources_queried": self.sources_queried,
            "blast_duration_ms": self.blast_duration_ms,
        }


# Knowledge type mappings for each agent
AGENT_KNOWLEDGE_FOCUS = {
    AgentType.CHIEF_OF_STAFF: {
        "types": ["commercial", "lead", "client", "case_study", "workflow"],
        "depth": 2,
        "max_items": 15,
        "include_workflow": True,
        "include_lessons": True,
    },
    AgentType.RESEARCHER: {
        "types": ["machine_spec", "operational", "commercial", "application", "market_intelligence"],
        "depth": 3,
        "max_items": 25,
        "include_all": True,
    },
    AgentType.WRITER: {
        "types": ["commercial", "application", "case_study", "communication_style"],
        "depth": 1,
        "max_items": 10,
        "include_style": True,
        "include_templates": True,
    },
    AgentType.FACT_CHECKER: {
        "types": ["machine_spec", "operational", "pricing"],
        "depth": 1,
        "max_items": 20,
        "include_verification": True,
        "strict_facts_only": True,
    },
    AgentType.REFLECTOR: {
        "types": ["lesson", "correction", "feedback", "interaction_pattern"],
        "depth": 2,
        "max_items": 15,
        "include_lessons": True,
        "include_errors": True,
    },
}


class KnowledgeBlaster:
    """
    Blasts relevant knowledge to agents before they execute tasks.
    
    Like Goku's Ki Blast, but for knowledge transfer.
    """
    
    def __init__(self):
        self._neo4j: Optional[Neo4jStore] = None
        self._retriever: Optional[UnifiedRetriever] = None
        self._lessons_cache: Dict[str, List[str]] = {}
        self._style_cache: str = ""
    
    def _get_neo4j(self) -> Optional[Neo4jStore]:
        """Get Neo4j store connection."""
        if self._neo4j is None and NEO4J_AVAILABLE:
            try:
                self._neo4j = get_neo4j_store()
                if not self._neo4j.is_connected():
                    self._neo4j = None
            except Exception as e:
                logger.warning(f"Neo4j not available: {e}")
        return self._neo4j
    
    def _get_retriever(self) -> Optional[UnifiedRetriever]:
        """Get unified retriever."""
        if self._retriever is None and RETRIEVER_AVAILABLE:
            try:
                self._retriever = UnifiedRetriever()
            except Exception as e:
                logger.warning(f"Retriever not available: {e}")
        return self._retriever
    
    def _extract_entities(self, text: str) -> Set[str]:
        """Extract entities (machines, materials, companies) from text."""
        entities = set()
        
        # Machine patterns
        patterns = [
            r'\bPF1[-\s]?[A-Z]?[-\s]?\d{3,4}\b',
            r'\bPF2[-\s]?\d*\b',
            r'\bAM[-\s]?[A-Z]?[-\s]?\d{4}\b',
            r'\bFCS[-\s]?\d{4}\b',
            r'\bIMG[-\s]?\d+\b',
            r'\bATF[-\s]?\d+\b',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for m in matches:
                entities.add(m.upper().replace(" ", "-"))
        
        # Series names
        series = ["PF1", "PF2", "AM", "FCS", "IMG", "ATF", "UNO", "DUO"]
        for s in series:
            if s.lower() in text.lower():
                entities.add(s)
        
        # Materials
        materials = ["ABS", "HDPE", "PP", "PET", "PVC", "PC", "PMMA", "TPO", "HIPS"]
        for m in materials:
            if m.lower() in text.lower():
                entities.add(m)
        
        # Applications
        applications = ["automotive", "packaging", "medical", "food", "industrial", "signage"]
        for app in applications:
            if app in text.lower():
                entities.add(app.title())
        
        return entities
    
    def _query_neo4j_for_entities(
        self,
        entities: Set[str],
        depth: int = 2,
        max_related: int = 10
    ) -> tuple[List[KnowledgeItem], Dict[str, List[str]]]:
        """Query Neo4j for knowledge about entities and their relationships."""
        items = []
        relationships = {}
        
        neo4j = self._get_neo4j()
        if not neo4j:
            return items, relationships
        
        for entity in list(entities)[:10]:  # Limit entities
            try:
                # Get related entities
                related = neo4j.get_related_entities(entity, depth=depth, limit=max_related)
                if related:
                    relationships[entity] = [
                        f"{r['entity']} ({', '.join(r.get('relationship_types', [])[:2])})"
                        for r in related[:5]
                    ]
                
                # Get knowledge about this entity
                knowledge = neo4j.get_entity_knowledge(entity)
                for k in knowledge[:3]:
                    items.append(KnowledgeItem(
                        text=k.get("text", "")[:1000],
                        source="neo4j",
                        knowledge_type=k.get("knowledge_type", "general"),
                        relevance_score=0.9,
                        entity=entity,
                        relationships=[r["entity"] for r in related[:3]] if related else [],
                        metadata={"source_file": k.get("source_file", "")},
                    ))
                
            except Exception as e:
                logger.debug(f"Neo4j query failed for {entity}: {e}")
        
        return items, relationships
    
    def _query_vector_for_context(
        self,
        query: str,
        knowledge_types: List[str],
        max_items: int = 10
    ) -> List[KnowledgeItem]:
        """Query vector store for semantic matches."""
        items = []
        
        retriever = self._get_retriever()
        if not retriever:
            return items
        
        try:
            results = retriever.search(
                query=query,
                top_k=max_items,
                include_emails=False,
            )
            
            for r in results:
                items.append(KnowledgeItem(
                    text=r.text[:1000],
                    source="qdrant",
                    knowledge_type=r.doc_type or "document",
                    relevance_score=r.score,
                    entity=", ".join(r.machines) if r.machines else "",
                    metadata={
                        "filename": r.filename,
                        "chunk_id": r.chunk_id,
                    },
                ))
        except Exception as e:
            logger.debug(f"Vector search failed: {e}")
        
        return items
    
    def _load_communication_style(self) -> str:
        """Load Rushabh's communication style for the Writer agent."""
        if self._style_cache:
            return self._style_cache
        
        style_file = PROJECT_ROOT / "data" / "knowledge" / "communication_style.json"
        if style_file.exists():
            import json
            try:
                data = json.loads(style_file.read_text())
                self._style_cache = data.get("style_guide", "")
                return self._style_cache
            except:
                pass
        
        # Default style guidance
        self._style_cache = """
        Communication Style:
        - Professional yet warm tone
        - Technical accuracy with accessibility
        - Focus on customer benefits
        - Clear, concise sentences
        - End emails with clear next steps
        """
        return self._style_cache
    
    def _load_lessons_for_agent(self, agent_type: AgentType) -> List[str]:
        """Load lessons learned relevant to an agent."""
        cache_key = agent_type.value
        if cache_key in self._lessons_cache:
            return self._lessons_cache[cache_key]
        
        lessons = []
        lessons_file = PROJECT_ROOT / "openclaw" / "agents" / "ira" / "src" / "agents" / agent_type.value / "lessons.md"
        
        if lessons_file.exists():
            try:
                content = lessons_file.read_text()
                # Extract lessons (lines starting with -)
                for line in content.split("\n"):
                    if line.strip().startswith("-"):
                        lessons.append(line.strip()[1:].strip())
            except:
                pass
        
        self._lessons_cache[cache_key] = lessons[:20]
        return lessons[:20]
    
    def blast(
        self,
        agent_type: AgentType,
        query: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> BrainPack:
        """
        BLAST knowledge to an agent!
        
        Like a Ki Blast, sends relevant knowledge from the unified brain
        to the agent before they make decisions.
        
        Args:
            agent_type: Type of agent to blast knowledge to
            query: The query/task the agent will handle
            context: Additional context (customer, channel, etc.)
        
        Returns:
            BrainPack containing all relevant knowledge for the agent
        """
        import time
        start_time = time.time()
        
        logger.info(f"⚡ Ki Blast to {agent_type.value}: {query[:50]}...")
        
        # Get agent-specific config
        config = AGENT_KNOWLEDGE_FOCUS.get(agent_type, AGENT_KNOWLEDGE_FOCUS[AgentType.RESEARCHER])
        
        # Create brain pack
        pack = BrainPack(
            agent_type=agent_type,
            query=query,
            timestamp=datetime.now(),
        )
        
        # Extract entities from query
        entities = self._extract_entities(query)
        if context:
            # Also extract from context
            context_text = " ".join(str(v) for v in context.values())
            entities.update(self._extract_entities(context_text))
        
        pack.entities_found = list(entities)
        
        # Query Neo4j for entity knowledge and relationships
        neo4j_items, relationships = self._query_neo4j_for_entities(
            entities,
            depth=config.get("depth", 2),
            max_related=config.get("max_items", 15),
        )
        pack.facts.extend(neo4j_items)
        pack.entity_relationships = relationships
        
        if neo4j_items:
            pack.sources_queried.append("neo4j")
        
        # Query vector store for semantic context
        vector_items = self._query_vector_for_context(
            query,
            knowledge_types=config.get("types", []),
            max_items=config.get("max_items", 10),
        )
        pack.context.extend(vector_items)
        
        if vector_items:
            pack.sources_queried.append("qdrant")
        
        # Agent-specific additions
        if agent_type == AgentType.WRITER and config.get("include_style"):
            pack.communication_style = self._load_communication_style()
        
        if config.get("include_lessons"):
            pack.lessons_learned = self._load_lessons_for_agent(agent_type)
        
        if agent_type == AgentType.FACT_CHECKER:
            # Add verification-focused data
            pack.verification_data = [
                {"entity": item.entity, "fact": item.text[:200], "source": item.metadata.get("source_file", "")}
                for item in pack.facts[:10]
            ]
        
        if agent_type == AgentType.CHIEF_OF_STAFF and context:
            # Add workflow context
            pack.workflow_context = f"Channel: {context.get('channel', 'unknown')}, Customer: {context.get('customer', 'unknown')}"
        
        # Calculate blast duration
        pack.blast_duration_ms = (time.time() - start_time) * 1000
        
        logger.info(
            f"⚡ Ki Blast complete: {len(pack.facts)} facts, {len(pack.context)} context items, "
            f"{len(pack.entity_relationships)} relationships in {pack.blast_duration_ms:.0f}ms"
        )
        
        return pack


# Singleton instance
_blaster: Optional[KnowledgeBlaster] = None


def get_knowledge_blaster() -> KnowledgeBlaster:
    """Get the singleton Knowledge Blaster instance."""
    global _blaster
    if _blaster is None:
        _blaster = KnowledgeBlaster()
    return _blaster


def blast_knowledge_to_agent(
    agent_type: str,
    query: str,
    context: Optional[Dict[str, Any]] = None,
) -> BrainPack:
    """
    Convenience function to blast knowledge to an agent.
    
    Args:
        agent_type: String name of agent ("researcher", "writer", etc.)
        query: The query/task
        context: Optional additional context
    
    Returns:
        BrainPack with relevant knowledge
    """
    blaster = get_knowledge_blaster()
    
    # Convert string to AgentType
    try:
        agent_enum = AgentType(agent_type.lower())
    except ValueError:
        agent_enum = AgentType.RESEARCHER
    
    return blaster.blast(agent_enum, query, context)


# =============================================================================
# CLI for testing
# =============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Knowledge Blaster CLI")
    parser.add_argument("query", type=str, help="Query to blast knowledge for")
    parser.add_argument("--agent", type=str, default="researcher", 
                       help="Agent type (chief_of_staff, researcher, writer, fact_checker, reflector)")
    parser.add_argument("--verbose", action="store_true", help="Show full brain pack")
    
    args = parser.parse_args()
    
    print(f"\n⚡ Ki Blast to {args.agent}...")
    print(f"Query: {args.query}\n")
    
    pack = blast_knowledge_to_agent(args.agent, args.query)
    
    print(f"=== Brain Pack Summary ===")
    print(f"Facts: {len(pack.facts)}")
    print(f"Context items: {len(pack.context)}")
    print(f"Entities found: {pack.entities_found}")
    print(f"Relationships: {len(pack.entity_relationships)}")
    print(f"Sources: {pack.sources_queried}")
    print(f"Duration: {pack.blast_duration_ms:.0f}ms")
    
    if args.verbose:
        print(f"\n=== Context String ===")
        print(pack.to_context_string())
