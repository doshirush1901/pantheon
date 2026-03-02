#!/bin/bash
#
# IRA NIGHTLY DREAM - Full Self-Learning Cycle
# =============================================
#
# This script runs Ira's complete "sleep learning" cycle:
# 1. Document extraction and knowledge storage
# 2. Knowledge graph consolidation (strengthen/weaken connections)
# 3. Episodic consolidation (patterns → semantic memories)
# 4. Price conflict detection
#
# Scheduled to run at 2 AM via launchd
#

set -e

# Configuration
IRA_DIR="/Users/rushabhdoshi/Desktop/Ira"
LOG_DIR="$IRA_DIR/logs"
PYTHON="/usr/bin/env python3"
DATE=$(date '+%Y-%m-%d')
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

# Ensure log directory exists
mkdir -p "$LOG_DIR"

# Log file for this run
DREAM_LOG="$LOG_DIR/dream_$DATE.log"

# Function to log with timestamp
log() {
    echo "[$TIMESTAMP] $1" | tee -a "$DREAM_LOG"
}

# Start
log "=============================================="
log "IRA NIGHTLY DREAM CYCLE STARTING"
log "=============================================="

cd "$IRA_DIR"

# Load environment
if [ -f ".env" ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Activate virtual environment if it exists
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
elif [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

# ==============================================================================
# PHASE 0: RUSHABH FEEDBACK (from chat log)
# ==============================================================================
log ""
log "📋 PHASE 0: Rushabh Feedback (from chat log)..."
log "----------------------------------------------"

$PYTHON scripts/process_rushabh_feedback.py 2>&1 | tee -a "$DREAM_LOG"

# ==============================================================================
# PHASE 0.5: CONSUME FEEDBACK BACKLOG + ERROR LOGS
# ==============================================================================
log ""
log "📝 PHASE 0.5: Processing feedback backlog and error logs..."
log "----------------------------------------------"

$PYTHON -c "
import sys, json, os
from pathlib import Path
from datetime import datetime

sys.path.insert(0, 'openclaw/agents/ira')
sys.path.insert(0, 'openclaw/agents/ira/src/brain')
sys.path.insert(0, 'openclaw/agents/ira/src/memory')

# 1. Process feedback backlog into correction learner
backlog = Path('data/chat_log/feedback_backlog.jsonl')
corrections_applied = 0
if backlog.exists():
    try:
        from correction_learner import CorrectionLearner
        cl = CorrectionLearner()
        for line in backlog.read_text().splitlines():
            if not line.strip():
                continue
            entry = json.loads(line)
            content = entry.get('content', '')
            if content:
                result = cl.detect_and_learn(content, '')
                if result.get('learned'):
                    corrections_applied += 1
        print(f'Feedback backlog: {corrections_applied} corrections applied')
    except Exception as e:
        print(f'Feedback backlog processing error: {e}')
else:
    print('No feedback backlog found (will be created after Telegram chats)')

# 2. Process error logs into knowledge gaps
errors_dir = Path('data/logs')
errors_today = 0
if errors_dir.exists():
    try:
        gaps_file = Path('data/knowledge_gaps.json')
        gaps = json.loads(gaps_file.read_text()) if gaps_file.exists() else []
        existing_topics = {g.get('topic', '') for g in gaps}

        for log_file in sorted(errors_dir.glob('errors_*.jsonl'))[-3:]:
            for line in log_file.read_text().splitlines():
                if not line.strip():
                    continue
                try:
                    entry = json.loads(line)
                    component = entry.get('component', '')
                    error_msg = str(entry.get('error', ''))
                    if 'retrieval' in component.lower() or 'knowledge' in error_msg.lower():
                        topic = entry.get('context', {}).get('query', error_msg[:100])
                        if topic and topic not in existing_topics:
                            gaps.append({
                                'topic': topic,
                                'source': 'error_log',
                                'detected': datetime.now().isoformat(),
                                'priority': 'medium',
                            })
                            existing_topics.add(topic)
                            errors_today += 1
                except json.JSONDecodeError:
                    pass

        gaps_file.parent.mkdir(parents=True, exist_ok=True)
        gaps_file.write_text(json.dumps(gaps, indent=2))
        print(f'Error logs: {errors_today} new knowledge gaps identified')
    except Exception as e:
        print(f'Error log processing error: {e}')

# 3. Process reflector lessons into dream context
lessons_file = Path('openclaw/agents/ira/data/lessons.md')
lesson_count = 0
if lessons_file.exists():
    content = lessons_file.read_text()
    lesson_count = content.count('- ')
    print(f'Reflector lessons available: {lesson_count} entries')
else:
    print('No reflector lessons file found yet')

print(f'Dream inputs ready: {corrections_applied} corrections, {errors_today} gaps, {lesson_count} lessons')
" 2>&1 | tee -a "$DREAM_LOG"

# ==============================================================================
# PHASE 1: DREAM MODE (Document Learning + Interaction Learning)
# ==============================================================================
log ""
log "🌙 PHASE 1: Dream Mode (Documents + Conversations)..."
log "----------------------------------------------"

$PYTHON -c "
import sys
sys.path.insert(0, 'openclaw/agents/ira/src/brain')
from dream_mode import IntegratedDreamMode

dream = IntegratedDreamMode()
result = dream.dream(force_all=False, deep_mode=False)

print(f'Documents processed: {result.get(\"documents_processed\", 0)}')
print(f'Facts learned: {result.get(\"facts_learned\", 0)}')
print(f'Qdrant indexed: {result.get(\"qdrant_indexed\", 0)}')
print(f'Insights generated: {result.get(\"insights_generated\", 0)}')

# Interaction learning results (from emails/Telegram)
interaction = result.get('interaction_learning', {})
if interaction:
    print(f'Conversation learnings: {interaction.get(\"stored\", 0)}')
    by_type = interaction.get('by_type', {})
    if by_type:
        print(f'  Corrections: {by_type.get(\"correction\", 0)}')
        print(f'  Facts: {by_type.get(\"fact\", 0)}')
        print(f'  Entity knowledge: {by_type.get(\"entity\", 0)}')
" 2>&1 | tee -a "$DREAM_LOG"

DREAM_EXIT=$?
if [ $DREAM_EXIT -ne 0 ]; then
    log "⚠️  Dream mode completed with warnings (exit code: $DREAM_EXIT)"
fi

# ==============================================================================
# PHASE 2: EPISODIC CONSOLIDATION (Patterns → Semantic Memories)
# ==============================================================================
log ""
log "🧠 PHASE 2: Episodic Consolidation..."
log "----------------------------------------------"

$PYTHON -c "
import sys
sys.path.insert(0, 'openclaw/agents/ira/src/memory')

try:
    from episodic_consolidator import run_consolidation
    
    result = run_consolidation(dry_run=False)
    
    print(f'Episodes analyzed: {result.episodes_analyzed}')
    print(f'Patterns found: {result.patterns_found}')
    print(f'Memories created: {result.memories_created}')
    print(f'Memories updated: {result.memories_updated}')
    
    if result.patterns:
        print('\\nTop patterns detected:')
        for p in result.patterns[:5]:
            print(f'  - [{p.get(\"type\", \"?\")}] {p.get(\"description\", \"?\")[:60]}...')
    
    if result.errors:
        print(f'\\nErrors: {result.errors}')
        
except ImportError as e:
    print(f'Episodic consolidation not available: {e}')
except Exception as e:
    print(f'Episodic consolidation error: {e}')
" 2>&1 | tee -a "$DREAM_LOG"

# ==============================================================================
# PHASE 3: KNOWLEDGE GRAPH CONSOLIDATION (Relationship Tuning)
# ==============================================================================
log ""
log "🔗 PHASE 3: Knowledge Graph Consolidation..."
log "----------------------------------------------"

$PYTHON -c "
import sys
sys.path.insert(0, 'openclaw/agents/ira/src/brain')

try:
    from graph_consolidation import GraphConsolidator
    
    consolidator = GraphConsolidator(verbose=True)
    result = consolidator.consolidate(days=1)
    
    print(f'Interactions analyzed: {result.interactions_analyzed}')
    print(f'Edges strengthened: {result.edges_strengthened}')
    print(f'Edges weakened: {result.edges_weakened}')
    print(f'Edges created: {result.edges_created}')
    print(f'Clusters reorganized: {result.clusters_reorganized}')
    
    if result.knowledge_gaps:
        print('\\nKnowledge gaps identified:')
        for gap in result.knowledge_gaps[:3]:
            print(f'  - {gap[:60]}...')
            
except ImportError as e:
    print(f'Graph consolidation not available: {e}')
except Exception as e:
    print(f'Graph consolidation error: {e}')
" 2>&1 | tee -a "$DREAM_LOG"

# ==============================================================================
# PHASE 4: MEMORY CLEANUP & OPTIMIZATION
# ==============================================================================
log ""
log "🧹 PHASE 4: Memory Cleanup..."
log "----------------------------------------------"

$PYTHON -c "
import sys
sys.path.insert(0, 'openclaw/agents/ira/src/memory')

try:
    from memory_intelligence import MemoryIntelligence
    
    mi = MemoryIntelligence()
    
    # Decay old memories
    decayed = mi.decay_old_memories(days=30)
    print(f'Memories decayed: {decayed}')
    
    # Archive very old memories
    archived = mi.archive_memories(days=180)
    print(f'Memories archived: {archived}')
    
except ImportError as e:
    print(f'Memory intelligence not available: {e}')
except Exception as e:
    print(f'Memory cleanup error: {e}')
" 2>&1 | tee -a "$DREAM_LOG"

# ==============================================================================
# PHASE 5: NEUROSCIENCE-INSPIRED PROCESSING
# ==============================================================================
log ""
log "🧬 PHASE 5: Neuroscience Dream Processing..."
log "----------------------------------------------"

$PYTHON -c "
import sys
sys.path.insert(0, 'openclaw/agents/ira/src/memory')

try:
    from dream_neuroscience import run_neuroscience_dream
    
    results = run_neuroscience_dream(verbose=True)
    
    # Summary
    sr = results.get('spaced_repetition', {})
    gaps = results.get('knowledge_gaps', {})
    insights = results.get('creative_insights', {})
    
    print()
    print('Neuroscience Dream Summary:')
    print(f'  Spaced Rep: {sr.get(\"total_memories\", 0)} memories tracked')
    print(f'  Knowledge Gaps: {gaps.get(\"total_gaps\", 0)} detected ({gaps.get(\"critical\", 0)} critical)')
    print(f'  Creative Insights: {insights.get(\"generated\", 0)} new connections')
    
except ImportError as e:
    print(f'Dream neuroscience not available: {e}')
except Exception as e:
    print(f'Neuroscience dream error: {e}')
    import traceback
    traceback.print_exc()
" 2>&1 | tee -a "$DREAM_LOG"

# ==============================================================================
# PHASE 6: ADVANCED DREAM FEATURES
# ==============================================================================
log ""
log "🎓 PHASE 6: Advanced Dream Processing..."
log "----------------------------------------------"

$PYTHON -c "
import sys
sys.path.insert(0, 'openclaw/agents/ira/src/memory')

try:
    from dream_advanced import run_advanced_dream
    
    # Run all advanced features
    results = run_advanced_dream(
        facts_learned=[],  # Will be populated from dream results
        patterns=[],
        insights=[],
        docs_processed=0,
        verbose=True,
    )
    
    # Summary
    print()
    print('Advanced Dream Summary:')
    print(f'  Memory Replay: {results.get(\"replay\", {}).get(\"conversations_replayed\", 0)} conversations')
    print(f'  Emotional Tags: {results.get(\"emotions\", {}).get(\"tagged\", 0)} interactions')
    print(f'  Schemas: {results.get(\"schemas\", {}).get(\"total\", 0)} mental models')
    print(f'  Self-Test: {results.get(\"self_test\", {}).get(\"score\", 0)}/{results.get(\"self_test\", {}).get(\"total\", 0)} correct')
    print(f'  Calibration: {results.get(\"calibration\", {}).get(\"score\", 0):.2f}')
    print(f'  Journal sent to Telegram: {results.get(\"telegram_sent\", False)}')
    
except ImportError as e:
    print(f'Advanced dream not available: {e}')
except Exception as e:
    print(f'Advanced dream error: {e}')
    import traceback
    traceback.print_exc()
" 2>&1 | tee -a "$DREAM_LOG"

# ==============================================================================
# PHASE 7: UNIFIED ORCHESTRATED DREAM (Phases 5-7 with inter-phase wiring)
# ==============================================================================
log ""
log "🎯 PHASE 7: Orchestrated Dream Processing (Unified Phases 5-7)..."
log "----------------------------------------------"
log "  This replaces individual Phases 5-7 with unified, wired processing"

$PYTHON -c "
import sys
sys.path.insert(0, 'openclaw/agents/ira/src/memory')

try:
    from dream_orchestrator import run_orchestrated_dream
    
    # Run orchestrated dream cycle (dry_run=False for real operations)
    # Set dry_run=True to simulate without actual deletions
    DRY_RUN = True  # Change to False for production
    
    results = run_orchestrated_dream(dry_run=DRY_RUN, verbose=True)
    
    # Summary
    ctx = results.get('context', {})
    metrics = results.get('metrics', {})
    
    print()
    print('=' * 50)
    print('ORCHESTRATED DREAM SUMMARY')
    print('=' * 50)
    print(f'  Total Duration: {metrics.get(\"total_duration_ms\", 0)}ms')
    print(f'  Phases Completed: {metrics.get(\"phases_completed\", 0)}')
    print()
    print('Phase 5 (Neuroscience):')
    print(f'  Creative Insights: {len(ctx.get(\"creative_insights\", []))}')
    print(f'  Knowledge Gaps: {len(ctx.get(\"knowledge_gaps\", []))} -> wired to Phase 6')
    print()
    print('Phase 6 (Advanced):')
    print(f'  Self-Test: {ctx.get(\"self_test_score\", 0)}/{ctx.get(\"self_test_total\", 0)} correct')
    print(f'  Calibration: {ctx.get(\"calibration_score\", 0):.2f}')
    print()
    print('Phase 7 (Experimental):')
    print(f'  Memories Deleted: {metrics.get(\"memories_deleted\", 0)} (dry_run={DRY_RUN})')
    print(f'  Conflicts Detected: {len(ctx.get(\"conflicts_detected\", []))}')
    print(f'  Counterfactual Readiness: {ctx.get(\"counterfactual_readiness\", 0):.0%}')
    
    if ctx.get('errors'):
        print()
        print('Errors:')
        for err in ctx.get('errors', [])[:3]:
            print(f'  - {err}')
    
except ImportError as e:
    print(f'Dream orchestrator not available: {e}')
    import traceback
    traceback.print_exc()
except Exception as e:
    print(f'Orchestrated dream error: {e}')
    import traceback
    traceback.print_exc()
" 2>&1 | tee -a "$DREAM_LOG"

# ==============================================================================
# PHASE 8: WAKE-UP HEALTH DIAGNOSTIC (Send to Telegram)
# ==============================================================================
log ""
log "🏥 PHASE 8: Wake-up Health Diagnostic..."
log "----------------------------------------------"

$PYTHON -c "
import sys, os, json, requests
from pathlib import Path
from datetime import datetime

sys.path.insert(0, 'openclaw/agents/ira')
sys.path.insert(0, 'openclaw/agents/ira/src/brain')
sys.path.insert(0, 'openclaw/agents/ira/src/memory')
sys.path.insert(0, 'openclaw/agents/ira/src/common')

PROJECT_ROOT = Path('.')
lines = ['🌅 <b>Good Morning! Ira is awake.</b>', '']

# Services
lines.append('<b>Services:</b>')
for name, check in [
    ('Qdrant', lambda: requests.get(os.environ.get('QDRANT_URL', 'http://localhost:6333'), timeout=5).status_code == 200),
    ('OpenAI', lambda: bool(os.environ.get('OPENAI_API_KEY'))),
    ('Voyage', lambda: bool(os.environ.get('VOYAGE_API_KEY'))),
    ('Mem0', lambda: bool(os.environ.get('MEM0_API_KEY'))),
]:
    try:
        ok = check()
        lines.append(f\"  {'✅' if ok else '❌'} {name}\")
    except:
        lines.append(f'  ❌ {name}')

# Knowledge health
try:
    from knowledge_health import run_health_check
    report = run_health_check()
    lines.append(f'')
    lines.append(f'<b>Knowledge Health:</b> {report.overall_score}/100')
    lines.append(f'  Passed: {report.checks_passed} | Failed: {report.checks_failed}')
    for issue in report.issues[:3]:
        icon = '🔴' if issue.severity == 'critical' else '🟡'
        lines.append(f'  {icon} {issue.message[:60]}')
except Exception as e:
    lines.append(f'Knowledge Health: unavailable')

# Knowledge gaps
try:
    gaps_file = PROJECT_ROOT / 'data' / 'knowledge_gaps.json'
    if gaps_file.exists():
        gaps = json.loads(gaps_file.read_text())
        gap_count = len(gaps) if isinstance(gaps, (list, dict)) else 0
        lines.append(f'')
        lines.append(f'<b>Knowledge Gaps:</b> {gap_count} topics need more data')
except:
    pass

# Agent scores
try:
    scores_file = PROJECT_ROOT / 'openclaw' / 'data' / 'learned_lessons' / 'agent_scores.json'
    if scores_file.exists():
        scores = json.loads(scores_file.read_text())
        lines.append(f'')
        lines.append(f'<b>Agent Performance:</b>')
        for agent, data in sorted(scores.items()):
            score = data.get('score', 0)
            s = data.get('successes', 0)
            f = data.get('failures', 0)
            bar = '█' * int(score * 10) + '░' * (10 - int(score * 10))
            lines.append(f'  {agent}: {bar} {score:.2f}')
except:
    pass

# Dream summary
try:
    dream_log = PROJECT_ROOT / 'logs' / f\"dream_{datetime.now().strftime('%Y-%m-%d')}.log\"
    if dream_log.exists():
        content = dream_log.read_text()
        facts_count = content.count('Facts:')
        lines.append(f'')
        lines.append(f'<b>Last Dream:</b> just completed')
        if 'Facts learned:' in content:
            import re
            m = re.search(r'Facts learned: (\d+)', content)
            if m:
                lines.append(f'  📄 Facts learned: {m.group(1)}')
        if 'Documents processed:' in content:
            m = re.search(r'Documents processed: (\d+)', content)
            if m:
                lines.append(f'  📁 Documents processed: {m.group(1)}')
except:
    pass

lines.append(f'')
lines.append(f'Type /health for full diagnostic.')
lines.append(f'Ready for the day! 🚀')

# Send to Telegram
message = chr(10).join(lines)
print(message)

bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
chat_id = os.environ.get('TELEGRAM_CHAT_ID') or os.environ.get('TELEGRAM_ADMIN_CHAT_ID')

if bot_token and chat_id:
    try:
        resp = requests.post(
            f'https://api.telegram.org/bot{bot_token}/sendMessage',
            json={'chat_id': chat_id, 'text': message, 'parse_mode': 'HTML'},
            timeout=10,
        )
        if resp.status_code == 200:
            print('✅ Wake-up diagnostic sent to Telegram')
        else:
            print(f'⚠️ Telegram send failed: {resp.text[:100]}')
    except Exception as e:
        print(f'⚠️ Telegram send error: {e}')
else:
    print('⚠️ Telegram not configured for wake-up message')
" 2>&1 | tee -a "$DREAM_LOG"

# ==============================================================================
# SUMMARY
# ==============================================================================
log ""
log "=============================================="
log "🌅 IRA DREAM CYCLE COMPLETE"
log "=============================================="
log "Log saved to: $DREAM_LOG"
log "Dashboard: data/dream_dashboard/index.html"
log "Results: data/dream_results/"

# Cleanup old logs (keep last 30 days)
find "$LOG_DIR" -name "dream_*.log" -mtime +30 -delete 2>/dev/null || true

exit 0
