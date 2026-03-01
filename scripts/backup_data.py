#!/usr/bin/env python3
"""
Ira Data Backup Script
======================

Automated backup script for Ira's data files.
Can be run manually or scheduled via cron/launchd.

Usage:
    python backup_data.py                    # Full backup
    python backup_data.py --json-only        # JSON files only
    python backup_data.py --sqlite-only      # SQLite databases only
    python backup_data.py --max-backups 10   # Keep 10 backups per file
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "openclaw" / "agents" / "ira"))

try:
    from config import (
        backup_all_data,
        backup_file,
        backup_sqlite_db,
        BACKUP_DIR,
        PROJECT_ROOT as CONFIG_ROOT,
        get_logger,
    )
    CONFIG_AVAILABLE = True
except ImportError as e:
    print(f"Error: Could not import config module: {e}")
    print("Make sure you're running from the Ira project directory")
    sys.exit(1)

logger = get_logger("backup_script")


def run_backup(
    include_json: bool = True,
    include_sqlite: bool = True,
    include_jsonl: bool = True,
    max_backups: int = 5,
    verbose: bool = False
) -> dict:
    """
    Run backup of all Ira data files.
    
    Args:
        include_json: Backup JSON files
        include_sqlite: Backup SQLite databases
        include_jsonl: Backup JSONL log files
        max_backups: Maximum backups to keep per file
        verbose: Print detailed output
    
    Returns:
        Dict with backup results
    """
    start_time = datetime.now()
    
    if verbose:
        print(f"Starting backup at {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Backup directory: {BACKUP_DIR}")
        print("-" * 50)
    
    results = backup_all_data(
        include_json=include_json,
        include_sqlite=include_sqlite,
        include_jsonl=include_jsonl,
    )
    
    elapsed = (datetime.now() - start_time).total_seconds()
    
    # Summary
    total_files = sum(len(v) for v in results.values())
    
    if verbose:
        print("-" * 50)
        print(f"Backup complete in {elapsed:.1f}s")
        print(f"  JSON files:   {len(results.get('json', []))}")
        print(f"  SQLite DBs:   {len(results.get('sqlite', []))}")
        print(f"  JSONL logs:   {len(results.get('jsonl', []))}")
        print(f"  Total:        {total_files}")
        
        if results.get('json'):
            print("\nJSON backups:")
            for p in results['json']:
                print(f"  ✓ {p.name}")
        
        if results.get('sqlite'):
            print("\nSQLite backups:")
            for p in results['sqlite']:
                print(f"  ✓ {p.name}")
    
    logger.info(f"Backup completed: {total_files} files in {elapsed:.1f}s")
    
    return {
        "success": True,
        "total_files": total_files,
        "elapsed_seconds": elapsed,
        "results": results,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Backup Ira data files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python backup_data.py                    # Full backup
    python backup_data.py --json-only        # JSON files only
    python backup_data.py --sqlite-only      # SQLite databases only
    python backup_data.py -v                 # Verbose output
        """
    )
    
    parser.add_argument(
        "--json-only",
        action="store_true",
        help="Only backup JSON files"
    )
    parser.add_argument(
        "--sqlite-only",
        action="store_true",
        help="Only backup SQLite databases"
    )
    parser.add_argument(
        "--jsonl-only",
        action="store_true",
        help="Only backup JSONL log files"
    )
    parser.add_argument(
        "--max-backups",
        type=int,
        default=5,
        help="Maximum backups to keep per file (default: 5)"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output"
    )
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Quiet mode - only print errors"
    )
    
    args = parser.parse_args()
    
    # Determine what to backup
    if args.json_only:
        include_json, include_sqlite, include_jsonl = True, False, False
    elif args.sqlite_only:
        include_json, include_sqlite, include_jsonl = False, True, False
    elif args.jsonl_only:
        include_json, include_sqlite, include_jsonl = False, False, True
    else:
        include_json, include_sqlite, include_jsonl = True, True, True
    
    try:
        result = run_backup(
            include_json=include_json,
            include_sqlite=include_sqlite,
            include_jsonl=include_jsonl,
            max_backups=args.max_backups,
            verbose=args.verbose and not args.quiet,
        )
        
        if not args.quiet:
            print(f"\n✓ Backup successful: {result['total_files']} files")
        
        return 0
        
    except Exception as e:
        logger.error(f"Backup failed: {e}")
        if not args.quiet:
            print(f"\n✗ Backup failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
