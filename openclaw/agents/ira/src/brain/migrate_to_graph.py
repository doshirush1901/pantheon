#!/usr/bin/env python3
"""
MIGRATE EXISTING KNOWLEDGE TO GRAPH SYSTEM
===========================================

Pulls all existing knowledge from Qdrant collections and reorganizes
it using the new Knowledge Graph system:

1. Fetch all points from Qdrant collections
2. Run through semantic clustering
3. Discover relationships
4. Update Qdrant payloads with cluster_id and topic
5. Save graph structure

Usage:
    python migrate_to_graph.py
    
    # Or with options:
    python migrate_to_graph.py --dry-run  # Preview without changes
    python migrate_to_graph.py --collection ira_discovered_knowledge
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import asdict

BRAIN_DIR = Path(__file__).parent
SKILLS_DIR = BRAIN_DIR.parent
AGENT_DIR = SKILLS_DIR.parent
PROJECT_ROOT = AGENT_DIR.parent.parent.parent

sys.path.insert(0, str(AGENT_DIR))
sys.path.insert(0, str(BRAIN_DIR))

# Import from centralized config
try:
    from config import COLLECTIONS, QDRANT_URL, get_logger
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
    QDRANT_URL = os.environ.get("QDRANT_URL", "http://localhost:6333")
    COLLECTIONS = {
        "chunks_voyage": "ira_chunks_v4_voyage",
        "discovered_knowledge": "ira_discovered_knowledge",
    }

from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, UpdateStatus

from knowledge_graph import KnowledgeGraph, KnowledgeNode

KNOWLEDGE_DIR = PROJECT_ROOT / "data" / "knowledge"
MIGRATION_LOG = KNOWLEDGE_DIR / "migration_log.json"

BATCH_SIZE = 100


def fetch_all_points(qdrant: QdrantClient, collection: str) -> List[Dict]:
    """Fetch all points from a Qdrant collection."""
    points = []
    offset = None
    
    while True:
        result = qdrant.scroll(
            collection_name=collection,
            limit=BATCH_SIZE,
            offset=offset,
            with_payload=True,
            with_vectors=True,
        )
        
        batch_points, next_offset = result
        
        for point in batch_points:
            points.append({
                "id": point.id,
                "payload": point.payload or {},
                "vector": point.vector,
            })
        
        if next_offset is None:
            break
        offset = next_offset
    
    return points


def points_to_items(points: List[Dict]) -> List[Dict[str, Any]]:
    """Convert Qdrant points to knowledge items for graph processing."""
    items = []
    
    for point in points:
        payload = point.get("payload", {})
        
        text = payload.get("text", payload.get("raw_text", ""))
        if not text or len(text) < 10:
            continue
        
        entity = ""
        machines = payload.get("machines", [])
        if machines:
            entity = machines[0] if isinstance(machines, list) else machines
        if not entity:
            entity = payload.get("entity", payload.get("model", ""))
        
        items.append({
            "point_id": point["id"],
            "text": text[:2000],
            "entity": entity,
            "knowledge_type": payload.get("doc_type", payload.get("knowledge_type", "general")),
            "source_file": payload.get("filename", payload.get("source_file", "")),
            "metadata": {
                k: v for k, v in payload.items() 
                if k not in ["text", "raw_text", "machines", "entity", "doc_type", "filename"]
            },
            "_vector": point.get("vector"),
        })
    
    return items


def update_qdrant_payloads(
    qdrant: QdrantClient, 
    collection: str, 
    items: List[Dict],
    dry_run: bool = False
) -> int:
    """Update Qdrant payloads with cluster_id and topic."""
    updated = 0
    
    for item in items:
        point_id = item.get("point_id")
        if not point_id:
            continue
        
        cluster_id = item.get("cluster_id")
        cluster_name = item.get("cluster_name", "")
        topic = item.get("topic")
        
        if not cluster_id and not topic:
            continue
        
        update_payload = {}
        if cluster_id:
            update_payload["cluster_id"] = cluster_id
            update_payload["cluster_name"] = cluster_name
        if topic:
            update_payload["topic"] = topic
        
        if dry_run:
            print(f"  [DRY-RUN] Would update {point_id}: {update_payload}")
            updated += 1
        else:
            try:
                qdrant.set_payload(
                    collection_name=collection,
                    payload=update_payload,
                    points=[point_id],
                )
                updated += 1
            except Exception as e:
                print(f"  Error updating {point_id}: {e}")
    
    return updated


def migrate_collection(
    collection: str, 
    graph: KnowledgeGraph,
    dry_run: bool = False,
    verbose: bool = True,
) -> Dict[str, Any]:
    """Migrate a single collection to the graph system."""
    
    result = {
        "collection": collection,
        "started_at": datetime.now().isoformat(),
        "points_fetched": 0,
        "items_processed": 0,
        "clusters_created": 0,
        "relationships_discovered": 0,
        "payloads_updated": 0,
        "errors": [],
    }
    
    if verbose:
        print(f"\n{'='*60}")
        print(f"MIGRATING: {collection}")
        print(f"{'='*60}")
    
    qdrant = QdrantClient(url=QDRANT_URL)
    
    try:
        qdrant.get_collection(collection)
    except Exception as e:
        result["errors"].append(f"Collection not found: {e}")
        return result
    
    if verbose:
        print(f"Fetching points from {collection}...")
    
    points = fetch_all_points(qdrant, collection)
    result["points_fetched"] = len(points)
    
    if verbose:
        print(f"  Found {len(points)} points")
    
    if not points:
        return result
    
    items = points_to_items(points)
    result["items_processed"] = len(items)
    
    if verbose:
        print(f"  Converted to {len(items)} processable items")
    
    if len(items) < 2:
        if verbose:
            print("  Not enough items for clustering")
        return result
    
    if verbose:
        print(f"Clustering {len(items)} items...")
    
    clustered_items, clusters = graph.cluster_items(items)
    result["clusters_created"] = len(clusters)
    
    if verbose:
        print(f"  Created {len(clusters)} clusters")
        for cluster in clusters[:5]:
            print(f"    - {cluster.name} ({len(cluster.node_ids)} items, coherence: {cluster.coherence:.2f})")
    
    if verbose:
        print(f"Discovering relationships...")
    
    relationships = graph.discover_relationships(clustered_items)
    result["relationships_discovered"] = len(relationships)
    
    if verbose:
        print(f"  Found {len(relationships)} relationships")
    
    for item, clustered in zip(items, clustered_items):
        item["cluster_id"] = clustered.get("cluster_id")
        item["cluster_name"] = clustered.get("cluster_name", "")
        item["topic"] = clustered.get("topic")
    
    if verbose:
        print(f"Updating Qdrant payloads...")
    
    updated = update_qdrant_payloads(qdrant, collection, items, dry_run=dry_run)
    result["payloads_updated"] = updated
    
    if verbose:
        action = "Would update" if dry_run else "Updated"
        print(f"  {action} {updated} point payloads")
    
    for item in items:
        if item.get("entity"):
            node = KnowledgeNode(
                id=f"{item['entity']}_{str(item['point_id'])[:8]}",
                text=item["text"][:500],
                entity=item["entity"],
                knowledge_type=item["knowledge_type"],
                source_file=item["source_file"],
                cluster_id=item.get("cluster_id"),
                topic=item.get("topic"),
            )
            graph.add_node(node)
    
    result["completed_at"] = datetime.now().isoformat()
    return result


def main():
    parser = argparse.ArgumentParser(description="Migrate knowledge to graph system")
    parser.add_argument("--dry-run", action="store_true", help="Preview without making changes")
    parser.add_argument("--collection", type=str, help="Migrate specific collection only")
    parser.add_argument("--quiet", action="store_true", help="Reduce output")
    args = parser.parse_args()
    
    verbose = not args.quiet
    
    if verbose:
        print("="*60)
        print("KNOWLEDGE GRAPH MIGRATION")
        print("="*60)
        print(f"Qdrant URL: {QDRANT_URL}")
        print(f"Dry run: {args.dry_run}")
        print("="*60)
    
    KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)
    
    graph = KnowledgeGraph(verbose=verbose)
    
    if args.collection:
        collections = [args.collection]
    else:
        collections = [
            COLLECTIONS.get("discovered_knowledge", "ira_discovered_knowledge"),
            COLLECTIONS.get("chunks_voyage", "ira_chunks_v4_voyage"),
        ]
    
    all_results = []
    
    for collection in collections:
        result = migrate_collection(
            collection=collection,
            graph=graph,
            dry_run=args.dry_run,
            verbose=verbose,
        )
        all_results.append(result)
    
    graph._save_graph()
    
    migration_log = {
        "migration_at": datetime.now().isoformat(),
        "dry_run": args.dry_run,
        "collections": all_results,
        "total_clusters": len(graph.clusters),
        "total_nodes": len(graph.nodes),
        "total_edges": len(graph.edges),
    }
    
    MIGRATION_LOG.write_text(json.dumps(migration_log, indent=2, default=str))
    
    if verbose:
        print("\n" + "="*60)
        print("MIGRATION COMPLETE")
        print("="*60)
        
        total_points = sum(r["points_fetched"] for r in all_results)
        total_clusters = sum(r["clusters_created"] for r in all_results)
        total_relationships = sum(r["relationships_discovered"] for r in all_results)
        total_updated = sum(r["payloads_updated"] for r in all_results)
        
        print(f"Points processed: {total_points}")
        print(f"Clusters created: {total_clusters}")
        print(f"Relationships: {total_relationships}")
        print(f"Payloads updated: {total_updated}")
        print(f"\nGraph saved to: {KNOWLEDGE_DIR}")
        print(f"Migration log: {MIGRATION_LOG}")
        
        print("\n" + graph.visualize_stats())


if __name__ == "__main__":
    main()
