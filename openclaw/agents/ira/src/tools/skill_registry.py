"""
Skill Registry (P3 Remediation)

Provides a discoverable, consistent interface for IRA skills.
Skills can be invoked via execute_skill(SkillTask) for tool/code integration.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("ira.skill_registry")


@dataclass
class SkillTask:
    """
    JSON-serializable task descriptor for skill invocation.
    Used by tools, OpenClaw, and programmatic callers.
    """
    skill_name: str
    arguments: Dict[str, Any]
    context: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "skill_name": self.skill_name,
            "arguments": self.arguments,
            "context": self.context,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "SkillTask":
        return cls(
            skill_name=d.get("skill_name", ""),
            arguments=d.get("arguments", {}),
            context=d.get("context", {}),
        )


@dataclass
class SkillResult:
    """Result from a skill execution."""
    success: bool
    output: str
    skill_name: str
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "output": self.output,
            "skill_name": self.skill_name,
            "error": self.error,
            "metadata": self.metadata,
        }


# Registry: name -> (description, openai_schema, executor)
_SKILLS: Dict[str, Dict[str, Any]] = {}


def register_skill(
    name: str,
    description: str,
    schema: Dict[str, Any],
    executor: Callable,
) -> None:
    """Register a skill for discovery and execution."""
    _SKILLS[name] = {
        "description": description,
        "schema": schema,
        "executor": executor,
    }


def get_skill(name: str) -> Optional[Dict[str, Any]]:
    """Get skill metadata by name."""
    return _SKILLS.get(name)


def list_skills() -> List[str]:
    """List registered skill names."""
    return list(_SKILLS.keys())


def get_all_schemas() -> List[Dict[str, Any]]:
    """Return OpenAI-compatible tool schemas for all registered skills."""
    return [_SKILLS[n]["schema"] for n in _SKILLS]


async def execute_skill(task: SkillTask) -> SkillResult:
    """
    Execute a skill by name. Used by tools, OpenClaw, and programmatic callers.
    """
    skill = get_skill(task.skill_name)
    if not skill:
        return SkillResult(
            success=False,
            output="",
            skill_name=task.skill_name,
            error=f"Unknown skill: {task.skill_name}",
        )
    try:
        from openclaw.agents.ira.src.tools.ira_skills_tools import execute_tool_call
        output = await execute_tool_call(
            task.skill_name,
            task.arguments,
            task.context,
        )
        return SkillResult(success=True, output=output, skill_name=task.skill_name)
    except Exception as e:
        logger.exception("Skill execution failed: %s", task.skill_name)
        return SkillResult(
            success=False,
            output="",
            skill_name=task.skill_name,
            error=str(e),
        )


def _bootstrap_registry() -> None:
    """Register IRA skills from ira_skills_tools schema."""
    try:
        from openclaw.agents.ira.src.tools.ira_skills_tools import IRA_TOOLS_SCHEMA
        for t in IRA_TOOLS_SCHEMA:
            fn = t.get("function", {})
            name = fn.get("name", "")
            if name:
                register_skill(
                    name=name,
                    description=fn.get("description", ""),
                    schema=t,
                    executor=None,
                )
    except ImportError:
        pass


_bootstrap_registry()
