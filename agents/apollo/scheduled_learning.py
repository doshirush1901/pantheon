#!/usr/bin/env python3
"""
SCHEDULED LEARNING JOB
======================

Run as a cron job or background process to continuously train Ira.

Modes:
1. Daily Learning - Run 5 simulations per day
2. Intensive Learning - Run many simulations for rapid improvement
3. Scenario Focus - Focus on specific weak areas

Usage:
    # Daily learning (add to crontab: 0 2 * * * ...)
    python scheduled_learning.py --daily
    
    # Intensive training
    python scheduled_learning.py --intensive --sessions 20
    
    # Focus on specific scenarios
    python scheduled_learning.py --focus price_negotiation --sessions 5
    
    # Review learning progress
    python scheduled_learning.py --report
"""

import os
import sys
import json
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "agents/apollo"))

from continuous_learning_loop import (
    run_learning_session, ScenarioType, REAL_SCENARIO_TEMPLATES,
    store_lesson
)


def get_learning_history() -> Dict:
    """Load all past learning sessions."""
    sessions_dir = PROJECT_ROOT / "data" / "learning_sessions"
    if not sessions_dir.exists():
        return {"sessions": [], "total_simulations": 0, "average_score": 0}
    
    sessions = []
    total_score = 0
    total_sims = 0
    
    for session_file in sorted(sessions_dir.glob("SESSION_*.json"), reverse=True):
        with open(session_file) as f:
            session = json.load(f)
            sessions.append(session)
            total_score += session.get("average_score", 0) * session.get("num_simulations", 0)
            total_sims += session.get("num_simulations", 0)
    
    return {
        "sessions": sessions,
        "total_simulations": total_sims,
        "average_score": total_score / total_sims if total_sims > 0 else 0,
    }


def get_weak_scenarios() -> List[ScenarioType]:
    """
    Analyze past sessions to find scenarios where Ira performs poorly.
    Returns scenarios that need more training.
    """
    sessions_dir = PROJECT_ROOT / "data" / "learning_sessions"
    if not sessions_dir.exists():
        return list(ScenarioType)  # All scenarios if no history
    
    scenario_scores = {}
    scenario_counts = {}
    
    for session_file in sessions_dir.glob("SESSION_*.json"):
        with open(session_file) as f:
            session = json.load(f)
            for conv in session.get("conversations", []):
                scenario = conv.get("scenario", "")
                score = conv.get("score", 0)
                
                if scenario not in scenario_scores:
                    scenario_scores[scenario] = 0
                    scenario_counts[scenario] = 0
                
                scenario_scores[scenario] += score
                scenario_counts[scenario] += 1
    
    # Calculate averages and find weak areas
    scenario_averages = {}
    for scenario, total in scenario_scores.items():
        count = scenario_counts.get(scenario, 1)
        scenario_averages[scenario] = total / count
    
    # Return scenarios with below-average performance
    if scenario_averages:
        avg_all = sum(scenario_averages.values()) / len(scenario_averages)
        weak_scenarios = [
            ScenarioType(s) for s, avg in scenario_averages.items()
            if avg < avg_all - 0.5 and s in [e.value for e in ScenarioType]
        ]
        return weak_scenarios if weak_scenarios else list(ScenarioType)[:3]
    
    return list(ScenarioType)


def generate_learning_report() -> str:
    """Generate a human-readable learning progress report."""
    
    history = get_learning_history()
    lessons_file = PROJECT_ROOT / "data" / "learned_lessons" / "continuous_learnings.json"
    
    lessons_count = 0
    sub_agent_counts = {}
    
    if lessons_file.exists():
        with open(lessons_file) as f:
            data = json.load(f)
            lessons_count = len(data.get("lessons", []))
            for agent, upgrades in data.get("sub_agent_upgrades", {}).items():
                sub_agent_counts[agent] = len(upgrades)
    
    report = []
    report.append("=" * 60)
    report.append("🎓 IRA CONTINUOUS LEARNING REPORT")
    report.append("=" * 60)
    report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    report.append("")
    
    report.append("📊 OVERALL METRICS")
    report.append("-" * 40)
    report.append(f"Total Simulations: {history['total_simulations']}")
    report.append(f"Average Score: {history['average_score']:.1f}/10")
    report.append(f"Lessons Learned: {lessons_count}")
    report.append(f"Learning Sessions: {len(history['sessions'])}")
    report.append("")
    
    report.append("🤖 SUB-AGENT UPGRADES")
    report.append("-" * 40)
    agent_names = {
        "athena": "Athena (Orchestrator)",
        "clio": "Clio (Researcher)",
        "calliope": "Calliope (Writer)",
        "vera": "Vera (Fact Checker)",
        "sophia": "Sophia (Mentor)",
    }
    for agent_key, name in agent_names.items():
        count = sub_agent_counts.get(agent_key, 0)
        if count > 0:
            report.append(f"  {name}: +{count} learnings")
    report.append("")
    
    # Recent sessions
    report.append("📅 RECENT SESSIONS")
    report.append("-" * 40)
    for session in history["sessions"][:5]:
        sid = session.get("session_id", "")
        score = session.get("average_score", 0)
        sims = session.get("num_simulations", 0)
        ts = session.get("timestamp", "")[:10]
        report.append(f"  {ts} | {sims} sims | Score: {score:.1f}/10")
    report.append("")
    
    # Weak areas
    weak = get_weak_scenarios()
    if weak:
        report.append("⚠️ AREAS NEEDING FOCUS")
        report.append("-" * 40)
        for scenario in weak[:3]:
            report.append(f"  • {scenario.value}")
    
    report.append("")
    report.append("=" * 60)
    
    return "\n".join(report)


def run_daily_learning():
    """Run daily learning routine - 5 simulations focusing on weak areas."""
    
    print("\n🌅 DAILY LEARNING ROUTINE")
    print("=" * 50)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    
    # Get weak scenarios to focus on
    weak_scenarios = get_weak_scenarios()
    print(f"Focus areas: {[s.value for s in weak_scenarios[:3]]}")
    
    # Run learning session
    run_learning_session(
        num_simulations=5,
        scenario_types=weak_scenarios[:3],
        verbose=False
    )
    
    # Generate and save report
    report = generate_learning_report()
    report_file = PROJECT_ROOT / "data" / "learning_reports" / f"daily_{datetime.now().strftime('%Y%m%d')}.txt"
    report_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(report_file, 'w') as f:
        f.write(report)
    
    print(f"\n📄 Report saved to: {report_file}")


def run_intensive_learning(num_sessions: int = 20):
    """Run intensive training with many simulations."""
    
    print("\n🚀 INTENSIVE LEARNING MODE")
    print("=" * 50)
    print(f"Target: {num_sessions} simulations")
    
    # Run in batches of 5
    batch_size = 5
    num_batches = (num_sessions + batch_size - 1) // batch_size
    
    for batch in range(num_batches):
        print(f"\n--- Batch {batch + 1}/{num_batches} ---")
        
        remaining = min(batch_size, num_sessions - batch * batch_size)
        run_learning_session(
            num_simulations=remaining,
            verbose=False
        )
        
        # Brief pause between batches
        if batch < num_batches - 1:
            print("Cooling down for 10 seconds...")
            time.sleep(10)
    
    print("\n✅ Intensive learning complete!")
    print(generate_learning_report())


def run_focused_learning(scenario_type: str, num_sessions: int = 5):
    """Focus learning on a specific scenario type."""
    
    try:
        scenario = ScenarioType(scenario_type)
    except ValueError:
        print(f"Unknown scenario type: {scenario_type}")
        print(f"Available: {[s.value for s in ScenarioType]}")
        return
    
    print(f"\n🎯 FOCUSED LEARNING: {scenario.value}")
    print("=" * 50)
    
    run_learning_session(
        num_simulations=num_sessions,
        scenario_types=[scenario],
        verbose=True
    )


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Scheduled Learning for Ira")
    parser.add_argument("--daily", action="store_true", help="Run daily learning routine")
    parser.add_argument("--intensive", action="store_true", help="Run intensive training")
    parser.add_argument("--focus", type=str, help="Focus on specific scenario type")
    parser.add_argument("--sessions", "-n", type=int, default=5, help="Number of simulations")
    parser.add_argument("--report", action="store_true", help="Generate learning report")
    
    args = parser.parse_args()
    
    if args.report:
        print(generate_learning_report())
    elif args.daily:
        run_daily_learning()
    elif args.intensive:
        run_intensive_learning(args.sessions)
    elif args.focus:
        run_focused_learning(args.focus, args.sessions)
    else:
        # Default: run a standard session
        run_learning_session(num_simulations=args.sessions)
