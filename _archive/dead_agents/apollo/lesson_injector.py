#!/usr/bin/env python3
"""
LESSON INJECTOR
===============

Injects learned lessons into Ira's response generation.

This module:
1. Loads all lessons from continuous learning
2. Matches incoming queries to relevant lessons
3. Injects guidance into Ira's system prompt
4. Tracks which lessons are being applied

The goal: Make Ira actually use what she learned from simulations.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
import re

PROJECT_ROOT = Path(__file__).parent.parent.parent
LESSONS_FILE = PROJECT_ROOT / "data" / "learned_lessons" / "continuous_learnings.json"
STRESS_TEST_LESSONS = PROJECT_ROOT / "data" / "learned_lessons" / "stress_test_learnings_2026_02_28.json"


class LessonInjector:
    """Injects learned lessons into Ira's responses."""
    
    def __init__(self):
        self.lessons: List[Dict] = []
        self.sub_agent_upgrades: Dict[str, List[Dict]] = {}
        self.lesson_applications: Dict[str, int] = {}  # Track usage
        self._load_lessons()
    
    def _load_lessons(self):
        """Load all lessons from all sources."""
        
        # Load continuous learnings
        if LESSONS_FILE.exists():
            with open(LESSONS_FILE) as f:
                data = json.load(f)
                self.lessons.extend(data.get("lessons", []))
                for agent, upgrades in data.get("sub_agent_upgrades", {}).items():
                    if agent not in self.sub_agent_upgrades:
                        self.sub_agent_upgrades[agent] = []
                    self.sub_agent_upgrades[agent].extend(upgrades)
        
        # Load stress test learnings
        if STRESS_TEST_LESSONS.exists():
            with open(STRESS_TEST_LESSONS) as f:
                data = json.load(f)
                self.lessons.extend(data.get("lessons_learned", []))
        
        print(f"[LessonInjector] Loaded {len(self.lessons)} lessons")
    
    def get_relevant_lessons(self, query: str, top_n: int = 3) -> List[Dict]:
        """
        Find lessons relevant to the current query.
        Uses keyword matching and category matching.
        """
        
        query_lower = query.lower()
        scored_lessons = []
        
        for lesson in self.lessons:
            score = 0
            
            # Check trigger match
            trigger = lesson.get("trigger", "").lower()
            if trigger:
                trigger_words = set(trigger.split())
                query_words = set(query_lower.split())
                overlap = trigger_words.intersection(query_words)
                score += len(overlap) * 2
            
            # Check category relevance
            category = lesson.get("category", "").lower()
            if category:
                category_keywords = {
                    "communication": ["help", "explain", "detail", "question"],
                    "qualification": ["need", "want", "looking", "require"],
                    "technical": ["spec", "size", "material", "temperature", "thickness"],
                    "pricing": ["price", "cost", "budget", "quote", "expensive"],
                    "urgency": ["urgent", "asap", "quickly", "deadline", "rush"],
                }
                for cat_key, keywords in category_keywords.items():
                    if cat_key in category:
                        for kw in keywords:
                            if kw in query_lower:
                                score += 1
            
            # Business rule keywords
            if any(kw in query_lower for kw in ["mm", "thick", "material"]):
                if "thickness" in lesson.get("lesson", "").lower():
                    score += 3
            
            if any(kw in query_lower for kw in ["img", "grain", "tpo", "texture"]):
                if "img" in lesson.get("lesson", "").lower():
                    score += 3
            
            if score > 0:
                scored_lessons.append((score, lesson))
        
        # Sort by score and return top N
        scored_lessons.sort(key=lambda x: x[0], reverse=True)
        return [lesson for _, lesson in scored_lessons[:top_n]]
    
    def generate_lesson_prompt(self, query: str) -> str:
        """
        Generate a prompt injection with relevant lessons.
        This gets added to Ira's system prompt.
        """
        
        relevant_lessons = self.get_relevant_lessons(query)
        
        if not relevant_lessons:
            return ""
        
        prompt_parts = [
            "\n\n--- LEARNED LESSONS (Apply These) ---",
        ]
        
        for i, lesson in enumerate(relevant_lessons, 1):
            lesson_id = lesson.get("id", f"LESSON_{i}")
            self.lesson_applications[lesson_id] = self.lesson_applications.get(lesson_id, 0) + 1
            
            prompt_parts.append(f"""
LESSON {i}: {lesson.get('lesson', 'N/A')}
• Trigger: {lesson.get('trigger', 'N/A')}
• Correct Action: {lesson.get('correct_action', 'N/A')}
• Avoid: {lesson.get('incorrect_action', 'N/A')}
""")
        
        prompt_parts.append("--- End of Lessons ---\n")
        
        return "\n".join(prompt_parts)
    
    def get_sub_agent_guidance(self, agent_name: str) -> str:
        """
        Get accumulated guidance for a specific sub-agent.
        """
        
        agent_key = agent_name.lower()
        upgrades = self.sub_agent_upgrades.get(agent_key, [])
        
        if not upgrades:
            return ""
        
        # Get unique feedback items
        seen = set()
        unique_feedback = []
        for upgrade in upgrades:
            feedback = upgrade.get("feedback", "")
            if feedback and feedback not in seen:
                seen.add(feedback)
                unique_feedback.append(feedback)
        
        if not unique_feedback:
            return ""
        
        guidance = f"\n\n--- {agent_name.upper()} LEARNINGS ---\n"
        for i, feedback in enumerate(unique_feedback[:5], 1):  # Max 5
            guidance += f"{i}. {feedback}\n"
        guidance += "--- End ---\n"
        
        return guidance
    
    def get_usage_stats(self) -> Dict:
        """Get statistics on lesson usage."""
        return {
            "total_lessons": len(self.lessons),
            "lesson_applications": self.lesson_applications,
            "sub_agent_categories": list(self.sub_agent_upgrades.keys()),
        }


# Global instance
_injector: Optional[LessonInjector] = None

def get_injector() -> LessonInjector:
    """Get or create the global LessonInjector instance."""
    global _injector
    if _injector is None:
        _injector = LessonInjector()
    return _injector


def inject_lessons(query: str) -> str:
    """
    Convenience function to get lesson prompt for a query.
    Call this from generate_answer.py to add lessons to the prompt.
    """
    return get_injector().generate_lesson_prompt(query)


def get_agent_guidance(agent_name: str) -> str:
    """
    Convenience function to get guidance for a sub-agent.
    """
    return get_injector().get_sub_agent_guidance(agent_name)


# Test
if __name__ == "__main__":
    injector = LessonInjector()
    
    print("\n=== LESSON INJECTOR TEST ===\n")
    
    test_queries = [
        "We need a machine for 5mm ABS sheets",
        "What's your best price?",
        "We need it URGENTLY",
        "Can you explain the heating system specifications?",
    ]
    
    for query in test_queries:
        print(f"\nQuery: {query}")
        print("-" * 40)
        lessons = injector.get_relevant_lessons(query)
        print(f"Found {len(lessons)} relevant lessons:")
        for l in lessons:
            print(f"  • {l.get('lesson', 'N/A')[:60]}...")
    
    print("\n\n=== SUB-AGENT GUIDANCE ===")
    for agent in ["athena", "clio", "calliope", "vera", "sophia"]:
        guidance = injector.get_sub_agent_guidance(agent)
        if guidance:
            print(f"\n{agent.upper()}: {guidance[:200]}...")
