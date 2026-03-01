#!/usr/bin/env python3
"""
KNOWLEDGE GRAPH SYSTEM
======================

Organizes knowledge like a graph database / Obsidian-style system:
- Semantic clustering: Group similar knowledge together
- Auto-linking: Discover relationships between knowledge items
- Topic detection: Automatically categorize knowledge
- Graph traversal: Navigate related knowledge

Architecture:
- Nodes: Knowledge items stored in Qdrant
- Edges: Relationships stored in knowledge_graph.json
- Clusters: Semantic groups for better organization
- Topics: Auto-detected categories

Usage:
    from knowledge_graph import KnowledgeGraph
    
    graph = KnowledgeGraph()
    
    # Organize items into clusters before ingestion
    clustered_items = graph.cluster_items(items)
    
    # Find relationships between items
    relationships = graph.discover_relationships(items)
    
    # Get related knowledge
    related = graph.get_related("PF1-C-2015", depth=2)
"""

import logging
import os
import sys
import json

logger = logging.getLogger(__name__)
import hashlib
import numpy as np
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Set, Tuple
from collections import defaultdict

BRAIN_DIR = Path(__file__).parent
SKILLS_DIR = BRAIN_DIR.parent
AGENT_DIR = SKILLS_DIR.parent
PROJECT_ROOT = AGENT_DIR.parent.parent.parent

sys.path.insert(0, str(AGENT_DIR))

# Import from centralized config
try:
    from config import VOYAGE_API_KEY, QDRANT_URL, get_logger
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

KNOWLEDGE_DIR = PROJECT_ROOT / "data" / "knowledge"
GRAPH_FILE = KNOWLEDGE_DIR / "knowledge_graph.json"
CLUSTERS_FILE = KNOWLEDGE_DIR / "clusters.json"

SIMILARITY_THRESHOLD = 0.75
MIN_CLUSTER_SIZE = 2
MAX_RELATIONSHIPS_PER_ITEM = 5


@dataclass
class KnowledgeNode:
    """A node in the knowledge graph."""
    id: str
    text: str
    entity: str
    knowledge_type: str
    source_file: str
    
    cluster_id: Optional[str] = None
    topic: Optional[str] = None
    embedding: List[float] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __hash__(self):
        return hash(self.id)


@dataclass
class KnowledgeEdge:
    """A relationship between knowledge nodes."""
    source_id: str
    target_id: str
    relationship_type: str
    strength: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __hash__(self):
        return hash((self.source_id, self.target_id, self.relationship_type))


@dataclass
class KnowledgeCluster:
    """A semantic cluster of related knowledge."""
    id: str
    name: str
    topic: str
    node_ids: List[str]
    centroid: List[float]
    coherence: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class KnowledgeGraph:
    """
    Graph-based knowledge organization system.
    
    Organizes knowledge like Obsidian:
    - Clusters similar items together
    - Creates links between related items
    - Enables graph traversal
    """
    
    TOPIC_KEYWORDS = {
        "machine_specs": ["forming area", "heater", "vacuum", "cylinder", "kw", "mm", "power"],
        "pricing": ["price", "cost", "inr", "usd", "quote", "offer"],
        "materials": ["abs", "hdpe", "pp", "pet", "tpu", "material", "sheet", "thickness"],
        "applications": ["automotive", "packaging", "signage", "medical", "food", "industrial"],
        "processes": ["thermoforming", "vacuum forming", "pressure forming", "lamination"],
        "customers": ["company", "client", "customer", "contact", "email", "lead"],
    }
    
    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self._voyage = None
        self._qdrant = None
        
        self.nodes: Dict[str, KnowledgeNode] = {}
        self.edges: List[KnowledgeEdge] = []
        self.clusters: Dict[str, KnowledgeCluster] = {}
        
        KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)
        self._load_graph()
    
    def _log(self, msg: str):
        if self.verbose:
            logger.info(msg)
    
    def _get_voyage(self):
        if self._voyage is None:
            import voyageai
            self._voyage = voyageai.Client(api_key=VOYAGE_API_KEY)
        return self._voyage
    
    def _get_qdrant(self):
        if self._qdrant is None:
            from qdrant_client import QdrantClient
            self._qdrant = QdrantClient(url=QDRANT_URL)
        return self._qdrant
    
    def _load_graph(self):
        """Load existing graph from disk."""
        if GRAPH_FILE.exists():
            try:
                data = json.loads(GRAPH_FILE.read_text())
                
                for node_data in data.get("nodes", []):
                    node = KnowledgeNode(**node_data)
                    self.nodes[node.id] = node
                
                for edge_data in data.get("edges", []):
                    self.edges.append(KnowledgeEdge(**edge_data))
                
                self._log(f"Loaded graph: {len(self.nodes)} nodes, {len(self.edges)} edges")
            except Exception as e:
                self._log(f"Error loading graph: {e}")
        
        if CLUSTERS_FILE.exists():
            try:
                data = json.loads(CLUSTERS_FILE.read_text())
                for cluster_data in data.get("clusters", []):
                    cluster = KnowledgeCluster(**cluster_data)
                    self.clusters[cluster.id] = cluster
                self._log(f"Loaded {len(self.clusters)} clusters")
            except Exception:
                pass
    
    def _save_graph(self):
        """Save graph to disk."""
        try:
            graph_data = {
                "updated_at": datetime.now().isoformat(),
                "nodes": [asdict(n) for n in self.nodes.values()],
                "edges": [asdict(e) for e in self.edges],
            }
            GRAPH_FILE.write_text(json.dumps(graph_data, indent=2, default=str))
            
            cluster_data = {
                "updated_at": datetime.now().isoformat(),
                "clusters": [asdict(c) for c in self.clusters.values()],
            }
            CLUSTERS_FILE.write_text(json.dumps(cluster_data, indent=2, default=str))
            
            self._log(f"Saved graph: {len(self.nodes)} nodes, {len(self.edges)} edges, {len(self.clusters)} clusters")
        except Exception as e:
            self._log(f"Error saving graph: {e}")
    
    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        a = np.array(a)
        b = np.array(b)
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))
    
    def _detect_topic(self, text: str) -> str:
        """Auto-detect topic from text content."""
        text_lower = text.lower()
        topic_scores = {}
        
        for topic, keywords in self.TOPIC_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            if score > 0:
                topic_scores[topic] = score
        
        if topic_scores:
            return max(topic_scores, key=topic_scores.get)
        return "general"
    
    def _generate_cluster_id(self, topic: str, index: int) -> str:
        """Generate a cluster ID."""
        return f"cluster_{topic}_{index}"
    
    def _generate_cluster_name(self, nodes: List[KnowledgeNode]) -> str:
        """Generate a human-readable cluster name."""
        entities = [n.entity for n in nodes if n.entity]
        if entities:
            if len(entities) <= 3:
                return " & ".join(entities)
            return f"{entities[0]} and {len(entities)-1} related"
        
        topics = [n.topic for n in nodes if n.topic]
        if topics:
            return f"{topics[0].replace('_', ' ').title()} Group"
        
        return "Knowledge Cluster"
    
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for texts."""
        voyage = self._get_voyage()
        result = voyage.embed(texts, model="voyage-3", input_type="document")
        return result.embeddings
    
    def cluster_items(
        self, 
        items: List[Dict[str, Any]],
        similarity_threshold: float = SIMILARITY_THRESHOLD,
    ) -> Tuple[List[Dict[str, Any]], List[KnowledgeCluster]]:
        """
        Cluster similar items together using semantic similarity.
        
        Returns items with cluster_id assigned and list of clusters.
        """
        if not items:
            return [], []
        
        self._log(f"Clustering {len(items)} items...")
        
        texts = [item.get("text", "") for item in items]
        embeddings = self.embed_texts(texts)
        
        for item, emb in zip(items, embeddings):
            item["_embedding"] = emb
            item["topic"] = self._detect_topic(item.get("text", ""))
        
        topic_groups = defaultdict(list)
        for i, item in enumerate(items):
            topic_groups[item["topic"]].append((i, item))
        
        clusters = []
        cluster_idx = 0
        
        for topic, topic_items in topic_groups.items():
            if len(topic_items) < MIN_CLUSTER_SIZE:
                for i, item in topic_items:
                    item["cluster_id"] = None
                continue
            
            indices = [i for i, _ in topic_items]
            topic_embeddings = [items[i]["_embedding"] for i in indices]
            
            assigned = set()
            
            for idx, (i, item) in enumerate(topic_items):
                if i in assigned:
                    continue
                
                cluster_members = [(i, item)]
                assigned.add(i)
                
                for jdx, (j, other_item) in enumerate(topic_items):
                    if j in assigned:
                        continue
                    
                    sim = self._cosine_similarity(
                        topic_embeddings[idx], 
                        topic_embeddings[jdx]
                    )
                    
                    if sim >= similarity_threshold:
                        cluster_members.append((j, other_item))
                        assigned.add(j)
                
                if len(cluster_members) >= MIN_CLUSTER_SIZE:
                    cluster_id = self._generate_cluster_id(topic, cluster_idx)
                    cluster_idx += 1
                    
                    member_embeddings = [items[m[0]]["_embedding"] for m in cluster_members]
                    centroid = np.mean(member_embeddings, axis=0).tolist()
                    
                    coherences = [
                        self._cosine_similarity(emb, centroid) 
                        for emb in member_embeddings
                    ]
                    coherence = float(np.mean(coherences))
                    
                    nodes = [
                        KnowledgeNode(
                            id=f"{item.get('entity', 'item')}_{hashlib.md5(item['text'].encode()).hexdigest()[:8]}",
                            text=item["text"][:500],
                            entity=item.get("entity", ""),
                            knowledge_type=item.get("knowledge_type", "general"),
                            source_file=item.get("source_file", ""),
                            topic=topic,
                        )
                        for _, item in cluster_members
                    ]
                    
                    cluster = KnowledgeCluster(
                        id=cluster_id,
                        name=self._generate_cluster_name(nodes),
                        topic=topic,
                        node_ids=[n.id for n in nodes],
                        centroid=centroid,
                        coherence=coherence,
                    )
                    clusters.append(cluster)
                    
                    for member_idx, member_item in cluster_members:
                        items[member_idx]["cluster_id"] = cluster_id
                        items[member_idx]["cluster_name"] = cluster.name
                else:
                    for member_idx, member_item in cluster_members:
                        items[member_idx]["cluster_id"] = None
        
        for item in items:
            if "_embedding" in item:
                del item["_embedding"]
        
        self._log(f"Created {len(clusters)} clusters from {len(items)} items")
        
        for cluster in clusters:
            self.clusters[cluster.id] = cluster
        self._save_graph()
        
        return items, clusters
    
    def discover_relationships(
        self,
        items: List[Dict[str, Any]],
        max_relationships: int = MAX_RELATIONSHIPS_PER_ITEM,
    ) -> List[KnowledgeEdge]:
        """
        Discover relationships between knowledge items.
        
        Relationship types:
        - same_entity: Same machine/entity
        - same_cluster: In same semantic cluster
        - similar_content: High semantic similarity
        - same_source: From same document
        - related_topic: Related topic
        """
        if len(items) < 2:
            return []
        
        self._log(f"Discovering relationships among {len(items)} items...")
        
        texts = [item.get("text", "") for item in items]
        embeddings = self.embed_texts(texts)
        
        new_edges = []
        
        for i, item_a in enumerate(items):
            relationships_for_item = []
            
            for j, item_b in enumerate(items):
                if i >= j:
                    continue
                
                entity_a = item_a.get("entity", "")
                entity_b = item_b.get("entity", "")
                
                if entity_a and entity_a == entity_b:
                    relationships_for_item.append(KnowledgeEdge(
                        source_id=f"{entity_a}_{i}",
                        target_id=f"{entity_b}_{j}",
                        relationship_type="same_entity",
                        strength=1.0,
                        metadata={"entity": entity_a}
                    ))
                    continue
                
                cluster_a = item_a.get("cluster_id")
                cluster_b = item_b.get("cluster_id")
                
                if cluster_a and cluster_a == cluster_b:
                    relationships_for_item.append(KnowledgeEdge(
                        source_id=f"{entity_a or i}",
                        target_id=f"{entity_b or j}",
                        relationship_type="same_cluster",
                        strength=0.9,
                        metadata={"cluster": cluster_a}
                    ))
                    continue
                
                sim = self._cosine_similarity(embeddings[i], embeddings[j])
                if sim >= SIMILARITY_THRESHOLD:
                    relationships_for_item.append(KnowledgeEdge(
                        source_id=f"{entity_a or i}",
                        target_id=f"{entity_b or j}",
                        relationship_type="similar_content",
                        strength=sim,
                    ))
                
                source_a = item_a.get("source_file", "")
                source_b = item_b.get("source_file", "")
                if source_a and source_a == source_b:
                    relationships_for_item.append(KnowledgeEdge(
                        source_id=f"{entity_a or i}",
                        target_id=f"{entity_b or j}",
                        relationship_type="same_source",
                        strength=0.7,
                        metadata={"source": source_a}
                    ))
            
            relationships_for_item.sort(key=lambda e: e.strength, reverse=True)
            new_edges.extend(relationships_for_item[:max_relationships])
        
        self.edges.extend(new_edges)
        self._save_graph()
        
        self._log(f"Discovered {len(new_edges)} relationships")
        return new_edges
    
    def add_node(self, node: KnowledgeNode):
        """Add a node to the graph."""
        self.nodes[node.id] = node
    
    def add_edge(self, edge: KnowledgeEdge):
        """Add an edge to the graph."""
        self.edges.append(edge)
    
    def get_related(
        self, 
        entity_or_id: str, 
        depth: int = 1,
        relationship_types: Optional[List[str]] = None,
    ) -> List[Tuple[KnowledgeNode, KnowledgeEdge]]:
        """
        Get related knowledge items using graph traversal.
        
        Args:
            entity_or_id: Entity name or node ID to start from
            depth: How many hops to traverse (1 = direct, 2 = friends of friends)
            relationship_types: Filter by relationship type
        
        Returns:
            List of (node, edge) tuples for DIFFERENT entities (excludes same entity)
        """
        entity_to_nodes: Dict[str, KnowledgeNode] = {}
        for node in self.nodes.values():
            if node.entity:
                entity_key = node.entity.lower()
                if entity_key not in entity_to_nodes:
                    entity_to_nodes[entity_key] = node
        
        starting_entity = entity_or_id.lower()
        matching_entities = set()
        
        for entity_key in entity_to_nodes.keys():
            if starting_entity in entity_key or entity_key in starting_entity:
                matching_entities.add(entity_key)
        
        if not matching_entities:
            return []
        
        visited_entities = set(matching_entities)
        results = []
        current_frontier = matching_entities
        
        edge_index_source: Dict[str, List[KnowledgeEdge]] = defaultdict(list)
        edge_index_target: Dict[str, List[KnowledgeEdge]] = defaultdict(list)
        
        for edge in self.edges:
            source_key = edge.source_id.lower().split('_')[0]
            target_key = edge.target_id.lower().split('_')[0]
            edge_index_source[source_key].append(edge)
            edge_index_target[target_key].append(edge)
        
        for _ in range(depth):
            next_frontier = set()
            
            for frontier_entity in current_frontier:
                frontier_key = frontier_entity.split('_')[0]
                
                for edge in edge_index_source.get(frontier_key, []):
                    if relationship_types and edge.relationship_type not in relationship_types:
                        continue
                    
                    target_key = edge.target_id.lower().split('_')[0]
                    
                    is_same_entity = any(
                        target_key in orig or orig in target_key
                        for orig in matching_entities
                    )
                    if is_same_entity:
                        continue
                    
                    if target_key not in visited_entities:
                        target_node = entity_to_nodes.get(target_key)
                        if not target_node:
                            for e, node in entity_to_nodes.items():
                                if target_key in e or e in target_key:
                                    target_node = node
                                    break
                        
                        if target_node:
                            results.append((target_node, edge))
                            next_frontier.add(target_key)
                            visited_entities.add(target_key)
                
                for edge in edge_index_target.get(frontier_key, []):
                    if relationship_types and edge.relationship_type not in relationship_types:
                        continue
                    
                    source_key = edge.source_id.lower().split('_')[0]
                    
                    is_same_entity = any(
                        source_key in orig or orig in source_key
                        for orig in matching_entities
                    )
                    if is_same_entity:
                        continue
                    
                    if source_key not in visited_entities:
                        source_node = entity_to_nodes.get(source_key)
                        if not source_node:
                            for e, node in entity_to_nodes.items():
                                if source_key in e or e in source_key:
                                    source_node = node
                                    break
                        
                        if source_node:
                            results.append((source_node, edge))
                            next_frontier.add(source_key)
                            visited_entities.add(source_key)
            
            current_frontier = next_frontier
            if not current_frontier:
                break
        
        results.sort(key=lambda x: x[1].strength, reverse=True)
        return results
    
    def get_cluster_members(self, cluster_id: str) -> List[KnowledgeNode]:
        """Get all nodes in a cluster."""
        if cluster_id not in self.clusters:
            return []
        
        cluster = self.clusters[cluster_id]
        return [self.nodes[nid] for nid in cluster.node_ids if nid in self.nodes]
    
    def get_topic_graph(self, topic: str) -> Dict[str, Any]:
        """Get subgraph for a specific topic."""
        topic_nodes = [n for n in self.nodes.values() if n.topic == topic]
        topic_node_ids = {n.id for n in topic_nodes}
        
        topic_edges = [
            e for e in self.edges 
            if e.source_id in topic_node_ids or e.target_id in topic_node_ids
        ]
        
        topic_clusters = [
            c for c in self.clusters.values() if c.topic == topic
        ]
        
        return {
            "topic": topic,
            "nodes": [asdict(n) for n in topic_nodes],
            "edges": [asdict(e) for e in topic_edges],
            "clusters": [asdict(c) for c in topic_clusters],
        }
    
    def visualize_stats(self) -> str:
        """Get graph statistics as formatted string."""
        topic_counts = defaultdict(int)
        for node in self.nodes.values():
            topic_counts[node.topic or "unknown"] += 1
        
        edge_type_counts = defaultdict(int)
        for edge in self.edges:
            edge_type_counts[edge.relationship_type] += 1
        
        lines = [
            "=" * 50,
            "KNOWLEDGE GRAPH STATISTICS",
            "=" * 50,
            f"Total Nodes: {len(self.nodes)}",
            f"Total Edges: {len(self.edges)}",
            f"Total Clusters: {len(self.clusters)}",
            "",
            "Nodes by Topic:",
        ]
        
        for topic, count in sorted(topic_counts.items(), key=lambda x: -x[1]):
            lines.append(f"  {topic}: {count}")
        
        lines.append("")
        lines.append("Edges by Type:")
        for etype, count in sorted(edge_type_counts.items(), key=lambda x: -x[1]):
            lines.append(f"  {etype}: {count}")
        
        lines.append("")
        lines.append("Clusters:")
        for cluster in self.clusters.values():
            lines.append(f"  {cluster.name}: {len(cluster.node_ids)} items (coherence: {cluster.coherence:.2f})")
        
        lines.append("=" * 50)
        return "\n".join(lines)


def organize_knowledge(items: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[KnowledgeEdge]]:
    """
    Convenience function to organize knowledge items.
    
    Returns items with cluster assignments and discovered relationships.
    """
    graph = KnowledgeGraph()
    
    clustered_items, clusters = graph.cluster_items(items)
    
    relationships = graph.discover_relationships(clustered_items)
    
    return clustered_items, relationships


# =============================================================================
# MACHINE RELATIONSHIP ENRICHMENT
# =============================================================================

MACHINE_SERIES_PATTERNS = {
    "PF1-C": {"series": "PF1", "variant": "C", "description": "Compact single-station thermoformer"},
    "PF1-X": {"series": "PF1", "variant": "X", "description": "Extended single-station with dual heaters"},
    "PF1-S": {"series": "PF1", "variant": "S", "description": "Standard single-station"},
    "PF1-A": {"series": "PF1", "variant": "A", "description": "Automatic single-station"},
    "PF1-R": {"series": "PF1", "variant": "R", "description": "Rotary single-station"},
    "PF1-P": {"series": "PF1", "variant": "P", "description": "Production single-station"},
    "PF2": {"series": "PF2", "variant": None, "description": "Twin-station thermoformer"},
    "AM": {"series": "AM", "variant": None, "description": "All-servo vacuum forming"},
    "ATF": {"series": "ATF", "variant": None, "description": "Automatic twin-station forming"},
    "IMG": {"series": "IMG", "variant": None, "description": "In-Mold Graining machine"},
    "FCS": {"series": "FCS", "variant": None, "description": "Form-Cut-Stack inline system"},
    "RT": {"series": "RT", "variant": None, "description": "Rotary table former"},
}

APPLICATION_CATEGORIES = {
    "automotive": ["automotive", "car", "vehicle", "dashboard", "interior", "bumper", "bedliner", "fender"],
    "packaging": ["packaging", "blister", "clamshell", "tray", "container", "food", "medical pack"],
    "signage": ["signage", "sign", "letter", "display", "pos", "point of sale", "illuminated"],
    "industrial": ["industrial", "tank", "pallet", "bin", "housing", "enclosure", "cover"],
    "medical": ["medical", "device", "sterile", "healthcare", "hospital", "lab"],
    "appliance": ["appliance", "refrigerator", "liner", "door panel", "housing"],
    "aerospace": ["aerospace", "aircraft", "aviation", "cabin"],
    "marine": ["marine", "boat", "yacht", "watercraft"],
}

MATERIAL_CATEGORIES = {
    "abs": ["abs", "acrylonitrile", "impact resistant"],
    "hdpe": ["hdpe", "high density", "polyethylene", "chemical resistant"],
    "pp": ["pp", "polypropylene"],
    "pet": ["pet", "petg", "polyester"],
    "pc": ["pc", "polycarbonate", "lexan"],
    "pmma": ["pmma", "acrylic", "perspex"],
    "tpu": ["tpu", "thermoplastic polyurethane", "flexible"],
    "hips": ["hips", "high impact polystyrene"],
    "pvc": ["pvc", "vinyl"],
}


def enrich_machine_relationships(graph: "KnowledgeGraph") -> int:
    """
    Enrich the knowledge graph with machine-specific relationships.
    
    Adds relationships for:
    - same_series: Machines in same series (PF1-C-2015 and PF1-C-2020)
    - same_model_family: Machines in same family (PF1-C and PF1-X)
    - application_overlap: Machines used for similar applications
    - material_compatibility: Machines that process same materials
    - size_progression: Machines of increasing/decreasing size
    
    Returns number of new edges added.
    """
    import re
    
    new_edges = []
    
    machine_nodes = [n for n in graph.nodes.values() if n.entity and re.match(r'^(PF1|PF2|AM|ATF|IMG|FCS|RT)', n.entity)]
    
    if not machine_nodes:
        return 0
    
    def parse_machine_model(entity: str) -> Optional[Dict[str, Any]]:
        """Parse machine model into components."""
        match = re.match(r'^(PF1|PF2|AM|ATF|IMG|FCS|RT)-?([A-Z])?-?(\d+)?', entity)
        if match:
            series = match.group(1)
            variant = match.group(2)
            size = match.group(3)
            return {
                "series": series,
                "variant": variant,
                "size": int(size) if size else None,
                "full_prefix": f"{series}-{variant}" if variant else series,
            }
        return None
    
    machine_info = {n.entity: parse_machine_model(n.entity) for n in machine_nodes}
    machine_info = {k: v for k, v in machine_info.items() if v}
    
    for entity_a, info_a in machine_info.items():
        for entity_b, info_b in machine_info.items():
            if entity_a >= entity_b:
                continue
            
            if info_a["full_prefix"] == info_b["full_prefix"] and info_a["size"] and info_b["size"]:
                new_edges.append(KnowledgeEdge(
                    source_id=entity_a,
                    target_id=entity_b,
                    relationship_type="same_series",
                    strength=0.95,
                    metadata={
                        "series": info_a["full_prefix"],
                        "size_diff": abs(info_a["size"] - info_b["size"])
                    }
                ))
            
            elif info_a["series"] == info_b["series"] and info_a["variant"] != info_b["variant"]:
                new_edges.append(KnowledgeEdge(
                    source_id=entity_a,
                    target_id=entity_b,
                    relationship_type="same_model_family",
                    strength=0.85,
                    metadata={"family": info_a["series"]}
                ))
            
            if info_a["size"] and info_b["size"]:
                size_diff = info_b["size"] - info_a["size"]
                if size_diff > 0 and size_diff <= 1000:
                    new_edges.append(KnowledgeEdge(
                        source_id=entity_a,
                        target_id=entity_b,
                        relationship_type="size_progression",
                        strength=0.7,
                        metadata={"direction": "upgrade", "size_increase": size_diff}
                    ))
    
    text_by_entity = defaultdict(list)
    for node in machine_nodes:
        text_by_entity[node.entity].append(node.text.lower())
    
    entity_applications = {}
    for entity, texts in text_by_entity.items():
        combined_text = " ".join(texts)
        apps = set()
        for app_category, keywords in APPLICATION_CATEGORIES.items():
            if any(kw in combined_text for kw in keywords):
                apps.add(app_category)
        if apps:
            entity_applications[entity] = apps
    
    entities_with_apps = list(entity_applications.keys())
    for i, entity_a in enumerate(entities_with_apps):
        for entity_b in entities_with_apps[i+1:]:
            common_apps = entity_applications[entity_a] & entity_applications[entity_b]
            if common_apps:
                new_edges.append(KnowledgeEdge(
                    source_id=entity_a,
                    target_id=entity_b,
                    relationship_type="application_overlap",
                    strength=0.6 + (0.1 * len(common_apps)),
                    metadata={"common_applications": list(common_apps)}
                ))
    
    entity_materials = {}
    for entity, texts in text_by_entity.items():
        combined_text = " ".join(texts)
        materials = set()
        for mat_category, keywords in MATERIAL_CATEGORIES.items():
            if any(kw in combined_text for kw in keywords):
                materials.add(mat_category)
        if materials:
            entity_materials[entity] = materials
    
    entities_with_mats = list(entity_materials.keys())
    for i, entity_a in enumerate(entities_with_mats):
        for entity_b in entities_with_mats[i+1:]:
            common_mats = entity_materials[entity_a] & entity_materials[entity_b]
            if common_mats and len(common_mats) >= 2:
                new_edges.append(KnowledgeEdge(
                    source_id=entity_a,
                    target_id=entity_b,
                    relationship_type="material_compatibility",
                    strength=0.5 + (0.1 * len(common_mats)),
                    metadata={"common_materials": list(common_mats)}
                ))
    
    existing_pairs = {(e.source_id, e.target_id) for e in graph.edges}
    existing_pairs |= {(e.target_id, e.source_id) for e in graph.edges}
    
    unique_new_edges = []
    for edge in new_edges:
        pair = (edge.source_id, edge.target_id)
        if pair not in existing_pairs:
            unique_new_edges.append(edge)
            existing_pairs.add(pair)
            existing_pairs.add((edge.target_id, edge.source_id))
    
    graph.edges.extend(unique_new_edges)
    graph._save_graph()
    
    return len(unique_new_edges)


if __name__ == "__main__":
    print("Knowledge Graph - Test")
    print("=" * 60)
    
    test_items = [
        {"text": "PF1-C-2015 has 72kW top heater and 50.4kW bottom heater for 2000x1500mm forming area", 
         "entity": "PF1-C-2015", "knowledge_type": "machine_spec", "source_file": "specs.xlsx"},
        {"text": "PF1-C-2020 has 96kW top heater and 67.2kW bottom heater for 2000x2000mm forming area", 
         "entity": "PF1-C-2020", "knowledge_type": "machine_spec", "source_file": "specs.xlsx"},
        {"text": "PF1-C-3020 has 144kW top heater for large format thermoforming up to 3000x2000mm", 
         "entity": "PF1-C-3020", "knowledge_type": "machine_spec", "source_file": "specs.xlsx"},
        {"text": "ABS sheet is commonly used for automotive interior parts with good impact resistance", 
         "entity": "ABS", "knowledge_type": "materials", "source_file": "materials.pdf"},
        {"text": "HDPE sheets are used for chemical tanks and industrial containers", 
         "entity": "HDPE", "knowledge_type": "materials", "source_file": "materials.pdf"},
    ]
    
    graph = KnowledgeGraph()
    
    clustered, clusters = graph.cluster_items(test_items)
    print(f"\nClustered {len(test_items)} items into {len(clusters)} clusters")
    
    for item in clustered:
        print(f"  {item.get('entity', 'N/A')}: cluster={item.get('cluster_id', 'None')}, topic={item.get('topic', 'N/A')}")
    
    relationships = graph.discover_relationships(clustered)
    print(f"\nDiscovered {len(relationships)} relationships")
    
    for rel in relationships[:5]:
        print(f"  {rel.source_id} --[{rel.relationship_type}]--> {rel.target_id} (strength: {rel.strength:.2f})")
    
    print("\n" + graph.visualize_stats())
