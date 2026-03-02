#!/usr/bin/env python3
"""
Ingest Sales Playbook into IRA's Knowledge System
=================================================

Adds the ATHENA-trained sales conversation patterns to IRA's memory.

Usage:
    python scripts/ingest_sales_playbook.py
"""

import sys
import os
from pathlib import Path

# Add paths
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "openclaw" / "agents" / "ira"))

def main():
    """Ingest the sales playbook into IRA's knowledge."""
    
    playbook_path = PROJECT_ROOT / "data" / "knowledge" / "sales_playbook.md"
    
    if not playbook_path.exists():
        print(f"Error: Playbook not found at {playbook_path}")
        return 1
    
    print("=" * 60)
    print("INGESTING SALES PLAYBOOK INTO IRA'S KNOWLEDGE")
    print("=" * 60)
    
    playbook_content = playbook_path.read_text()
    
    # Try to use the knowledge ingestor
    try:
        from src.brain.knowledge_ingestor import KnowledgeIngestor
        
        ingestor = KnowledgeIngestor()
        
        # Split playbook into sections for better retrieval
        sections = playbook_content.split("\n## ")
        
        for i, section in enumerate(sections):
            if not section.strip():
                continue
            
            # Get section title
            lines = section.split("\n")
            title = lines[0].replace("#", "").strip()
            content = "\n".join(lines[1:]).strip()
            
            if len(content) < 50:
                continue
            
            print(f"\nIngesting section: {title}")
            
            ingestor.ingest(
                text=content,
                knowledge_type="sales_playbook",
                source_file="sales_playbook.md",
                metadata={
                    "section": title,
                    "source": "ATHENA training",
                    "category": "conversation_patterns"
                }
            )
            
        print("\n" + "=" * 60)
        print("INGESTION COMPLETE")
        print("=" * 60)
        
    except ImportError as e:
        print(f"Warning: Could not import KnowledgeIngestor: {e}")
        print("Playbook saved to data/knowledge/sales_playbook.md")
        print("IRA will read it via AGENTS.md reference")
    
    # Also print key stats
    print("\nSales Playbook Statistics:")
    print(f"  - Total characters: {len(playbook_content)}")
    print(f"  - Total lines: {len(playbook_content.splitlines())}")
    print(f"  - Location: {playbook_path}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
