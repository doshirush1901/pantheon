# Ira Backup Automation

## Quick Start

### Manual Backup
```bash
cd /Users/rushabhdoshi/Desktop/Ira
python scripts/backup_data.py -v
```

### Install Scheduled Backup (macOS)

1. **Copy the launchd plist:**
```bash
cp scripts/com.ira.backup.plist ~/Library/LaunchAgents/
```

2. **Load the backup job:**
```bash
launchctl load ~/Library/LaunchAgents/com.ira.backup.plist
```

3. **Verify it's loaded:**
```bash
launchctl list | grep ira.backup
```

### Run Backup Now (test)
```bash
launchctl start com.ira.backup
```

### Check Logs
```bash
tail -f logs/backup.log
tail -f logs/backup_error.log
```

### Uninstall
```bash
launchctl unload ~/Library/LaunchAgents/com.ira.backup.plist
rm ~/Library/LaunchAgents/com.ira.backup.plist
```

## Schedule

By default, backups run **daily at 3:00 AM**.

To change the schedule, edit the plist file:
```xml
<key>StartCalendarInterval</key>
<dict>
    <key>Hour</key>
    <integer>3</integer>
    <key>Minute</key>
    <integer>0</integer>
</dict>
```

For example, to run every 6 hours:
```xml
<key>StartInterval</key>
<integer>21600</integer>
```

## What Gets Backed Up

### JSON Files
- `data/knowledge/ingested_hashes.json`
- `data/knowledge/knowledge_graph.json`
- `data/knowledge/price_index.json`
- `data/knowledge/price_conflicts.json`
- `data/knowledge/clusters.json`
- `data/identities.json`
- `data/qualification_states.json`

### SQLite Databases
- `data/unified_identity.db`
- `crm/relationships.db`
- `crm/learned_knowledge.db`
- `crm/memory_analytics.db`
- `crm/cache/embedding_cache.db`

### JSONL Logs
- `data/knowledge/audit.jsonl`
- `data/knowledge/retrieval_log.jsonl`
- `crm/logs/requests.jsonl`

## Backup Location

Backups are stored in `/Users/rushabhdoshi/Desktop/Ira/backups/`:
```
backups/
├── json/
│   ├── price_index_20240227_030000.json
│   ├── knowledge_graph_20240227_030000.json
│   └── ...
├── sqlite/
│   ├── unified_identity_20240227_030000.db
│   ├── relationships_20240227_030000.db
│   └── ...
└── jsonl/
    ├── audit_20240227_030000.jsonl
    └── ...
```

## Retention

By default, keeps the **5 most recent** backups per file.

To change, edit `backup_data.py` or pass `--max-backups N`.

## Restore

To restore from backup:
```bash
# SQLite (safest - use SQLite backup API)
sqlite3 data/unified_identity.db ".restore backups/sqlite/unified_identity_TIMESTAMP.db"

# JSON (simple copy)
cp backups/json/price_index_TIMESTAMP.json data/knowledge/price_index.json
```
