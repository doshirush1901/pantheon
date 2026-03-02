"""
Sophia - The Reflector (OpenClaw Native)

The wise mentor. Introspective, adaptive, and the keeper of wisdom.
She learns from every interaction, consolidates memories during Dream Mode,
and makes the entire system smarter over time.

This module provides reflection functions that can be invoked by the LLM
through OpenClaw's native tool system.
"""

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("ira.sophia")

# Path to learning files
AGENT_DIR = Path(__file__).parent.parent.parent.parent
ERRORS_FILE = AGENT_DIR / "data" / "errors.md"
LESSONS_FILE = AGENT_DIR / "data" / "lessons.md"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class QualityScore:
    """Quality assessment for an interaction."""
    factual_accuracy: float = 0.0
    helpfulness: float = 0.0
    completeness: float = 0.0
    tone: float = 0.0
    structure: float = 0.0
    responsiveness: float = 0.0
    
    @property
    def overall(self) -> float:
        """Calculate overall score."""
        scores = [
            self.factual_accuracy,
            self.helpfulness,
            self.completeness,
            self.tone,
            self.structure,
            self.responsiveness
        ]
        return sum(scores) / len(scores)


@dataclass
class ReflectionResult:
    """Result of a reflection analysis."""
    quality_score: QualityScore
    issues: List[str] = field(default_factory=list)
    lessons: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


# =============================================================================
# CORE REFLECTION FUNCTIONS
# =============================================================================

async def reflect(interaction_data: Dict[str, Any]) -> ReflectionResult:
    """
    Main reflection function - can be called as an OpenClaw tool.
    
    Analyzes an interaction and extracts learnings.
    
    Args:
        interaction_data: Dict containing:
            - user_message: Original user message
            - response: Generated response
            - intent: Detected intent
            - results: Results from each agent (optional)
            
    Returns:
        ReflectionResult with quality scores and learnings
    """
    logger.info({
        "agent": "Sophia",
        "event": "reflection_started"
    })
    
    user_message = interaction_data.get("user_message") or ""
    response = interaction_data.get("response") or ""
    intent = interaction_data.get("intent") or "general"
    results = interaction_data.get("results") or {}
    
    # Evaluate quality — try LLM for substantive responses, fall back to heuristic
    quality = None
    if len(response) > 100:
        quality = await _evaluate_quality_llm(user_message, response, intent)
    if quality is None:
        quality = _evaluate_quality(user_message, response, intent)
    
    # Identify issues
    issues = _identify_issues(user_message, response, results)
    
    # Extract lessons
    lessons = _extract_lessons(user_message, response, issues)
    
    # Log errors if any
    if issues:
        _log_errors(issues, interaction_data)

    # Log lessons if any
    if lessons:
        _log_lessons(lessons, interaction_data)

    # Feed back into the endocrine system so agent scores reflect quality
    _signal_quality_to_endocrine(quality, issues, interaction_data)

    logger.info({
        "agent": "Sophia",
        "event": "reflection_complete",
        "quality_score": round(quality.overall, 2),
        "issues_found": len(issues),
        "lessons_extracted": len(lessons)
    })
    
    return ReflectionResult(
        quality_score=quality,
        issues=issues,
        lessons=lessons,
        recommendations=_generate_recommendations(quality, issues)
    )


def _evaluate_quality(user_message: str, response: str, intent: str) -> QualityScore:
    """Evaluate the quality of the interaction across 6 dimensions."""
    score = QualityScore()
    
    # Factual Accuracy (check for disclaimers, proper warnings)
    if "subject to configuration" in response.lower():
        score.factual_accuracy += 0.2
    if "1.5mm" in response or "≤1.5" in response:
        score.factual_accuracy += 0.3
    if "[SOURCE:" in response or "[Machine Database]" in response:
        score.factual_accuracy += 0.5
    score.factual_accuracy = min(1.0, score.factual_accuracy)
    
    # Helpfulness (did we provide useful information?)
    if len(response) > 100:
        score.helpfulness += 0.3
    if any(keyword in response.lower() for keyword in ["specification", "price", "recommend", "model"]):
        score.helpfulness += 0.4
    if "let me know" in response.lower() or "happy to" in response.lower():
        score.helpfulness += 0.3
    score.helpfulness = min(1.0, score.helpfulness)
    
    # Completeness (did we address all parts of the query?)
    if "?" in user_message:
        # Question was asked - check if we gave an answer
        if any(word in response.lower() for word in ["yes", "no", "is", "are", "can", "will"]):
            score.completeness += 0.5
    if len(response) > 200:
        score.completeness += 0.3
    score.completeness = min(1.0, max(0.5, score.completeness))
    
    # Tone (professional and appropriate)
    exclaim_count = response.count("!")
    if exclaim_count <= 1:
        score.tone += 0.5
    if not any(word in response.lower() for word in ["sorry", "unfortunately", "can't"]):
        score.tone += 0.3
    if "thank" in response.lower() or "please" in response.lower():
        score.tone += 0.2
    score.tone = min(1.0, score.tone)
    
    # Structure (well-organized response)
    if "**" in response or "##" in response:  # Has formatting
        score.structure += 0.3
    if "\n\n" in response:  # Has paragraphs
        score.structure += 0.3
    if "-" in response:  # Has bullet points
        score.structure += 0.2
    score.structure = min(1.0, max(0.3, score.structure))
    
    # Responsiveness (answered promptly and directly)
    if response[:100].lower().count(user_message.split()[0].lower() if user_message else "") > 0:
        score.responsiveness += 0.5
    score.responsiveness = min(1.0, max(0.5, score.responsiveness))
    
    return score


def _identify_issues(user_message: str, response: str, results: Dict) -> List[str]:
    """Identify issues with the interaction."""
    issues = []
    
    # Check for missing pricing disclaimer
    if any(x in response for x in ["₹", "Rs", "lakh", "crore"]):
        if "subject to" not in response.lower():
            issues.append("PRICING_DISCLAIMER_MISSING: Response contains price without disclaimer")
    
    # Check for potential AM series violation
    thickness_match = None
    import re
    thickness_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:mm|millimeter)', user_message, re.IGNORECASE)
    if thickness_match:
        thickness = float(thickness_match.group(1))
        if thickness > 1.5:
            if "AM" in response and "1.5" not in response:
                issues.append(f"AM_SERIES_VIOLATION: AM series mentioned for {thickness}mm without warning")
            if "1.5" not in response and "AM" not in response.lower():
                issues.append(f"AM_WARNING_MISSING: {thickness}mm material query without AM series guidance")
    
    # Check for empty or very short response — but allow short replies to
    # greetings, acknowledgments, and commands (these are valid short exchanges)
    if len(response) < 50:
        msg_lower = user_message.lower().strip()
        is_greeting = any(g in msg_lower for g in ["hi", "hello", "hey", "good morning", "good evening", "good afternoon"])
        is_ack = any(a in msg_lower for a in ["thanks", "thank you", "ok", "got it", "cool", "great", "nice"])
        is_command = msg_lower.startswith("/")
        if not (is_greeting or is_ack or is_command):
            issues.append("RESPONSE_TOO_SHORT: Response may be incomplete")
    
    # Check for apology-heavy responses
    apology_count = response.lower().count("sorry") + response.lower().count("apologize")
    if apology_count > 1:
        issues.append("EXCESSIVE_APOLOGIES: Response contains multiple apologies")
    
    return issues


def _extract_lessons(user_message: str, response: str, issues: List[str]) -> List[str]:
    """Extract generalizable lessons from the interaction."""
    lessons = []
    
    # Lesson from pricing interactions
    if any(x in user_message.lower() for x in ["price", "cost", "quote"]):
        if "subject to" in response.lower():
            lessons.append("GOOD_PRACTICE: Pricing disclaimer included correctly")
        else:
            lessons.append("IMPROVEMENT: Always include pricing disclaimer for price queries")
    
    # Lesson from thickness-related queries
    import re
    if re.search(r'\d+\s*mm', user_message, re.IGNORECASE):
        if "1.5" in response or "AM series" in response:
            lessons.append("GOOD_PRACTICE: Thickness guidance provided correctly")
    
    # Lessons from issues
    for issue in issues:
        if "PRICING_DISCLAIMER" in issue:
            lessons.append("REMINDER: Check all responses for pricing disclaimer compliance")
        if "AM_SERIES" in issue:
            lessons.append("REMINDER: Always verify AM series recommendations against thickness requirements")
    
    return lessons


def _generate_recommendations(quality: QualityScore, issues: List[str]) -> List[str]:
    """Generate recommendations for improvement."""
    recommendations = []
    
    if quality.factual_accuracy < 0.7:
        recommendations.append("Improve source citation in responses")
    
    if quality.helpfulness < 0.7:
        recommendations.append("Provide more specific and actionable information")
    
    if quality.completeness < 0.7:
        recommendations.append("Ensure all parts of user queries are addressed")
    
    if quality.structure < 0.7:
        recommendations.append("Use better formatting (headers, bullet points) for clarity")
    
    if any("AM_SERIES" in issue for issue in issues):
        recommendations.append("CRITICAL: Review AM series thickness rule compliance")
    
    if any("PRICING" in issue for issue in issues):
        recommendations.append("Add pricing disclaimer check to response pipeline")
    
    return recommendations


def _signal_quality_to_endocrine(
    quality: QualityScore, issues: List[str], interaction_data: Dict
) -> None:
    """Feed Sophia's quality assessment back into the endocrine system.

    This closes the loop: Sophia evaluates → endocrine scores update →
    scores are visible in vital signs and (via P3-2) influence tool dispatch.
    """
    try:
        from openclaw.agents.ira.src.holistic.endocrine_system import get_endocrine_system
        endo = get_endocrine_system()

        tools_used = interaction_data.get("tools_used", [])
        tool_agent_map = {
            "research_skill": "clio", "writing_skill": "calliope",
            "fact_checking_skill": "vera", "web_search": "iris",
            "lead_intelligence": "iris",
        }
        agents_involved = {tool_agent_map[t] for t in tools_used if t in tool_agent_map}

        if quality.overall >= 0.7 and not issues:
            for agent in agents_involved:
                endo.signal_success(agent, context={"source": "sophia_reflection"})
            endo.signal_success("athena", context={"source": "sophia_reflection", "score": round(quality.overall, 2)})
        elif quality.overall < 0.5 or len(issues) >= 2:
            for agent in agents_involved:
                endo.signal_failure(agent, context={"source": "sophia_reflection", "issues": issues[:3]})
            endo.signal_failure("athena", context={"source": "sophia_reflection", "score": round(quality.overall, 2)})
    except Exception as e:
        logger.debug("Sophia: endocrine feedback failed: %s", e)


def _log_errors(issues: List[str], interaction_data: Dict) -> None:
    """Log errors to errors.md file."""
    try:
        ERRORS_FILE.parent.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        user_message = interaction_data.get('user_message') or 'N/A'
        entry = f"\n## {timestamp}\n\n"
        entry += f"**Query:** {str(user_message)[:100]}\n\n"
        entry += "**Issues:**\n"
        for issue in issues:
            entry += f"- {issue}\n"
        entry += "\n---\n"
        
        with open(ERRORS_FILE, "a") as f:
            f.write(entry)
        
        logger.debug(f"Logged {len(issues)} errors to {ERRORS_FILE}")
        
    except Exception as e:
        logger.error(f"Failed to log errors: {e}")


def _log_lessons(lessons: List[str], interaction_data: Dict) -> None:
    """Log lessons to lessons.md file."""
    try:
        LESSONS_FILE.parent.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = f"\n## {timestamp}\n\n"
        
        for lesson in lessons:
            if lesson.startswith("GOOD_PRACTICE"):
                entry += f"✓ {lesson}\n"
            elif lesson.startswith("IMPROVEMENT"):
                entry += f"→ {lesson}\n"
            elif lesson.startswith("REMINDER"):
                entry += f"⚠ {lesson}\n"
            else:
                entry += f"- {lesson}\n"
        
        entry += "\n---\n"
        
        with open(LESSONS_FILE, "a") as f:
            f.write(entry)
        
        logger.debug(f"Logged {len(lessons)} lessons to {LESSONS_FILE}")
        
    except Exception as e:
        logger.error(f"Failed to log lessons: {e}")


# =============================================================================
# LLM-BASED QUALITY EVALUATION
# =============================================================================

async def _evaluate_quality_llm(user_message: str, response: str, intent: str) -> Optional[QualityScore]:
    """LLM-based quality evaluation for substantive responses.
    
    Returns None on failure so the caller can fall back to the heuristic.
    """
    try:
        import openai
        api_key = os.environ.get("OPENAI_API_KEY", "")
        if not api_key:
            return None

        client = openai.OpenAI(api_key=api_key)
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": (
                    "Rate this customer service response on 6 dimensions (0.0-1.0).\n"
                    "Consider the context: this is for Machinecraft Technologies, a thermoforming machine company.\n\n"
                    "Dimensions:\n"
                    "- factual_accuracy: Are claims specific and verifiable? Are disclaimers present where needed?\n"
                    "- helpfulness: Does it answer the question with useful, actionable information?\n"
                    "- completeness: Are all parts of the query addressed?\n"
                    "- tone: Professional, warm, confident? Not overly apologetic?\n"
                    "- structure: Well-organized with formatting where appropriate?\n"
                    "- responsiveness: Direct and to-the-point?\n\n"
                    "Output ONLY valid JSON: {\"factual_accuracy\": 0.8, \"helpfulness\": 0.7, "
                    "\"completeness\": 0.9, \"tone\": 0.8, \"structure\": 0.7, \"responsiveness\": 0.8}"
                )},
                {"role": "user", "content": f"QUERY: {user_message[:200]}\nRESPONSE: {response[:500]}"},
            ],
            max_tokens=100,
            temperature=0.1,
        )
        raw = resp.choices[0].message.content.strip()
        # Handle markdown-wrapped JSON
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()
        scores = json.loads(raw)
        return QualityScore(
            factual_accuracy=float(scores.get("factual_accuracy", 0.5)),
            helpfulness=float(scores.get("helpfulness", 0.5)),
            completeness=float(scores.get("completeness", 0.5)),
            tone=float(scores.get("tone", 0.5)),
            structure=float(scores.get("structure", 0.5)),
            responsiveness=float(scores.get("responsiveness", 0.5)),
        )
    except Exception as e:
        logger.debug(f"Sophia: LLM quality evaluation failed, using heuristic: {e}")
        return None


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def get_recent_errors(limit: int = 10) -> List[str]:
    """Get recent errors from the error log."""
    try:
        if not ERRORS_FILE.exists():
            return []
        
        content = ERRORS_FILE.read_text()
        sections = content.split("---")
        return [s.strip() for s in sections[-limit:] if s.strip()]
    except Exception as e:
        logger.error(f"Failed to read errors: {e}")
        return []


def get_recent_lessons(limit: int = 10) -> List[str]:
    """Get recent lessons from the lesson log."""
    try:
        if not LESSONS_FILE.exists():
            return []
        
        content = LESSONS_FILE.read_text()
        sections = content.split("---")
        return [s.strip() for s in sections[-limit:] if s.strip()]
    except Exception as e:
        logger.error(f"Failed to read lessons: {e}")
        return []


def get_quality_trends() -> Dict[str, Any]:
    """Analyze quality trends from recent reflections."""
    # This would analyze historical reflection data
    # For now, return a placeholder
    return {
        "note": "Quality trend analysis requires historical data",
        "recommendation": "Run more interactions to build baseline"
    }
