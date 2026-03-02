#!/usr/bin/env python3
"""
Relationship Health Dashboard
=============================

Provides a comprehensive view of all relationship health across contacts.
Can be queried via Telegram commands or run as a standalone report.

Features:
- Overall relationship health metrics
- At-risk relationships needing attention
- Proactive outreach priorities
- Communication style insights
- Pattern and trend analysis

Usage:
    # Via Python
    from relationship_dashboard import get_dashboard, get_priorities, generate_report
    
    dashboard = get_dashboard()
    priorities = get_priorities()
    report = generate_report()
    
    # Via Telegram
    /dashboard        - Get relationship health overview
    /priorities       - Get top contacts needing attention
    /at_risk          - Get declining relationships
    /insights [name]  - Get insights about a specific contact
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import json

from .replika_integration import ConversationalEnhancer, create_enhancer
from .relationship_store import get_relationship_store, RelationshipStore


@dataclass
class DashboardMetrics:
    """Key metrics for the dashboard."""
    total_relationships: int = 0
    healthy_relationships: int = 0
    at_risk_relationships: int = 0
    declining_relationships: int = 0
    
    # Warmth distribution
    trusted_count: int = 0
    warm_count: int = 0
    familiar_count: int = 0
    acquaintance_count: int = 0
    stranger_count: int = 0
    
    # Health
    average_health_score: float = 50.0
    health_trend: str = "stable"  # improving, stable, declining
    
    # Engagement
    total_interactions: int = 0
    interactions_last_7_days: int = 0
    interactions_last_30_days: int = 0
    
    # Actions pending
    pending_followups: int = 0
    pending_milestones: int = 0
    actionable_insights: int = 0
    
    def to_dict(self) -> Dict:
        return {
            "total_relationships": self.total_relationships,
            "healthy_relationships": self.healthy_relationships,
            "at_risk_relationships": self.at_risk_relationships,
            "declining_relationships": self.declining_relationships,
            "warmth_distribution": {
                "trusted": self.trusted_count,
                "warm": self.warm_count,
                "familiar": self.familiar_count,
                "acquaintance": self.acquaintance_count,
                "stranger": self.stranger_count,
            },
            "average_health_score": round(self.average_health_score, 1),
            "health_trend": self.health_trend,
            "engagement": {
                "total": self.total_interactions,
                "last_7_days": self.interactions_last_7_days,
                "last_30_days": self.interactions_last_30_days,
            },
            "pending_actions": {
                "followups": self.pending_followups,
                "milestones": self.pending_milestones,
                "insights": self.actionable_insights,
            },
        }


@dataclass
class ContactSummary:
    """Summary of a single contact for the dashboard."""
    contact_id: str
    name: str
    warmth: str
    health_score: float
    health_trend: str
    risk_level: str
    last_interaction_days: int
    interaction_count: int
    pending_actions: List[str] = field(default_factory=list)
    top_insight: Optional[str] = None
    style_summary: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "contact_id": self.contact_id,
            "name": self.name,
            "warmth": self.warmth,
            "health_score": round(self.health_score, 1),
            "health_trend": self.health_trend,
            "risk_level": self.risk_level,
            "last_interaction_days": self.last_interaction_days,
            "interaction_count": self.interaction_count,
            "pending_actions": self.pending_actions,
            "top_insight": self.top_insight,
            "style_summary": self.style_summary,
        }


class RelationshipDashboard:
    """
    Central dashboard for relationship health monitoring.
    
    Now reads from SQLite for persistence across restarts.
    Falls back to in-memory if SQLite has no data.
    """
    
    def __init__(self, enhancer: Optional[ConversationalEnhancer] = None):
        self.enhancer = enhancer or create_enhancer()
        self.store = get_relationship_store()
    
    def get_metrics(self) -> DashboardMetrics:
        """Get overall dashboard metrics from SQLite (persisted) or memory (fallback)."""
        metrics = DashboardMetrics()
        
        # Try SQLite first (survives restarts)
        db_metrics = self.store.get_dashboard_metrics()
        
        if db_metrics.get("total_contacts", 0) > 0:
            # Use SQLite data
            metrics.total_relationships = db_metrics["total_contacts"]
            
            warmth_dist = db_metrics.get("warmth_distribution", {})
            metrics.trusted_count = warmth_dist.get("trusted", 0)
            metrics.warm_count = warmth_dist.get("warm", 0)
            metrics.familiar_count = warmth_dist.get("familiar", 0)
            metrics.acquaintance_count = warmth_dist.get("acquaintance", 0)
            metrics.stranger_count = warmth_dist.get("stranger", 0)
            
            metrics.average_health_score = db_metrics.get("average_health", 50.0)
            metrics.at_risk_relationships = db_metrics.get("at_risk_count", 0)
            metrics.declining_relationships = db_metrics.get("declining_count", 0)
            metrics.healthy_relationships = metrics.total_relationships - metrics.at_risk_relationships
            metrics.pending_followups = db_metrics.get("pending_followups", 0)
            
            return metrics
        
        # Fallback to in-memory (for backwards compat)
        relationships = self.enhancer.relationship_memory.relationships
        metrics.total_relationships = len(relationships)
        
        if not relationships:
            return metrics
        
        # Warmth distribution
        warmth_counts = {"trusted": 0, "warm": 0, "familiar": 0, "acquaintance": 0, "stranger": 0}
        health_scores = []
        declining_count = 0
        at_risk_count = 0
        
        for contact_id, rel in relationships.items():
            # Warmth
            warmth = rel.warmth.value
            if warmth in warmth_counts:
                warmth_counts[warmth] += 1
            
            # Health
            health = self.enhancer.quality_tracker.get_health(contact_id)
            if health:
                health_scores.append(health.health_score)
                if health.trend == "declining":
                    declining_count += 1
                if health.risk_level in ["medium", "high"]:
                    at_risk_count += 1
            
            # Interactions
            metrics.total_interactions += rel.interaction_count
            
            # Recent interactions
            if rel.last_interaction:
                days_since = (datetime.now() - rel.last_interaction).days
                if days_since <= 7:
                    metrics.interactions_last_7_days += 1
                if days_since <= 30:
                    metrics.interactions_last_30_days += 1
        
        metrics.trusted_count = warmth_counts["trusted"]
        metrics.warm_count = warmth_counts["warm"]
        metrics.familiar_count = warmth_counts["familiar"]
        metrics.acquaintance_count = warmth_counts["acquaintance"]
        metrics.stranger_count = warmth_counts["stranger"]
        
        metrics.declining_relationships = declining_count
        metrics.at_risk_relationships = at_risk_count
        metrics.healthy_relationships = metrics.total_relationships - at_risk_count
        
        if health_scores:
            metrics.average_health_score = sum(health_scores) / len(health_scores)
        
        # Pending actions
        outreach = self.enhancer.get_proactive_outreach_candidates()
        metrics.pending_followups = len([c for c in outreach if any("follow" in r.lower() for r in c.get("reasons", []))])
        metrics.pending_milestones = len([c for c in outreach if any("milestone" in r.lower() for r in c.get("reasons", []))])
        metrics.actionable_insights = len([c for c in outreach if any("insight" in r.lower() for r in c.get("reasons", []))])
        
        return metrics
    
    def get_contact_summaries(self, limit: int = 20) -> List[ContactSummary]:
        """Get summaries for all contacts, sorted by priority."""
        summaries = []
        
        for contact_id, rel in self.enhancer.relationship_memory.relationships.items():
            health = self.enhancer.quality_tracker.get_health(contact_id)
            health_score = health.health_score if health else 50.0
            health_trend = health.trend if health else "stable"
            risk_level = health.risk_level if health else "low"
            
            # Last interaction
            days_since = 0
            if rel.last_interaction:
                days_since = (datetime.now() - rel.last_interaction).days
            
            # Pending actions
            pending = []
            if rel.needs_followup():
                pending.append("Care follow-up needed")
            milestones = self.enhancer.progress_tracker.get_uncelebrated(contact_id)
            if milestones:
                pending.append(f"Milestone: {milestones[0].get('type', 'unknown')}")
            
            # Top insight
            top_insight = None
            insights = self.enhancer.insights_engine.get_insights(contact_id, actionable_only=True)
            if insights:
                top_insight = insights[0].title
            
            # Style summary
            style_summary = None
            style = self.enhancer.style_engine.profiles.get(contact_id)
            if style and style.messages_analyzed >= 3:
                traits = []
                if style.formality_score > 70:
                    traits.append("formal")
                elif style.formality_score < 30:
                    traits.append("casual")
                if style.detail_score > 70:
                    traits.append("detail-oriented")
                elif style.detail_score < 30:
                    traits.append("prefers brevity")
                if style.pace_score > 70:
                    traits.append("fast-paced")
                if traits:
                    style_summary = ", ".join(traits)
            
            summaries.append(ContactSummary(
                contact_id=contact_id,
                name=rel.name,
                warmth=rel.warmth.value,
                health_score=health_score,
                health_trend=health_trend,
                risk_level=risk_level,
                last_interaction_days=days_since,
                interaction_count=rel.interaction_count,
                pending_actions=pending,
                top_insight=top_insight,
                style_summary=style_summary,
            ))
        
        # Sort by priority: at-risk first, then by days since contact
        summaries.sort(key=lambda s: (
            0 if s.risk_level == "high" else 1 if s.risk_level == "medium" else 2,
            -s.health_score,
            s.last_interaction_days
        ))
        
        return summaries[:limit]
    
    def get_priorities(self, limit: int = 5) -> List[Dict]:
        """Get top priority contacts needing attention."""
        return self.enhancer.get_proactive_outreach_candidates()[:limit]
    
    def get_at_risk(self) -> List[Dict]:
        """Get at-risk relationships from SQLite."""
        # Try SQLite first
        at_risk = self.store.get_at_risk_contacts(threshold=45.0)
        if at_risk:
            results = []
            for row in at_risk:
                suggestions = []
                if row.get("trend") == "declining":
                    suggestions.append("Relationship quality is declining. Consider personalized follow-up.")
                if row.get("health_score", 50) < 40:
                    suggestions.append("Low satisfaction detected. Address underlying concerns.")
                
                results.append({
                    "contact_id": row["contact_id"],
                    "name": row.get("name", row["contact_id"]),
                    "health_score": row.get("health_score", 50),
                    "trend": row.get("trend", "stable"),
                    "risk_level": row.get("risk_level", "low"),
                    "warmth": row.get("warmth", "stranger"),
                    "suggestions": suggestions,
                })
            return results
        
        # Fallback to in-memory
        return self.enhancer.get_at_risk_relationships()
    
    def get_contact_detail(self, contact_id: str) -> Optional[Dict]:
        """Get detailed view of a single contact."""
        rel = self.enhancer.relationship_memory.relationships.get(contact_id)
        if not rel:
            return None
        
        health = self.enhancer.quality_tracker.get_health(contact_id)
        insights = self.enhancer.insights_engine.get_insights(contact_id)
        style = self.enhancer.style_engine.profiles.get(contact_id)
        context = self.enhancer.relationship_memory.get_relationship_context(contact_id)
        
        return {
            "contact_id": contact_id,
            "name": rel.name,
            "warmth": rel.warmth.value,
            "warmth_score": rel.warmth_score,
            "interaction_count": rel.interaction_count,
            "positive_interactions": rel.positive_interactions,
            "relationship_started": rel.relationship_started.isoformat() if rel.relationship_started else None,
            "last_interaction": rel.last_interaction.isoformat() if rel.last_interaction else None,
            "conversation_health": health.to_dict() if health else None,
            "improvement_suggestions": self.enhancer.quality_tracker.get_improvement_suggestions(contact_id),
            "insights": [i.to_dict() for i in insights],
            "style_profile": style.to_dict() if style else None,
            "memorable_moments": [
                {"type": m.moment_type.value, "content": m.content, "date": m.timestamp.isoformat()}
                for m in rel.memorable_moments[-5:]
            ],
            "learned_preferences": [
                {"type": p.preference_type, "value": p.value}
                for p in rel.learned_preferences
            ],
            "pending_followups": context.get("pending_followups", []),
        }
    
    def generate_text_report(self) -> str:
        """Generate a text report for Telegram."""
        metrics = self.get_metrics()
        priorities = self.get_priorities(5)
        at_risk = self.get_at_risk()
        
        lines = ["📊 **Relationship Health Dashboard**", ""]
        
        # Overview
        lines.append(f"**Total Contacts:** {metrics.total_relationships}")
        lines.append(f"**Healthy:** {metrics.healthy_relationships} | **At Risk:** {metrics.at_risk_relationships}")
        lines.append(f"**Average Health:** {metrics.average_health_score:.0f}/100")
        lines.append("")
        
        # Warmth distribution
        lines.append("**Relationship Warmth:**")
        if metrics.trusted_count:
            lines.append(f"  🌟 Trusted: {metrics.trusted_count}")
        if metrics.warm_count:
            lines.append(f"  ❤️ Warm: {metrics.warm_count}")
        if metrics.familiar_count:
            lines.append(f"  👋 Familiar: {metrics.familiar_count}")
        if metrics.acquaintance_count:
            lines.append(f"  🤝 Acquaintance: {metrics.acquaintance_count}")
        if metrics.stranger_count:
            lines.append(f"  👤 New: {metrics.stranger_count}")
        lines.append("")
        
        # Priorities
        if priorities:
            lines.append("**🎯 Top Priorities:**")
            for i, p in enumerate(priorities[:3], 1):
                name = p.get("name", p.get("contact_id", "Unknown"))
                reasons = p.get("reasons", [])
                reason_text = reasons[0] if reasons else "Needs attention"
                lines.append(f"  {i}. {name}: {reason_text}")
            lines.append("")
        
        # At risk
        if at_risk:
            lines.append("**⚠️ At Risk Relationships:**")
            for r in at_risk[:3]:
                name = r.get("name", r.get("contact_id", "Unknown"))
                score = r.get("health_score", 0)
                trend = r.get("trend", "unknown")
                lines.append(f"  • {name}: {score:.0f}/100 ({trend})")
            lines.append("")
        
        # Pending actions
        pending_total = metrics.pending_followups + metrics.pending_milestones + metrics.actionable_insights
        if pending_total > 0:
            lines.append(f"**📋 Pending Actions:** {pending_total}")
            if metrics.pending_followups:
                lines.append(f"  • Follow-ups: {metrics.pending_followups}")
            if metrics.pending_milestones:
                lines.append(f"  • Milestones: {metrics.pending_milestones}")
            if metrics.actionable_insights:
                lines.append(f"  • Insights: {metrics.actionable_insights}")
        
        return "\n".join(lines)
    
    def generate_json_report(self) -> Dict:
        """Generate a JSON report for API/export."""
        return {
            "generated_at": datetime.now().isoformat(),
            "metrics": self.get_metrics().to_dict(),
            "priorities": self.get_priorities(10),
            "at_risk": self.get_at_risk(),
            "contact_summaries": [s.to_dict() for s in self.get_contact_summaries(20)],
        }


# Module-level singleton
_dashboard: Optional[RelationshipDashboard] = None


def get_dashboard() -> RelationshipDashboard:
    """Get or create the dashboard singleton."""
    global _dashboard
    if _dashboard is None:
        _dashboard = RelationshipDashboard()
    return _dashboard


def get_metrics() -> DashboardMetrics:
    """Get dashboard metrics."""
    return get_dashboard().get_metrics()


def get_priorities(limit: int = 5) -> List[Dict]:
    """Get priority contacts."""
    return get_dashboard().get_priorities(limit)


def get_at_risk() -> List[Dict]:
    """Get at-risk relationships."""
    return get_dashboard().get_at_risk()


def get_contact_detail(contact_id: str) -> Optional[Dict]:
    """Get detail for a contact."""
    return get_dashboard().get_contact_detail(contact_id)


def generate_report(format: str = "text") -> str:
    """Generate a report."""
    dashboard = get_dashboard()
    if format == "json":
        return json.dumps(dashboard.generate_json_report(), indent=2, default=str)
    return dashboard.generate_text_report()


# CLI support
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--json":
        print(generate_report("json"))
    else:
        print(generate_report("text"))
