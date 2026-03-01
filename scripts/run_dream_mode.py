#!/usr/bin/env python3
"""
RUN DREAM MODE - Nightly Learning Scheduler
============================================

Run this script nightly to have Ira "dream" - scanning all documents
and updating her knowledge base.

Schedule with cron:
    # Run at 2 AM every day
    0 2 * * * cd /path/to/Ira && python scripts/run_dream_mode.py >> logs/dream.log 2>&1

Or run manually:
    python scripts/run_dream_mode.py
    python scripts/run_dream_mode.py --force  # Reprocess all docs
"""

import os
import sys
from pathlib import Path
from datetime import datetime

# Setup
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Load env
for line in (PROJECT_ROOT / ".env").read_text().splitlines():
    if line.strip() and not line.startswith('#') and '=' in line:
        key, _, value = line.partition('=')
        os.environ[key.strip()] = value.strip().strip('"')

sys.path.insert(0, str(PROJECT_ROOT / "openclaw/agents/ira/src/brain"))

from dream_mode import DreamMode

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Run Ira's Dream Mode")
    parser.add_argument("--force", action="store_true", help="Reprocess all documents")
    parser.add_argument("--status", action="store_true", help="Show current status")
    args = parser.parse_args()
    
    print(f"\n{'='*60}")
    print(f"IRA DREAM MODE - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")
    
    dream = DreamMode()
    
    if args.status:
        print(f"\nLast dream: {dream.state.last_dream or 'Never'}")
        print(f"Documents processed: {len(dream.state.documents_processed)}")
        print(f"Total facts learned: {dream.state.total_facts_learned}")
        print(f"Topics: {len(dream.state.topics_covered)}")
    else:
        result = dream.dream(force_all=args.force)
        
        print(f"\n✓ Dream complete!")
        print(f"  Documents: {result['documents_processed']}")
        print(f"  Facts learned: {result['facts_learned']}")
