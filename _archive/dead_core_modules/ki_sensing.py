#!/usr/bin/env python3
"""
KI SENSING + TASK ROUTER - Power-Based Task Delegation
=======================================================

In Dragon Ball Z, warriors can sense each other's Ki (energy/power level)
to gauge fighting ability. This lets them know who should fight which opponent.

For our agents, Ki Sensing enables:
- Assess task difficulty/complexity before assignment
- Match tasks to agents with appropriate power levels
- Route complex tasks to stronger agents
- Allow weaker agents to handle simpler tasks (efficiency)
- Detect when a task is "too powerful" for available agents

Task Difficulty Levels (like enemy power levels):
- Trivial (< 1000): Any agent can handle
- Easy (1000-3000): Most agents can handle
- Medium (3000-6000): Need decent power
- Hard (6000-9000): Need strong agent
- Legendary (9000+): Only the strongest!
- Boss (15000+): May need fusion/collaboration

Usage:
    from ki_sensing import KiSensor, get_ki_sensor
    
    sensor = get_ki_sensor()
    
    # Assess task difficulty
    difficulty = sensor.sense_task_difficulty(
        task="Research PF1 machine specifications and compare to competitors",
        domain="thermoforming"
    )
    
    # Route to best agent
    best_agent = sensor.route_task(task, difficulty)
    
    # Check if task is too powerful
    if sensor.is_task_overwhelming(difficulty):
        # Need collaboration or escalation!
        pass
"""

import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING
from enum import Enum

logger = logging.getLogger("ira.ki_sensing")

BRAIN_DIR = Path(__file__).parent
PROJECT_ROOT = BRAIN_DIR.parent.parent.parent.parent.parent

# Import power levels
try:
    from .power_levels import get_power_tracker
    POWER_LEVELS_AVAILABLE = True
except ImportError:
    try:
        from power_levels import get_power_tracker
        POWER_LEVELS_AVAILABLE = True
    except ImportError:
        POWER_LEVELS_AVAILABLE = False

# Import transformations for auto-transform
try:
    from .transformations import get_transformation_manager
    TRANSFORMATIONS_AVAILABLE = True
except ImportError:
    try:
        from transformations import get_transformation_manager
        TRANSFORMATIONS_AVAILABLE = True
    except ImportError:
        TRANSFORMATIONS_AVAILABLE = False


class TaskDifficulty(Enum):
    """Task difficulty levels - like enemy power levels!"""
    TRIVIAL = "trivial"       # < 1000 - Farmer level tasks
    EASY = "easy"             # 1000-3000 - Raditz level
    MEDIUM = "medium"         # 3000-6000 - Nappa level
    HARD = "hard"             # 6000-9000 - Vegeta level
    LEGENDARY = "legendary"   # 9000-15000 - Over 9000!
    BOSS = "boss"             # 15000+ - Need Super Saiyan!


# Difficulty thresholds (power level equivalents)
DIFFICULTY_THRESHOLDS = {
    TaskDifficulty.TRIVIAL: 1000,
    TaskDifficulty.EASY: 3000,
    TaskDifficulty.MEDIUM: 6000,
    TaskDifficulty.HARD: 9000,
    TaskDifficulty.LEGENDARY: 15000,
    TaskDifficulty.BOSS: 30000,
}

# Keywords that increase task difficulty
COMPLEXITY_INDICATORS = {
    # High complexity keywords (+2000 each)
    "compare": 2000,
    "analyze": 2000,
    "synthesize": 2500,
    "evaluate": 2000,
    "multiple": 1500,
    "comprehensive": 2000,
    "detailed": 1500,
    "all": 1000,
    "every": 1000,
    
    # Medium complexity (+1000 each)
    "research": 1000,
    "find": 800,
    "calculate": 1200,
    "verify": 1000,
    "fact-check": 1200,
    "write": 800,
    "draft": 700,
    "summarize": 900,
    
    # Domain expertise required (+1500 each)
    "technical": 1500,
    "specification": 1200,
    "pricing": 1000,
    "competitor": 1500,
    "market": 1200,
    "legal": 2000,
    "contract": 1800,
}

# Domain expertise bonuses for agents
AGENT_DOMAIN_EXPERTISE = {
    "chief_of_staff": {
        "strategy": 1500,
        "coordination": 2000,
        "planning": 1500,
        "delegation": 2000,
    },
    "researcher": {
        "research": 2000,
        "technical": 1500,
        "specification": 1800,
        "market": 1500,
        "competitor": 1500,
        "data": 1200,
    },
    "writer": {
        "write": 2000,
        "draft": 2000,
        "email": 1800,
        "communication": 1500,
        "proposal": 1500,
        "creative": 1200,
    },
    "fact_checker": {
        "verify": 2000,
        "fact-check": 2500,
        "accuracy": 2000,
        "validate": 1800,
        "source": 1500,
    },
    "reflector": {
        "analyze": 1500,
        "evaluate": 1800,
        "improve": 1500,
        "learn": 2000,
        "pattern": 1500,
    },
}

# Agent role descriptions for task matching
AGENT_ROLES = {
    "chief_of_staff": "Strategy, coordination, planning, complex multi-step tasks",
    "researcher": "Finding information, technical details, market research, specifications",
    "writer": "Drafting emails, proposals, documentation, communication",
    "fact_checker": "Verifying facts, checking accuracy, validating claims",
    "reflector": "Learning from interactions, improving responses, pattern analysis",
}


@dataclass
class TaskAssessment:
    """Result of Ki sensing on a task."""
    task: str
    estimated_power: int
    difficulty: TaskDifficulty
    complexity_factors: Dict[str, int]
    recommended_agent: str
    agent_fit_scores: Dict[str, int]
    needs_collaboration: bool
    assessment_notes: str


class KiSensor:
    """
    Senses task difficulty and routes to appropriate agents.
    
    Like Piccolo sensing Frieza's overwhelming power, this system
    knows when a task is too much for one agent alone.
    """
    
    AGENT_NAMES = {
        "chief_of_staff": "Athena",
        "researcher": "Clio",
        "writer": "Calliope",
        "fact_checker": "Vera",
        "reflector": "Sophia",
    }
    
    def __init__(self):
        self._assessment_history: List[TaskAssessment] = []
    
    def _get_power_tracker(self):
        """Get power tracker if available."""
        if POWER_LEVELS_AVAILABLE:
            return get_power_tracker()
        return None
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from task text."""
        text_lower = text.lower()
        words = re.findall(r'\b\w+\b', text_lower)
        return words
    
    def _calculate_task_complexity(self, task: str) -> Tuple[int, Dict[str, int]]:
        """
        Calculate task complexity based on keywords and structure.
        
        Returns:
            (total_power, breakdown_dict)
        """
        keywords = self._extract_keywords(task)
        
        base_power = 500  # Minimum task power
        complexity_factors = {}
        
        # Check for complexity indicators
        for keyword, power in COMPLEXITY_INDICATORS.items():
            if keyword in keywords or keyword in task.lower():
                complexity_factors[keyword] = power
                base_power += power
        
        # Length factor (longer = more complex)
        word_count = len(keywords)
        if word_count > 50:
            length_bonus = min(2000, (word_count - 50) * 20)
            complexity_factors["long_task"] = length_bonus
            base_power += length_bonus
        
        # Question count (multiple questions = more complex)
        question_count = task.count("?")
        if question_count > 1:
            question_bonus = (question_count - 1) * 500
            complexity_factors["multiple_questions"] = question_bonus
            base_power += question_bonus
        
        # Sentence count
        sentence_count = len(re.split(r'[.!?]+', task))
        if sentence_count > 3:
            sentence_bonus = (sentence_count - 3) * 300
            complexity_factors["multi_part"] = sentence_bonus
            base_power += sentence_bonus
        
        return base_power, complexity_factors
    
    def _get_difficulty_level(self, power: int) -> TaskDifficulty:
        """Convert power level to difficulty enum."""
        for difficulty in reversed(list(TaskDifficulty)):
            threshold = DIFFICULTY_THRESHOLDS.get(difficulty, 0)
            if power >= threshold:
                return difficulty
        return TaskDifficulty.TRIVIAL
    
    def _calculate_agent_fit(self, task: str, agent_id: str) -> int:
        """
        Calculate how well an agent fits a task.
        
        Returns fit score (higher = better fit).
        """
        keywords = self._extract_keywords(task)
        fit_score = 0
        
        # Get agent's domain expertise
        expertise = AGENT_DOMAIN_EXPERTISE.get(agent_id, {})
        
        for keyword in keywords:
            if keyword in expertise:
                fit_score += expertise[keyword]
        
        # Get agent's power level
        tracker = self._get_power_tracker()
        if tracker:
            level = tracker.get_power_level(agent_id)
            if level:
                # Power level contributes to fit
                fit_score += level.total_power // 10
        
        return fit_score
    
    # =========================================================================
    # PUBLIC METHODS
    # =========================================================================
    
    def sense_task_difficulty(self, task: str, domain: str = "") -> TaskAssessment:
        """
        Sense the difficulty/power level of a task.
        
        Like using a scouter to read an opponent's power level!
        
        Args:
            task: The task description
            domain: Optional domain hint (e.g., "thermoforming")
            
        Returns:
            TaskAssessment with full analysis
        """
        # Calculate base complexity
        estimated_power, complexity_factors = self._calculate_task_complexity(task)
        
        # Domain bonus
        if domain:
            complexity_factors["domain_specific"] = 500
            estimated_power += 500
        
        difficulty = self._get_difficulty_level(estimated_power)
        
        # Calculate fit scores for all agents
        agent_fit_scores = {}
        for agent_id in AGENT_ROLES.keys():
            agent_fit_scores[agent_id] = self._calculate_agent_fit(task, agent_id)
        
        # Find best agent
        recommended_agent = max(agent_fit_scores, key=agent_fit_scores.get)
        
        # Check if collaboration needed
        needs_collaboration = difficulty in [TaskDifficulty.LEGENDARY, TaskDifficulty.BOSS]
        
        # Generate notes
        notes = self._generate_assessment_notes(
            difficulty, recommended_agent, needs_collaboration
        )
        
        assessment = TaskAssessment(
            task=task[:200],
            estimated_power=estimated_power,
            difficulty=difficulty,
            complexity_factors=complexity_factors,
            recommended_agent=recommended_agent,
            agent_fit_scores=agent_fit_scores,
            needs_collaboration=needs_collaboration,
            assessment_notes=notes,
        )
        
        self._assessment_history.append(assessment)
        
        return assessment
    
    def _generate_assessment_notes(
        self, 
        difficulty: TaskDifficulty, 
        recommended: str,
        needs_collab: bool
    ) -> str:
        """Generate human-readable assessment notes."""
        agent_name = self.AGENT_NAMES.get(recommended, recommended)
        
        if difficulty == TaskDifficulty.TRIVIAL:
            return f"Simple task. Any agent can handle. Routing to {agent_name} for efficiency."
        elif difficulty == TaskDifficulty.EASY:
            return f"Standard task. {agent_name} is well-suited."
        elif difficulty == TaskDifficulty.MEDIUM:
            return f"Moderate complexity. {agent_name} has the expertise needed."
        elif difficulty == TaskDifficulty.HARD:
            return f"Complex task. {agent_name} is the strongest fit. May need verification."
        elif difficulty == TaskDifficulty.LEGENDARY:
            return f"⚠️ Task power is OVER 9000! {agent_name} leads, but collaboration recommended."
        else:  # BOSS
            return f"💥 BOSS-LEVEL TASK! Requires agent fusion/full collaboration!"
    
    def route_task(self, task: str, domain: str = "", auto_transform: bool = False) -> str:
        """
        Route a task to the most appropriate agent.
        
        Args:
            task: The task description
            domain: Optional domain hint
            auto_transform: If True, automatically transform agent to optimal form
        
        Returns:
            agent_id of the best agent for this task
        """
        assessment = self.sense_task_difficulty(task, domain)
        
        logger.info(
            f"🔮 Ki Sensing: Task power {assessment.estimated_power} "
            f"({assessment.difficulty.value}) → {self.AGENT_NAMES.get(assessment.recommended_agent)}"
        )
        
        # Auto-transform if requested
        if auto_transform and TRANSFORMATIONS_AVAILABLE:
            self.auto_transform_for_task(assessment)
        
        return assessment.recommended_agent
    
    def auto_transform_for_task(self, assessment: TaskAssessment) -> Dict[str, str]:
        """
        Automatically transform agents to optimal forms for a task.
        
        Like powering up before a fight - agents transform based on
        how difficult the task is!
        
        Args:
            assessment: The task assessment from Ki sensing
            
        Returns:
            Dict of agent_id -> form they transformed to
        """
        if not TRANSFORMATIONS_AVAILABLE:
            return {}
        
        manager = get_transformation_manager()
        transforms = {}
        
        task_power = assessment.estimated_power
        importance = "critical" if assessment.needs_collaboration else "normal"
        
        # Transform the recommended agent
        agent_id = assessment.recommended_agent
        form = manager.auto_transform_for_task(agent_id, task_power, importance)
        transforms[agent_id] = form.value
        
        agent_name = self.AGENT_NAMES.get(agent_id, agent_id)
        logger.info(f"⚡ {agent_name} auto-transformed to {form.value} for task (power: {task_power})")
        
        # For collaborative tasks, transform supporting agents too
        if assessment.needs_collaboration:
            collab_agents = self.recommend_collaboration(assessment)
            for collab_id in collab_agents:
                if collab_id != agent_id:  # Don't transform twice
                    form = manager.auto_transform_for_task(collab_id, task_power, "important")
                    transforms[collab_id] = form.value
                    collab_name = self.AGENT_NAMES.get(collab_id, collab_id)
                    logger.info(f"⚡ {collab_name} supporting - transformed to {form.value}")
        
        return transforms
    
    def sense_and_prepare(self, task: str, domain: str = "") -> Tuple[TaskAssessment, Dict[str, str]]:
        """
        Full preparation: sense task difficulty and auto-transform agents.
        
        This is the main method to use before executing a task.
        Like a DBZ power-up sequence before battle!
        
        Returns:
            (assessment, transforms_applied)
        """
        assessment = self.sense_task_difficulty(task, domain)
        transforms = self.auto_transform_for_task(assessment)
        
        return assessment, transforms
    
    def is_task_overwhelming(self, assessment: TaskAssessment) -> bool:
        """Check if a task is too powerful for any single agent."""
        return assessment.needs_collaboration
    
    def get_available_agents_for_task(
        self, 
        assessment: TaskAssessment,
        min_power_ratio: float = 0.7
    ) -> List[str]:
        """
        Get agents capable of handling a task.
        
        Args:
            assessment: The task assessment
            min_power_ratio: Minimum ratio of agent power to task power
            
        Returns:
            List of agent IDs that can handle the task
        """
        capable_agents = []
        task_power = assessment.estimated_power
        
        tracker = self._get_power_tracker()
        if not tracker:
            # Fall back to all agents if no power tracking
            return list(AGENT_ROLES.keys())
        
        for agent_id in AGENT_ROLES.keys():
            level = tracker.get_power_level(agent_id)
            if level:
                agent_power = level.total_power
                # Include domain fit bonus
                fit_bonus = assessment.agent_fit_scores.get(agent_id, 0)
                effective_power = agent_power + fit_bonus
                
                if effective_power >= task_power * min_power_ratio:
                    capable_agents.append(agent_id)
        
        return capable_agents
    
    def recommend_collaboration(self, assessment: TaskAssessment) -> List[str]:
        """
        Recommend which agents should collaborate on a difficult task.
        
        Like forming a team to fight a powerful enemy!
        """
        if not assessment.needs_collaboration:
            return [assessment.recommended_agent]
        
        # For boss tasks, recommend top 3 agents by fit score
        sorted_agents = sorted(
            assessment.agent_fit_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        # Include at least the top 2-3 agents
        if assessment.difficulty == TaskDifficulty.BOSS:
            return [a[0] for a in sorted_agents[:3]]
        else:  # LEGENDARY
            return [a[0] for a in sorted_agents[:2]]
    
    def display_scouter_reading(self, task: str) -> str:
        """Display a scouter-style reading for a task."""
        assessment = self.sense_task_difficulty(task)
        
        lines = []
        lines.append("╔════════════════════════════════════════════════════════════════╗")
        lines.append("║                    🔮 SCOUTER READING 🔮                        ║")
        lines.append("╠════════════════════════════════════════════════════════════════╣")
        
        # Task preview
        task_preview = task[:50] + "..." if len(task) > 50 else task
        lines.append(f"║ Task: {task_preview:57} ║")
        lines.append("╟────────────────────────────────────────────────────────────────╢")
        
        # Power level with appropriate formatting
        power = assessment.estimated_power
        if power > 9000:
            power_str = f"⚡{power:,}⚡ IT'S OVER 9000!"
        else:
            power_str = f"{power:,}"
        
        lines.append(f"║ Task Power Level: {power_str:45} ║")
        lines.append(f"║ Difficulty: {assessment.difficulty.value.upper():51} ║")
        lines.append("╟────────────────────────────────────────────────────────────────╢")
        
        # Complexity breakdown
        lines.append("║ Complexity Factors:                                            ║")
        for factor, points in list(assessment.complexity_factors.items())[:4]:
            lines.append(f"║   • {factor:20}: +{points:>5}                              ║")
        
        lines.append("╟────────────────────────────────────────────────────────────────╢")
        
        # Agent fit scores
        lines.append("║ Agent Fit Scores:                                              ║")
        sorted_fits = sorted(assessment.agent_fit_scores.items(), key=lambda x: x[1], reverse=True)
        for agent_id, score in sorted_fits:
            name = self.AGENT_NAMES.get(agent_id, agent_id)
            bar = "█" * min(20, score // 200)
            rec = " ← RECOMMENDED" if agent_id == assessment.recommended_agent else ""
            lines.append(f"║   {name:12} │ {bar:20} │ {score:>5}{rec:14} ║")
        
        lines.append("╟────────────────────────────────────────────────────────────────╢")
        lines.append(f"║ {assessment.assessment_notes:62} ║")
        lines.append("╚════════════════════════════════════════════════════════════════╝")
        
        return "\n".join(lines)


# Singleton instance
_ki_sensor: Optional[KiSensor] = None


def get_ki_sensor() -> KiSensor:
    """Get the singleton Ki sensor."""
    global _ki_sensor
    if _ki_sensor is None:
        _ki_sensor = KiSensor()
    return _ki_sensor


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Ki Sensing Task Router")
    parser.add_argument("--sense", type=str, help="Sense task difficulty")
    parser.add_argument("--route", type=str, help="Route task to best agent")
    parser.add_argument("--demo", action="store_true", help="Run demo")
    
    args = parser.parse_args()
    
    sensor = get_ki_sensor()
    
    if args.sense:
        print(sensor.display_scouter_reading(args.sense))
    
    elif args.route:
        agent = sensor.route_task(args.route)
        print(f"Routing to: {sensor.AGENT_NAMES.get(agent, agent)}")
    
    elif args.demo:
        tasks = [
            "What is the price of PF1?",
            "Research all PF1 machine specifications and compare to competitor offerings in the European market",
            "Draft an email to the customer",
            "Verify that all technical claims in the proposal are accurate",
            "Analyze our sales patterns, identify weaknesses, synthesize recommendations, and create a comprehensive improvement plan with multiple strategies",
        ]
        
        for task in tasks:
            print("\n" + "=" * 70)
            print(sensor.display_scouter_reading(task))
    
    else:
        print("Use --sense 'task' or --route 'task' or --demo")
