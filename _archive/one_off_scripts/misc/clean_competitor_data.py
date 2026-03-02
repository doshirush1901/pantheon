#!/usr/bin/env python3
"""
CLEAN COMPETITOR DATA FROM QDRANT
=================================

Removes all chunks containing competitor mentions from Qdrant collections.
This ensures Ira never retrieves misleading data from competitors.

Usage:
    python scripts/clean_competitor_data.py --dry-run    # Preview what would be deleted
    python scripts/clean_competitor_data.py              # Actually delete
    python scripts/clean_competitor_data.py --verbose    # Show details of each deletion
"""

import os
import sys
import re
import argparse
from pathlib import Path
from typing import List, Set

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "openclaw" / "agents" / "ira"))

try:
    from config import QDRANT_URL
except ImportError:
    QDRANT_URL = os.environ.get("QDRANT_URL", "http://localhost:6333")

from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

# Competitor names to search for (actual competitors only)
COMPETITORS = [
    "frimo",
    "illig", 
    "kiefel",
    "geiss",
    "cms thermoforming",
    "maac",
    "formech",
    "belovac",
    "ezform",
    "gabler",
    "brown machine",
    "sencorp",
]

# Patterns that indicate non-Machinecraft specs (disabled for now)
COMPETITOR_PATTERNS = [
    # r'\d\.\d{3}\s*[x×]\s*\d\.\d{3}',  # European format - too broad
    # r'€\s*\d+[\.,]\d{3}',              # Euro pricing - Machinecraft quotes in Euros too
]

# Collections to clean
COLLECTIONS = [
    "ira_chunks_v4_voyage",
    "ira_dream_knowledge_v1",
    "ira_feature_knowledge_v1",
]


def is_competitor_content(text: str) -> tuple[bool, str]:
    """
    Check if text contains competitor mentions.
    Returns (is_competitor, reason)
    """
    text_lower = text.lower()
    
    # Check for competitor names
    for comp in COMPETITORS:
        if comp in text_lower:
            return True, f"Contains competitor: {comp}"
    
    # Check for competitor patterns
    for pattern in COMPETITOR_PATTERNS:
        if re.search(pattern, text):
            # But exclude if it also mentions Machinecraft
            if "machinecraft" not in text_lower and "pf1" not in text_lower:
                return True, f"Matches competitor pattern: {pattern}"
    
    return False, ""


def clean_collection(
    qdrant: QdrantClient,
    collection_name: str,
    dry_run: bool = True,
    verbose: bool = False
) -> dict:
    """
    Clean competitor data from a single collection.
    """
    print(f"\n{'=' * 60}")
    print(f"Cleaning: {collection_name}")
    print(f"{'=' * 60}")
    
    try:
        info = qdrant.get_collection(collection_name)
        total_points = info.points_count
        print(f"Total points: {total_points}")
    except Exception as e:
        print(f"Collection not found or error: {e}")
        return {"collection": collection_name, "error": str(e)}
    
    if total_points == 0:
        print("Empty collection, skipping")
        return {"collection": collection_name, "total": 0, "deleted": 0}
    
    # Scroll through all points
    competitor_ids: Set[str] = set()
    offset = None
    batch_num = 0
    
    while True:
        batch_num += 1
        print(f"  Scanning batch {batch_num}...", end="\r")
        
        results = qdrant.scroll(
            collection_name=collection_name,
            limit=100,
            offset=offset,
            with_payload=True,
            with_vectors=False
        )
        
        points, offset = results
        
        if not points:
            break
        
        for point in points:
            # Get text content from payload
            payload = point.payload or {}
            text = ""
            
            # Try different payload fields
            for field in ["text", "content", "chunk", "body", "description"]:
                if field in payload and payload[field]:
                    text += str(payload[field]) + " "
            
            # Also check source/filename
            if "source" in payload:
                text += str(payload["source"]) + " "
            if "filename" in payload:
                text += str(payload["filename"]) + " "
            
            is_comp, reason = is_competitor_content(text)
            
            if is_comp:
                competitor_ids.add(point.id)
                if verbose:
                    preview = text[:100].replace("\n", " ")
                    print(f"\n  Found competitor: {point.id}")
                    print(f"    Reason: {reason}")
                    print(f"    Preview: {preview}...")
        
        if offset is None:
            break
    
    print(f"\n  Found {len(competitor_ids)} competitor chunks out of {total_points}")
    
    if not competitor_ids:
        print("  No competitor data found!")
        return {"collection": collection_name, "total": total_points, "deleted": 0}
    
    if dry_run:
        print(f"\n  [DRY RUN] Would delete {len(competitor_ids)} points")
        if verbose and competitor_ids:
            print(f"  IDs: {list(competitor_ids)[:10]}...")
    else:
        # Actually delete
        print(f"\n  Deleting {len(competitor_ids)} points...")
        
        # Delete in batches
        ids_list = list(competitor_ids)
        batch_size = 100
        
        for i in range(0, len(ids_list), batch_size):
            batch = ids_list[i:i+batch_size]
            qdrant.delete(
                collection_name=collection_name,
                points_selector=batch
            )
            print(f"    Deleted batch {i//batch_size + 1}/{(len(ids_list)-1)//batch_size + 1}")
        
        print(f"  Successfully deleted {len(competitor_ids)} competitor chunks")
    
    return {
        "collection": collection_name,
        "total": total_points,
        "deleted": len(competitor_ids),
        "dry_run": dry_run
    }


def main():
    parser = argparse.ArgumentParser(description="Clean competitor data from Qdrant")
    parser.add_argument("--dry-run", action="store_true", help="Preview without deleting")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show details")
    parser.add_argument("--collection", type=str, help="Clean specific collection only")
    args = parser.parse_args()
    
    print("\n" + "=" * 60)
    print("QDRANT COMPETITOR DATA CLEANER")
    print("=" * 60)
    
    if args.dry_run:
        print("\n*** DRY RUN MODE - No data will be deleted ***\n")
    else:
        print("\n*** LIVE MODE - Data WILL be deleted ***\n")
        response = input("Are you sure you want to proceed? (yes/no): ")
        if response.lower() != "yes":
            print("Aborted.")
            return
    
    # Connect to Qdrant
    print(f"\nConnecting to Qdrant at {QDRANT_URL}...")
    qdrant = QdrantClient(url=QDRANT_URL)
    
    # Get list of collections to clean
    if args.collection:
        collections = [args.collection]
    else:
        collections = COLLECTIONS
    
    results = []
    total_deleted = 0
    
    for collection in collections:
        result = clean_collection(
            qdrant=qdrant,
            collection_name=collection,
            dry_run=args.dry_run,
            verbose=args.verbose
        )
        results.append(result)
        if "deleted" in result:
            total_deleted += result["deleted"]
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    for result in results:
        if "error" in result:
            print(f"  {result['collection']}: ERROR - {result['error']}")
        else:
            status = "[DRY RUN]" if result.get("dry_run") else "[DELETED]"
            print(f"  {result['collection']}: {result['deleted']}/{result['total']} chunks {status}")
    
    print(f"\nTotal competitor chunks {'identified' if args.dry_run else 'deleted'}: {total_deleted}")
    
    if args.dry_run:
        print("\nRun without --dry-run to actually delete these chunks.")


if __name__ == "__main__":
    main()
