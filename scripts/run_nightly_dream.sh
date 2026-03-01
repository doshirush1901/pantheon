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
if [ -f "venv/bin/activate" ]; then
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
