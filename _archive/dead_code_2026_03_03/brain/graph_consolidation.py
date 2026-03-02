#!/usr/bin/env python3
"""
KNOWLEDGE GRAPH CONSOLIDATION (Sleep Learning)
==============================================

During Ira's "sleep" cycle, this module:

1. INTERACTION ANALYSIS
   - Reviews today's queries and retrieved results
   - Tracks which knowledge was accessed and how useful
   - Identifies knowledge gaps from failed queries

2. RELATIONSHIP TUNING
   - Strengthens edges between co-accessed knowledge
   - Weakens edges that weren't useful together
   - Creates new edges for knowledge that should connect

3. CLUSTER REORGANIZATION
   - Moves nodes between clusters based on usage patterns
   - Merges similar clusters that should be together
   - Splits clusters that have grown too broad

4. NODE UPDATES
   - Updates stale nodes with new information
   - Removes outdated/contradicted knowledge
   - Enriches nodes with learned context

Usage:
    from graph_consolidation import GraphConsolidator
    
    consolidator = GraphConsolidator()
    result = consolidator.consolidate()  # Run nightly
    
    # Or specific operations:
    consolidator.analyze_interactions()
    consolidator.tune_relationships()
    consolidator.reorganize_clusters()
"""

import logging
import os
import sys
import json
import hashlib

logger = logging.getLogger(__name__)
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple
from collections import defaultdict
import math

BRAIN_DIR = Path(__file__).parent
SKILLS_DIR = BRAIN_DIR.parent
AGENT_DIR = SKILLS_DIR.parent
PROJECT_ROOT = AGENT_DIR.parent.parent.parent

sys.path.insert(0, str(AGENT_DIR))
sys.path.insert(0, str(BRAIN_DIR))

# Import from centralized config
try:
    from config import VOYAGE_API_KEY, QDRANT_URL, QDRANT_API_KEY, get_logger
    CONFIG_AVAILABLE = True
except ImportError:
    CONFIG_AVAILABLE = False
    # Fallback: Load environment manually
    env_file = PROJECT_ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if line.strip() and not line.startswith('#') and '=' in line:
                key, _, value = line.partition('=')
                os.environ.setdefault(key.strip(), value.strip().strip('"'))
    VOYAGE_API_KEY = os.environ.get("VOYAGE_API_KEY")
    QDRANT_URL = os.environ.get("QDRANT_URL", "http://localhost:6333")
    QDRANT_API_KEY = os.environ.get("QDRANT_API_KEY", "")

KNOWLEDGE_DIR = PROJECT_ROOT / "data" / "knowledge"
GRAPH_FILE = KNOWLEDGE_DIR / "knowledge_graph.json"
RETRIEVAL_LOG = KNOWLEDGE_DIR / "retrieval_log.jsonl"
INTERACTIONS_LOG = PROJECT_ROOT / "crm" / "logs" / "requests.jsonl"
CONSOLIDATION_LOG = KNOWLEDGE_DIR / "consolidation_log.json"

# Neo4j integration
try:
    from src.brain.neo4j_store import Neo4jStore, get_neo4j_store
    NEO4J_AVAILABLE = True
except ImportError:
    NEO4J_AVAILABLE = False
    logger.warning("Neo4j store not available for consolidation")

# Power Level tracking (Saiyan Saga)
try:
    from src.brain.power_levels import get_power_tracker
    POWER_LEVELS_AVAILABLE = True
except ImportError:
    POWER_LEVELS_AVAILABLE = False

DECAY_FACTOR = 0.95
REINFORCEMENT_BOOST = 0.15
CO_ACCESS_THRESHOLD = 3
SIMILARITY_MERGE_THRESHOLD = 0.85
STALE_DAYS = 30


@dataclass
class InteractionRecord:
    """A single interaction (query + retrieved knowledge)."""
    timestamp: datetime
    query: str
    retrieved_ids: List[str]
    was_helpful: Optional[bool] = None
    feedback_score: float = 0.0


@dataclass
class ConsolidationResult:
    """Results of a consolidation run."""
    timestamp: datetime
    interactions_analyzed: int
    edges_strengthened: int
    edges_weakened: int
    edges_created: int
    nodes_updated: int
    clusters_reorganized: int
    knowledge_gaps: List[str]


class GraphConsolidator:
    """
    Consolidates knowledge graph based on daily interactions.
    
    Like human sleep, this process:
    - Reviews the day's experiences (queries)
    - Strengthens useful connections (LTP)
    - Prunes unused connections (synaptic pruning)
    - Reorganizes memories (memory consolidation)
    """
    
    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self._qdrant = None
        self._voyage = None
        self._graph = None
        self._neo4j = None
        
        KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)
    
    def _get_neo4j(self):
        """Get Neo4j store for graph operations."""
        if self._neo4j is None and NEO4J_AVAILABLE:
            try:
                self._neo4j = get_neo4j_store()
                if not self._neo4j.is_connected():
                    self._log("Neo4j not connected, using JSON fallback")
                    self._neo4j = None
            except Exception as e:
                self._log(f"Failed to connect to Neo4j: {e}")
        return self._neo4j
    
    def _log(self, msg: str):
        if self.verbose:
            logger.info("[Consolidator] %s", msg)
    
    def _get_qdrant(self):
        if self._qdrant is None:
            from qdrant_client import QdrantClient
            self._qdrant = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
        return self._qdrant
    
    def _get_voyage(self):
        if self._voyage is None and VOYAGE_API_KEY:
            import voyageai
            self._voyage = voyageai.Client(api_key=VOYAGE_API_KEY)
        return self._voyage
    
    def _get_graph(self):
        if self._graph is None:
            try:
                from knowledge_graph import KnowledgeGraph
                self._graph = KnowledgeGraph(verbose=False)
            except ImportError:
                self._log("Warning: KnowledgeGraph not available")
        return self._graph
    
    def _load_graph_data(self) -> Dict:
        """Load the raw graph JSON."""
        if GRAPH_FILE.exists():
            return json.loads(GRAPH_FILE.read_text())
        return {"nodes": [], "edges": [], "clusters": []}
    
    def _save_graph_data(self, data: Dict):
        """Save the graph JSON."""
        GRAPH_FILE.write_text(json.dumps(data, indent=2, default=str))
    
    # =========================================================================
    # PHASE 1: INTERACTION ANALYSIS
    # =========================================================================
    
    def analyze_interactions(self, days: int = 1) -> List[InteractionRecord]:
        """
        Analyze recent interactions to understand usage patterns.
        
        Reads from:
        - Retrieval log (queries + retrieved chunk IDs) - PRIMARY
        - Request logs (fallback)
        """
        interactions = []
        cutoff = datetime.now() - timedelta(days=days)
        
        if RETRIEVAL_LOG.exists():
            self._log(f"Reading from retrieval log...")
            try:
                with open(RETRIEVAL_LOG, 'r') as f:
                    for line in f:
                        if not line.strip():
                            continue
                        try:
                            record = json.loads(line)
                            
                            timestamp_str = record.get("timestamp", "")
                            if timestamp_str:
                                try:
                                    ts = datetime.fromisoformat(timestamp_str)
                                    if ts < cutoff:
                                        continue
                                except (ValueError, TypeError):
                                    pass  # Invalid timestamp format, process anyway
                            
                            query = record.get("query", "")
                            retrieved = record.get("retrieved_ids", [])
                            scores = record.get("scores", [])
                            
                            if query and retrieved:
                                avg_score = sum(scores) / len(scores) if scores else 0.5
                                interactions.append(InteractionRecord(
                                    timestamp=datetime.now(),
                                    query=query,
                                    retrieved_ids=[str(r) for r in retrieved if r],
                                    feedback_score=avg_score,
                                ))
                        except json.JSONDecodeError:
                            continue
            except Exception as e:
                self._log(f"Error reading retrieval log: {e}")
        
        if not interactions and INTERACTIONS_LOG.exists():
            self._log(f"Falling back to request log...")
            try:
                with open(INTERACTIONS_LOG, 'r') as f:
                    for line in f:
                        if not line.strip():
                            continue
                        try:
                            record = json.loads(line)
                            
                            timestamp_str = record.get("timestamp", "")
                            if timestamp_str:
                                try:
                                    ts = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                                    if ts.replace(tzinfo=None) < cutoff:
                                        continue
                                except (ValueError, TypeError):
                                    continue  # Skip records with invalid timestamps
                            
                            query = record.get("query", record.get("message_preview", ""))
                            retrieved = record.get("retrieved_ids", record.get("citations", []))
                            
                            if isinstance(retrieved, list) and len(retrieved) > 0:
                                if isinstance(retrieved[0], dict):
                                    retrieved = [r.get("chunk_id", r.get("id", "")) for r in retrieved]
                            
                            if query:
                                interactions.append(InteractionRecord(
                                    timestamp=datetime.now(),
                                    query=query,
                                    retrieved_ids=[str(r) for r in retrieved if r],
                                    feedback_score=record.get("feedback_score", 0.0),
                                ))
                        except json.JSONDecodeError:
                            continue
            except Exception as e:
                self._log(f"Error reading request log: {e}")
        
        self._log(f"Found {len(interactions)} interactions from last {days} day(s)")
        return interactions
    
    def _calculate_co_access_matrix(self, interactions: List[InteractionRecord]) -> Dict[Tuple[str, str], int]:
        """
        Calculate how often knowledge pairs are accessed together.
        
        If two pieces of knowledge are frequently retrieved for the same query,
        they should have a stronger relationship.
        """
        co_access = defaultdict(int)
        
        for interaction in interactions:
            ids = interaction.retrieved_ids
            for i, id1 in enumerate(ids):
                for id2 in ids[i+1:]:
                    key = tuple(sorted([id1, id2]))
                    co_access[key] += 1
        
        return dict(co_access)
    
    def _identify_knowledge_gaps(self, interactions: List[InteractionRecord]) -> List[str]:
        """
        Identify queries that retrieved poor results (potential knowledge gaps).
        """
        gaps = []
        
        for interaction in interactions:
            if len(interaction.retrieved_ids) == 0:
                gaps.append(f"No results for: {interaction.query[:100]}")
            elif interaction.feedback_score and interaction.feedback_score < 0.3:
                gaps.append(f"Low quality results for: {interaction.query[:100]}")
        
        return list(set(gaps))[:20]
    
    # =========================================================================
    # PHASE 2: RELATIONSHIP TUNING
    # =========================================================================
    
    def tune_relationships(self, co_access: Dict[Tuple[str, str], int]) -> Tuple[int, int, int]:
        """
        Adjust edge strengths based on usage patterns.
        
        - Strengthen edges between co-accessed knowledge
        - Weaken edges that weren't used together
        - Create new edges for strongly co-accessed pairs
        """
        graph_data = self._load_graph_data()
        edges = graph_data.get("edges", [])
        
        strengthened = 0
        weakened = 0
        created = 0
        
        existing_pairs = set()
        for edge in edges:
            pair = tuple(sorted([edge["source_id"], edge["target_id"]]))
            existing_pairs.add(pair)
        
        edge_index = {
            tuple(sorted([e["source_id"], e["target_id"]])): i 
            for i, e in enumerate(edges)
        }
        
        for pair, count in co_access.items():
            if count >= CO_ACCESS_THRESHOLD:
                if pair in edge_index:
                    idx = edge_index[pair]
                    old_strength = edges[idx].get("strength", 0.5)
                    new_strength = min(1.0, old_strength + REINFORCEMENT_BOOST * (count / CO_ACCESS_THRESHOLD))
                    edges[idx]["strength"] = new_strength
                    edges[idx]["last_reinforced"] = datetime.now().isoformat()
                    strengthened += 1
                else:
                    edges.append({
                        "source_id": pair[0],
                        "target_id": pair[1],
                        "relationship_type": "co_accessed",
                        "strength": 0.5 + REINFORCEMENT_BOOST * (count / CO_ACCESS_THRESHOLD),
                        "created_at": datetime.now().isoformat(),
                        "metadata": {"co_access_count": count}
                    })
                    created += 1
        
        for edge in edges:
            pair = tuple(sorted([edge["source_id"], edge["target_id"]]))
            if pair not in co_access:
                old_strength = edge.get("strength", 0.5)
                new_strength = max(0.1, old_strength * DECAY_FACTOR)
                if new_strength < old_strength:
                    edge["strength"] = new_strength
                    weakened += 1
        
        graph_data["edges"] = edges
        self._save_graph_data(graph_data)
        
        # Sync to Neo4j if available
        neo4j = self._get_neo4j()
        if neo4j:
            self._log("Syncing relationship changes to Neo4j...")
            try:
                # Apply decay to unused relationships in Neo4j
                neo4j.decay_unused_relationships(days_threshold=1, decay_factor=DECAY_FACTOR)
                
                # Create/strengthen relationships that were co-accessed
                for pair, count in co_access.items():
                    if count >= CO_ACCESS_THRESHOLD:
                        boost = REINFORCEMENT_BOOST * (count / CO_ACCESS_THRESHOLD)
                        neo4j.strengthen_relationship(
                            pair[0], pair[1], "CO_ACCESSED", 
                            factor=1.0 + boost
                        )
                
                self._log("Neo4j sync complete")
            except Exception as e:
                self._log(f"Failed to sync to Neo4j: {e}")
        
        self._log(f"Relationships: +{strengthened} strengthened, -{weakened} weakened, +{created} created")
        return strengthened, weakened, created
    
    # =========================================================================
    # PHASE 3: CLUSTER REORGANIZATION
    # =========================================================================
    
    def reorganize_clusters(self, co_access: Dict[Tuple[str, str], int]) -> int:
        """
        Reorganize clusters based on actual usage patterns.
        
        - Nodes that are frequently accessed together should be in the same cluster
        - Nodes that are never accessed together might be in wrong clusters
        """
        graph = self._get_graph()
        if not graph:
            return 0
        
        graph_data = self._load_graph_data()
        nodes = graph_data.get("nodes", [])
        clusters = graph_data.get("clusters", [])
        
        if not nodes:
            return 0
        
        node_to_cluster = {}
        for node in nodes:
            if node.get("cluster_id"):
                node_to_cluster[node["id"]] = node["cluster_id"]
        
        cross_cluster_pairs = []
        for pair, count in co_access.items():
            if count >= CO_ACCESS_THRESHOLD:
                c1 = node_to_cluster.get(pair[0])
                c2 = node_to_cluster.get(pair[1])
                if c1 and c2 and c1 != c2:
                    cross_cluster_pairs.append((pair, count, c1, c2))
        
        reorganized = 0
        
        cluster_merge_candidates = defaultdict(int)
        for pair, count, c1, c2 in cross_cluster_pairs:
            key = tuple(sorted([c1, c2]))
            cluster_merge_candidates[key] += count
        
        merged_clusters = set()
        for (c1, c2), count in sorted(cluster_merge_candidates.items(), key=lambda x: -x[1]):
            if count >= CO_ACCESS_THRESHOLD * 3:
                if c1 not in merged_clusters and c2 not in merged_clusters:
                    for node in nodes:
                        if node.get("cluster_id") == c2:
                            node["cluster_id"] = c1
                            reorganized += 1
                    merged_clusters.add(c2)
                    self._log(f"  Merged cluster {c2} into {c1} (co-access count: {count})")
        
        clusters = [c for c in clusters if c.get("id") not in merged_clusters]
        
        graph_data["nodes"] = nodes
        graph_data["clusters"] = clusters
        self._save_graph_data(graph_data)
        
        self._log(f"Clusters: {reorganized} nodes reorganized, {len(merged_clusters)} clusters merged")
        return reorganized
    
    # =========================================================================
    # PHASE 4: NODE UPDATES
    # =========================================================================
    
    def update_stale_nodes(self) -> int:
        """
        Update nodes that haven't been accessed in a while.
        
        - Flag stale nodes for review
        - Update access timestamps
        """
        graph_data = self._load_graph_data()
        nodes = graph_data.get("nodes", [])
        
        cutoff = datetime.now() - timedelta(days=STALE_DAYS)
        stale_count = 0
        
        for node in nodes:
            last_accessed = node.get("last_accessed")
            if last_accessed:
                try:
                    la = datetime.fromisoformat(last_accessed)
                    if la < cutoff:
                        node["is_stale"] = True
                        stale_count += 1
                except (ValueError, TypeError):
                    pass  # Invalid timestamp, skip staleness check
        
        graph_data["nodes"] = nodes
        self._save_graph_data(graph_data)
        
        self._log(f"Nodes: {stale_count} marked as stale")
        return stale_count
    
    def update_qdrant_from_graph(self) -> int:
        """
        Sync graph metadata back to Qdrant payloads.
        """
        qdrant = self._get_qdrant()
        if not qdrant:
            return 0
        
        graph_data = self._load_graph_data()
        nodes = graph_data.get("nodes", [])
        
        updated = 0
        
        for node in nodes:
            qdrant_id = node.get("qdrant_id", node.get("id"))
            if not qdrant_id:
                continue
            
            payload_update = {}
            if node.get("cluster_id"):
                payload_update["cluster_id"] = node["cluster_id"]
            if node.get("topic"):
                payload_update["topic"] = node["topic"]
            if node.get("is_stale"):
                payload_update["is_stale"] = True
            
            if payload_update:
                try:
                    from config import COLLECTIONS
                    collection = COLLECTIONS.get("discovered_knowledge", "ira_discovered_knowledge")
                    
                    qdrant.set_payload(
                        collection_name=collection,
                        payload=payload_update,
                        points=[qdrant_id],
                    )
                    updated += 1
                except Exception as e:
                    pass
        
        self._log(f"Qdrant: {updated} payloads updated")
        return updated
    
    # =========================================================================
    # MAIN CONSOLIDATION
    # =========================================================================
    
    def consolidate(self, days: int = 1) -> ConsolidationResult:
        """
        Run the full consolidation cycle (call this nightly).
        """
        self._log("=" * 60)
        self._log("KNOWLEDGE GRAPH CONSOLIDATION")
        self._log("=" * 60)
        
        start_time = datetime.now()
        
        self._log("\n📊 Phase 1: Analyzing interactions...")
        interactions = self.analyze_interactions(days=days)
        
        co_access = self._calculate_co_access_matrix(interactions)
        self._log(f"  Co-access pairs: {len(co_access)}")
        
        knowledge_gaps = self._identify_knowledge_gaps(interactions)
        if knowledge_gaps:
            self._log(f"  Knowledge gaps identified: {len(knowledge_gaps)}")
        
        self._log("\n🔗 Phase 2: Tuning relationships...")
        strengthened, weakened, created = self.tune_relationships(co_access)
        
        self._log("\n📦 Phase 3: Reorganizing clusters...")
        clusters_reorg = self.reorganize_clusters(co_access)
        
        self._log("\n🔄 Phase 4: Updating nodes...")
        stale = self.update_stale_nodes()
        qdrant_updated = self.update_qdrant_from_graph()
        
        # ⚡ Phase 5: Power Level Training (Saiyan Training)
        self._log("\n⚡ Phase 5: Agent power level training...")
        self._apply_training_boosts(
            interactions=len(interactions),
            lessons=created + strengthened,
            errors_fixed=qdrant_updated,
        )
        
        result = ConsolidationResult(
            timestamp=datetime.now(),
            interactions_analyzed=len(interactions),
            edges_strengthened=strengthened,
            edges_weakened=weakened,
            edges_created=created,
            nodes_updated=qdrant_updated + stale,
            clusters_reorganized=clusters_reorg,
            knowledge_gaps=knowledge_gaps,
        )
        
        self._save_consolidation_log(result)
        
        duration = (datetime.now() - start_time).total_seconds()
        
        self._log("\n" + "=" * 60)
        self._log("CONSOLIDATION COMPLETE")
        self._log("=" * 60)
        self._log(f"  Duration: {duration:.1f}s")
        self._log(f"  Interactions analyzed: {result.interactions_analyzed}")
        self._log(f"  Edges: +{result.edges_strengthened} ↑, -{result.edges_weakened} ↓, +{result.edges_created} new")
        self._log(f"  Nodes updated: {result.nodes_updated}")
        self._log(f"  Clusters reorganized: {result.clusters_reorganized}")
        if knowledge_gaps:
            self._log(f"  Knowledge gaps: {len(knowledge_gaps)}")
            for gap in knowledge_gaps[:3]:
                self._log(f"    - {gap[:60]}...")
        
        return result
    
    def _apply_training_boosts(self, interactions: int, lessons: int, errors_fixed: int):
        """
        Apply training boosts to all agents' power levels during dream mode.
        
        Like Saiyans training in the Hyperbolic Time Chamber, agents get stronger
        from their night training session.
        """
        if not POWER_LEVELS_AVAILABLE:
            self._log("  Power levels not available, skipping training")
            return
        
        try:
            tracker = get_power_tracker()
            
            # All agents benefit from dream mode training
            agents = ["chief_of_staff", "researcher", "writer", "fact_checker", "reflector"]
            
            for agent_id in agents:
                tracker.apply_training_boost(
                    agent_id,
                    lessons_learned=lessons,
                    errors_analyzed=errors_fixed,
                    interactions_reviewed=interactions,
                )
            
            self._log(f"  Applied training boosts to {len(agents)} agents")
            self._log(f"    Lessons: {lessons}, Errors analyzed: {errors_fixed}, Interactions: {interactions}")
            
            # Show updated power levels
            for level in tracker.get_leaderboard():
                self._log(f"    {level.agent_name}: {level.total_power:,} ({level.power_tier.value})")
            
        except Exception as e:
            self._log(f"  Failed to apply training boosts: {e}")
    
    def _save_consolidation_log(self, result: ConsolidationResult):
        """Log consolidation results."""
        log_data = []
        if CONSOLIDATION_LOG.exists():
            try:
                log_data = json.loads(CONSOLIDATION_LOG.read_text())
            except (json.JSONDecodeError, IOError) as e:
                self._log(f"Could not read consolidation log, starting fresh: {e}")
                log_data = []
        
        log_data.append({
            "timestamp": result.timestamp.isoformat(),
            "interactions_analyzed": result.interactions_analyzed,
            "edges_strengthened": result.edges_strengthened,
            "edges_weakened": result.edges_weakened,
            "edges_created": result.edges_created,
            "nodes_updated": result.nodes_updated,
            "clusters_reorganized": result.clusters_reorganized,
            "knowledge_gaps_count": len(result.knowledge_gaps),
        })
        
        log_data = log_data[-100:]
        
        CONSOLIDATION_LOG.write_text(json.dumps(log_data, indent=2))


if __name__ == "__main__":
    import argparse
    
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="Knowledge Graph Consolidation")
    parser.add_argument("--days", type=int, default=1, help="Days of interactions to analyze")
    parser.add_argument("--quiet", action="store_true", help="Reduce output")
    args = parser.parse_args()
    
    consolidator = GraphConsolidator(verbose=not args.quiet)
    consolidator.consolidate(days=args.days)
