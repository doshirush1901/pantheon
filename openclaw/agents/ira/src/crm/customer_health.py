#!/usr/bin/env python3
"""
CUSTOMER HEALTH SCORING
========================

Tracks customer engagement and calculates health scores to identify
at-risk relationships and engagement opportunities.

Metrics tracked:
- Message frequency (Telegram + Email)
- Response latency
- Sentiment trends
- Quote conversion history
- Engagement recency

Usage:
    from customer_health import HealthScorer, get_scorer
    
    scorer = get_scorer()
    
    # Get health score for a customer
    health = scorer.get_customer_health("john@acme.com")
    print(f"Score: {health.score}/100")
    print(f"Risk: {health.risk_level}")
    
    # Get all at-risk customers
    at_risk = scorer.get_at_risk_customers()
"""

import os
import sys
import json
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from contextlib import contextmanager

SKILL_DIR = Path(__file__).parent
SKILLS_DIR = SKILL_DIR.parent
AGENT_DIR = SKILLS_DIR.parent
PROJECT_ROOT = AGENT_DIR.parent.parent.parent

# Load env
env_file = PROJECT_ROOT / ".env"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        if line.strip() and not line.startswith('#') and '=' in line:
            key, _, value = line.partition('=')
            os.environ.setdefault(key.strip(), value.strip().strip('"'))

# Paths
CRM_DIR = PROJECT_ROOT / "crm"
REQUEST_LOG = CRM_DIR / "logs" / "requests.jsonl"
HEALTH_DB = CRM_DIR / "customer_health.db"


class RiskLevel(Enum):
    """Customer risk levels."""
    HEALTHY = "healthy"
    WATCH = "watch"
    AT_RISK = "at_risk"
    CHURNING = "churning"


class EngagementTrend(Enum):
    """Engagement direction."""
    IMPROVING = "improving"
    STABLE = "stable"
    DECLINING = "declining"
    INACTIVE = "inactive"


@dataclass
class EngagementMetrics:
    """Raw engagement metrics for a customer."""
    total_messages: int = 0
    telegram_messages: int = 0
    email_messages: int = 0
    last_contact: Optional[datetime] = None
    days_since_contact: int = 0
    
    # Response patterns
    avg_response_time_hours: float = 0
    messages_last_7_days: int = 0
    messages_last_30_days: int = 0
    
    # Quote activity
    total_quotes: int = 0
    active_quotes: int = 0
    won_quotes: int = 0
    lost_quotes: int = 0
    
    # Engagement quality
    follow_up_response_rate: float = 0  # % of follow-ups that got response
    multi_channel: bool = False  # Uses both email and telegram
    
    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["last_contact"] = self.last_contact.isoformat() if self.last_contact else None
        return d


@dataclass
class CustomerHealth:
    """Health assessment for a customer."""
    customer_email: str
    customer_name: Optional[str] = None
    company: Optional[str] = None
    
    # Score (0-100)
    score: int = 50
    risk_level: RiskLevel = RiskLevel.WATCH
    trend: EngagementTrend = EngagementTrend.STABLE
    
    # Component scores
    recency_score: int = 50      # Recent engagement
    frequency_score: int = 50    # Message frequency
    monetary_score: int = 50     # Quote value
    conversion_score: int = 50   # Win rate
    
    # Detailed metrics
    metrics: EngagementMetrics = field(default_factory=EngagementMetrics)
    
    # Insights and recommendations
    risk_factors: List[str] = field(default_factory=list)
    opportunities: List[str] = field(default_factory=list)
    recommended_action: str = ""
    
    # Metadata
    calculated_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "customer_email": self.customer_email,
            "customer_name": self.customer_name,
            "company": self.company,
            "score": self.score,
            "risk_level": self.risk_level.value,
            "trend": self.trend.value,
            "recency_score": self.recency_score,
            "frequency_score": self.frequency_score,
            "monetary_score": self.monetary_score,
            "conversion_score": self.conversion_score,
            "metrics": self.metrics.to_dict(),
            "risk_factors": self.risk_factors,
            "opportunities": self.opportunities,
            "recommended_action": self.recommended_action,
            "calculated_at": self.calculated_at.isoformat(),
        }
    
    def to_summary(self) -> str:
        """Short summary for Telegram."""
        risk_emoji = {
            "healthy": "💚",
            "watch": "💛", 
            "at_risk": "🟠",
            "churning": "🔴",
        }[self.risk_level.value]
        
        trend_emoji = {
            "improving": "📈",
            "stable": "➡️",
            "declining": "📉",
            "inactive": "💤",
        }[self.trend.value]
        
        summary = f"{risk_emoji} *{self.customer_name or self.customer_email}*"
        if self.company:
            summary += f" ({self.company})"
        summary += f"\n   Score: {self.score}/100 {trend_emoji}"
        summary += f"\n   Last contact: {self.metrics.days_since_contact}d ago"
        
        if self.risk_factors:
            summary += f"\n   ⚠️ {self.risk_factors[0]}"
        
        return summary


class HealthScorer:
    """
    Calculates customer health scores based on engagement data.
    
    Score components (each 0-100):
    - Recency (30%): How recently they engaged
    - Frequency (25%): How often they engage
    - Monetary (25%): Quote values and pipeline
    - Conversion (20%): Historical win rate
    """
    
    # Weights for final score
    WEIGHTS = {
        "recency": 0.30,
        "frequency": 0.25,
        "monetary": 0.25,
        "conversion": 0.20,
    }
    
    # Thresholds
    HEALTHY_SCORE = 70
    WATCH_SCORE = 50
    AT_RISK_SCORE = 30
    
    def __init__(self):
        self._cache: Dict[str, CustomerHealth] = {}
        self._cache_time: Optional[datetime] = None
    
    def get_customer_health(
        self, 
        customer_email: str,
        force_refresh: bool = False
    ) -> CustomerHealth:
        """Get health score for a specific customer."""
        # Check cache
        if not force_refresh and customer_email in self._cache:
            cached = self._cache[customer_email]
            if (datetime.now() - cached.calculated_at).seconds < 3600:
                return cached
        
        # Calculate fresh
        metrics = self._collect_metrics(customer_email)
        health = self._calculate_health(customer_email, metrics)
        
        # Cache
        self._cache[customer_email] = health
        
        return health
    
    def get_all_customer_health(self, min_messages: int = 2) -> List[CustomerHealth]:
        """Get health scores for all customers."""
        customers = self._get_all_customers(min_messages)
        return [self.get_customer_health(email) for email in customers]
    
    def get_at_risk_customers(self) -> List[CustomerHealth]:
        """Get customers with declining health."""
        all_health = self.get_all_customer_health()
        return [
            h for h in all_health 
            if h.risk_level in [RiskLevel.AT_RISK, RiskLevel.CHURNING]
        ]
    
    def get_healthy_customers(self) -> List[CustomerHealth]:
        """Get customers in good health."""
        all_health = self.get_all_customer_health()
        return [h for h in all_health if h.risk_level == RiskLevel.HEALTHY]
    
    def _get_all_customers(self, min_messages: int = 2) -> List[str]:
        """Get list of all customer emails with enough activity."""
        customers = {}
        
        if REQUEST_LOG.exists():
            try:
                with open(REQUEST_LOG, 'r') as f:
                    for line in f:
                        if not line.strip():
                            continue
                        try:
                            record = json.loads(line)
                            email = record.get("user_id", "")
                            if "@" in email:  # Only emails
                                customers[email] = customers.get(email, 0) + 1
                        except json.JSONDecodeError:
                            continue
            except Exception:
                pass
        
        # Also check quotes database
        try:
            sys.path.insert(0, str(SKILL_DIR))
            from quote_lifecycle import get_tracker
            tracker = get_tracker()
            
            for quote in tracker.get_active_quotes():
                email = quote.customer_email
                if email:
                    customers[email] = customers.get(email, 0) + 1
        except Exception:
            pass
        
        return [email for email, count in customers.items() if count >= min_messages]
    
    def _collect_metrics(self, customer_email: str) -> EngagementMetrics:
        """Collect engagement metrics for a customer."""
        metrics = EngagementMetrics()
        
        email_lower = customer_email.lower()
        now = datetime.now()
        cutoff_7d = now - timedelta(days=7)
        cutoff_30d = now - timedelta(days=30)
        
        # Read request logs
        if REQUEST_LOG.exists():
            try:
                with open(REQUEST_LOG, 'r') as f:
                    for line in f:
                        if not line.strip():
                            continue
                        try:
                            record = json.loads(line)
                            user_id = record.get("user_id", "").lower()
                            
                            if user_id != email_lower:
                                continue
                            
                            metrics.total_messages += 1
                            
                            channel = record.get("channel", "")
                            if channel == "telegram":
                                metrics.telegram_messages += 1
                            elif channel == "email":
                                metrics.email_messages += 1
                            
                            # Parse timestamp
                            ts_str = record.get("timestamp", "")
                            if ts_str:
                                ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00")).replace(tzinfo=None)
                                
                                if metrics.last_contact is None or ts > metrics.last_contact:
                                    metrics.last_contact = ts
                                
                                if ts > cutoff_7d:
                                    metrics.messages_last_7_days += 1
                                if ts > cutoff_30d:
                                    metrics.messages_last_30_days += 1
                                    
                        except (json.JSONDecodeError, ValueError):
                            continue
            except Exception:
                pass
        
        # Calculate days since contact
        if metrics.last_contact:
            metrics.days_since_contact = (now - metrics.last_contact).days
        else:
            metrics.days_since_contact = 999
        
        # Check multi-channel
        metrics.multi_channel = metrics.telegram_messages > 0 and metrics.email_messages > 0
        
        # Get quote data
        try:
            sys.path.insert(0, str(SKILL_DIR))
            from quote_lifecycle import get_tracker, QuoteStatus
            tracker = get_tracker()
            
            quotes = tracker.get_quotes_for_customer(customer_email)
            metrics.total_quotes = len(quotes)
            metrics.active_quotes = sum(
                1 for q in quotes 
                if q.status not in [QuoteStatus.WON, QuoteStatus.LOST, QuoteStatus.EXPIRED]
            )
            metrics.won_quotes = sum(1 for q in quotes if q.status == QuoteStatus.WON)
            metrics.lost_quotes = sum(1 for q in quotes if q.status == QuoteStatus.LOST)
        except Exception:
            pass
        
        return metrics
    
    def _calculate_health(
        self, 
        customer_email: str, 
        metrics: EngagementMetrics
    ) -> CustomerHealth:
        """Calculate health score from metrics."""
        health = CustomerHealth(
            customer_email=customer_email,
            metrics=metrics,
        )
        
        # Get customer name/company if available
        try:
            sys.path.insert(0, str(SKILLS_DIR / "identity"))
            from unified_identity import get_identity_service
            identity_svc = get_identity_service()
            
            contact_id = identity_svc.resolve("email", customer_email)
            if contact_id:
                contact = identity_svc.get_contact(contact_id)
                if contact:
                    health.customer_name = contact.name
                    health.company = contact.company
        except Exception:
            pass
        
        # Calculate component scores
        health.recency_score = self._score_recency(metrics)
        health.frequency_score = self._score_frequency(metrics)
        health.monetary_score = self._score_monetary(metrics)
        health.conversion_score = self._score_conversion(metrics)
        
        # Calculate weighted total
        health.score = int(
            health.recency_score * self.WEIGHTS["recency"] +
            health.frequency_score * self.WEIGHTS["frequency"] +
            health.monetary_score * self.WEIGHTS["monetary"] +
            health.conversion_score * self.WEIGHTS["conversion"]
        )
        
        # Determine risk level
        if health.score >= self.HEALTHY_SCORE:
            health.risk_level = RiskLevel.HEALTHY
        elif health.score >= self.WATCH_SCORE:
            health.risk_level = RiskLevel.WATCH
        elif health.score >= self.AT_RISK_SCORE:
            health.risk_level = RiskLevel.AT_RISK
        else:
            health.risk_level = RiskLevel.CHURNING
        
        # Determine trend
        health.trend = self._calculate_trend(metrics)
        
        # Generate insights
        self._add_insights(health)
        
        return health
    
    def _score_recency(self, metrics: EngagementMetrics) -> int:
        """Score based on recency of contact."""
        days = metrics.days_since_contact
        
        if days <= 3:
            return 100
        elif days <= 7:
            return 80
        elif days <= 14:
            return 60
        elif days <= 30:
            return 40
        elif days <= 60:
            return 20
        else:
            return 0
    
    def _score_frequency(self, metrics: EngagementMetrics) -> int:
        """Score based on message frequency."""
        # Weekly rate
        weekly = metrics.messages_last_7_days
        monthly = metrics.messages_last_30_days
        
        if weekly >= 3:
            return 100
        elif weekly >= 1:
            return 80
        elif monthly >= 4:
            return 60
        elif monthly >= 2:
            return 40
        elif metrics.total_messages >= 5:
            return 20
        else:
            return 0
    
    def _score_monetary(self, metrics: EngagementMetrics) -> int:
        """Score based on quote activity and value."""
        if metrics.active_quotes >= 2:
            return 100
        elif metrics.active_quotes == 1:
            return 70
        elif metrics.total_quotes >= 3:
            return 50
        elif metrics.total_quotes >= 1:
            return 30
        else:
            return 10
    
    def _score_conversion(self, metrics: EngagementMetrics) -> int:
        """Score based on conversion history."""
        total_closed = metrics.won_quotes + metrics.lost_quotes
        
        if total_closed == 0:
            return 50  # No history
        
        win_rate = metrics.won_quotes / total_closed
        
        if win_rate >= 0.5:
            return 100
        elif win_rate >= 0.25:
            return 70
        elif win_rate > 0:
            return 40
        else:
            return 20
    
    def _calculate_trend(self, metrics: EngagementMetrics) -> EngagementTrend:
        """Calculate engagement trend."""
        if metrics.days_since_contact > 30:
            return EngagementTrend.INACTIVE
        
        # Compare 7-day to 30-day rate
        weekly_rate = metrics.messages_last_7_days
        monthly_rate = metrics.messages_last_30_days / 4  # Normalize to weekly
        
        if weekly_rate > monthly_rate * 1.5:
            return EngagementTrend.IMPROVING
        elif weekly_rate < monthly_rate * 0.5:
            return EngagementTrend.DECLINING
        else:
            return EngagementTrend.STABLE
    
    def _add_insights(self, health: CustomerHealth) -> None:
        """Add risk factors and opportunities."""
        metrics = health.metrics
        
        # Risk factors
        if metrics.days_since_contact > 14:
            health.risk_factors.append(f"No contact in {metrics.days_since_contact} days")
        
        if metrics.active_quotes > 0 and metrics.days_since_contact > 7:
            health.risk_factors.append("Active quote but going quiet")
        
        if metrics.lost_quotes > metrics.won_quotes and metrics.total_quotes > 2:
            health.risk_factors.append("Low historical conversion rate")
        
        if health.trend == EngagementTrend.DECLINING:
            health.risk_factors.append("Engagement trending down")
        
        # Opportunities
        if metrics.multi_channel:
            health.opportunities.append("Multi-channel engagement - highly engaged")
        
        if metrics.messages_last_7_days > 2:
            health.opportunities.append("Very active this week - good time for quote")
        
        if metrics.active_quotes > 0 and metrics.won_quotes > 0:
            health.opportunities.append("Repeat customer with active quote")
        
        # Recommended action
        if health.risk_level == RiskLevel.CHURNING:
            health.recommended_action = "Urgent re-engagement needed"
        elif health.risk_level == RiskLevel.AT_RISK:
            health.recommended_action = "Schedule check-in call"
        elif health.trend == EngagementTrend.IMPROVING:
            health.recommended_action = "Capitalize on momentum - propose next step"
        elif metrics.active_quotes > 0:
            health.recommended_action = "Follow up on active quote"
        else:
            health.recommended_action = "Maintain relationship"
    
    def generate_health_report(self) -> Dict[str, Any]:
        """Generate overall health report for all customers."""
        all_health = self.get_all_customer_health()
        
        if not all_health:
            return {"total_customers": 0}
        
        report = {
            "total_customers": len(all_health),
            "avg_score": sum(h.score for h in all_health) / len(all_health),
            "by_risk_level": {},
            "by_trend": {},
            "at_risk_customers": [],
        }
        
        for level in RiskLevel:
            count = sum(1 for h in all_health if h.risk_level == level)
            report["by_risk_level"][level.value] = count
        
        for trend in EngagementTrend:
            count = sum(1 for h in all_health if h.trend == trend)
            report["by_trend"][trend.value] = count
        
        # Top at-risk
        at_risk = [h for h in all_health if h.risk_level in [RiskLevel.AT_RISK, RiskLevel.CHURNING]]
        at_risk.sort(key=lambda h: h.score)
        report["at_risk_customers"] = [h.to_summary() for h in at_risk[:5]]
        
        return report


# Singleton
_scorer: Optional[HealthScorer] = None


def get_scorer() -> HealthScorer:
    """Get singleton health scorer."""
    global _scorer
    if _scorer is None:
        _scorer = HealthScorer()
    return _scorer


def run_health_check() -> Dict[str, Any]:
    """
    Run customer health check (called by dream mode).
    
    Returns summary report.
    """
    scorer = get_scorer()
    report = scorer.generate_health_report()
    
    # Send alert if customers are churning
    churning = report.get("by_risk_level", {}).get("churning", 0)
    at_risk = report.get("by_risk_level", {}).get("at_risk", 0)
    
    if churning > 0 or at_risk > 2:
        _send_health_alert(report)
    
    return report


def _send_health_alert(report: Dict[str, Any]) -> bool:
    """Send Telegram alert for concerning health levels."""
    try:
        import requests
        
        telegram_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
        chat_id = os.environ.get("ADMIN_TELEGRAM_ID", os.environ.get("RUSHABH_TELEGRAM_ID", ""))
        
        if not telegram_token:
            return False
        
        churning = report.get("by_risk_level", {}).get("churning", 0)
        at_risk = report.get("by_risk_level", {}).get("at_risk", 0)
        
        message = f"⚠️ *Customer Health Alert*\n"
        message += f"━━━━━━━━━━━━━━━\n"
        message += f"🔴 Churning: {churning}\n"
        message += f"🟠 At Risk: {at_risk}\n\n"
        
        if report.get("at_risk_customers"):
            message += "*Needs Attention:*\n"
            for summary in report["at_risk_customers"][:3]:
                message += f"{summary}\n\n"
        
        message += "_Use /health for full report_"
        
        response = requests.post(
            f"https://api.telegram.org/bot{telegram_token}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": message,
                "parse_mode": "Markdown",
            },
            timeout=10,
        )
        
        return response.ok
        
    except Exception as e:
        print(f"[customer_health] Alert error: {e}")
        return False


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Customer Health Scoring")
    parser.add_argument("--report", action="store_true", help="Generate health report")
    parser.add_argument("--at-risk", action="store_true", help="Show at-risk customers")
    parser.add_argument("--customer", help="Check specific customer email")
    parser.add_argument("--alert", action="store_true", help="Send test alert")
    args = parser.parse_args()
    
    scorer = get_scorer()
    
    if args.report:
        report = scorer.generate_health_report()
        print("\n📊 Customer Health Report")
        print("=" * 50)
        print(f"Total customers: {report['total_customers']}")
        print(f"Average score: {report.get('avg_score', 0):.0f}/100")
        print(f"\nBy Risk Level:")
        for level, count in report.get("by_risk_level", {}).items():
            print(f"  {level}: {count}")
        print(f"\nBy Trend:")
        for trend, count in report.get("by_trend", {}).items():
            print(f"  {trend}: {count}")
    
    elif args.at_risk:
        at_risk = scorer.get_at_risk_customers()
        print(f"\n⚠️ At-Risk Customers ({len(at_risk)})")
        print("=" * 50)
        for h in at_risk:
            print(h.to_summary())
            print()
    
    elif args.customer:
        health = scorer.get_customer_health(args.customer)
        print(f"\n📊 Health: {args.customer}")
        print("=" * 50)
        print(json.dumps(health.to_dict(), indent=2, default=str))
    
    elif args.alert:
        report = scorer.generate_health_report()
        success = _send_health_alert(report)
        print(f"Alert sent: {'✅' if success else '❌'}")
    
    else:
        parser.print_help()
