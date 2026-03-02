#!/usr/bin/env python3
"""
Quick document ingestion script.

Usage:
    python3 scripts/ingest_doc.py /path/to/document.pdf
    python3 scripts/ingest_doc.py --folder /path/to/docs/
    python3 scripts/ingest_doc.py --no-conflicts /path/to/document.pdf

This script:
1. Extracts text from the document (PDF, XLSX, DOCX, CSV, TXT)
2. Uses GPT to extract structured facts
3. Stores facts in Ira's persistent memory
4. Detects conflicts with existing facts
5. Queues conflicts for Telegram clarification
"""

import sys
import os
from pathlib import Path

# Add project to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "openclaw" / "agents" / "ira" / "skills" / "memory"))


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        print("\nSupported formats: PDF, XLSX, XLS, DOCX, DOC, TXT, CSV, MD")
        sys.exit(1)
    
    # Parse arguments
    check_conflicts = True
    paths = []
    is_folder = False
    
    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg == "--no-conflicts":
            check_conflicts = False
        elif arg == "--folder":
            is_folder = True
        else:
            paths.append(arg)
        i += 1
    
    if not paths:
        print("Error: No path provided")
        sys.exit(1)
    
    # Import the ingestor
    try:
        from document_ingestor import DocumentIngestor
    except ImportError:
        from openclaw.agents.ira.src.memory.document_ingestor import DocumentIngestor
    
    ingestor = DocumentIngestor(check_conflicts=check_conflicts)
    
    # Process
    if is_folder:
        for folder_path in paths:
            print(f"\n📂 Processing folder: {folder_path}")
            results = ingestor.ingest_folder(folder_path)
            
            # Summary
            total_facts = sum(r.facts_extracted for r in results)
            total_stored = sum(r.memories_stored for r in results)
            total_conflicts = sum(r.conflicts_found for r in results)
            
            print(f"\n{'='*60}")
            print(f"FOLDER COMPLETE: {len(results)} documents")
            print(f"  Total Facts: {total_facts}")
            print(f"  Total Stored: {total_stored}")
            print(f"  Total Conflicts: {total_conflicts}")
    else:
        for doc_path in paths:
            print(f"\n📄 Processing: {doc_path}")
            result = ingestor.ingest(doc_path)
            
            if result.errors:
                print(f"\n⚠️ Errors: {result.errors}")
    
    # Final note about conflicts
    try:
        from conflict_clarifier import ConflictQueue
    except ImportError:
        from openclaw.agents.ira.src.memory.conflict_clarifier import ConflictQueue
    
    queue = ConflictQueue()
    pending = queue.get_pending()
    
    if pending:
        print(f"\n{'='*60}")
        print(f"⚠️  {len(pending)} CONFLICTS PENDING REVIEW")
        print("="*60)
        print("\nUse Telegram commands to resolve:")
        print("  /conflicts - View all conflicts")
        print("  /resolve <id> <1|2|merge:text> - Resolve a conflict")
        print("\nOr run: python3 scripts/ingest_doc.py --send-conflicts")


if __name__ == "__main__":
    main()
