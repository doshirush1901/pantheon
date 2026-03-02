#!/usr/bin/env python3
"""
CAMPAIGN SELF-EVALUATOR
=======================

Ira's self-reflection engine for drip campaigns. She asks herself
hard questions about why leads aren't replying, analyzes patterns
in successful vs failed emails, and generates concrete strategies
for improvement.

This is the "thinking" part. The autonomous_drip_engine sends emails.
This module asks: "How am I doing? What can I do better?"

The output feeds into drip_dream_reflection.py which runs during
Ira's nightly dream cycle to generate new ideas.

Key questions Ira asks herself:
    - Why are they not replying to me?
    - What did I do wrong?
    - How can I do the right things?
    - What can I do to get them to reply?
    - How do I sound more interesting?
    - How can I sound more technical?
    - What patterns do I see in replies vs silence?

Usage:
    from campaign_self_evaluator import CampaignSelfEvaluator, run_evaluation

    evaluator = CampaignSelfEvaluator()
    report = evaluator.full_evaluation()
    strategies = evaluator.generate_new_strategies(report)
"""

import json
import logging
import os
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any

logger = logging.getLogger("ira.campaign_evaluator")

SKILL_DIR = Path(__file__).parent
SKILLS_DIR = SKILL_DIR.parent
AGENT_DIR = SKILLS_DIR.parent
PROJECT_ROOT = AGENT_DIR.parent.parent.parent

env_file = PROJECT_ROOT / ".env"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        if line.strip() and not line.startswith('#') and '=' in line:
            key, _, value = line.partition('=')
            os.environ.setdefault(key.strip(), value.strip().strip('"'))

BATCH_HISTORY_FILE = PROJECT_ROOT / "data" / "drip_batch_history.jsonl"
SELF_EVAL_FILE = PROJECT_ROOT / "data" / "drip_self_evaluation.json"
STRATEGY_FILE = PROJECT_ROOT / "data" / "drip_strategies.json"
EVAL_HISTORY_FILE = PROJECT_ROOT / "data" / "drip_eval_history.jsonl"
CAMPAIGN_STATE_FILE = PROJECT_ROOT / "data" / "european_campaign_state.json"

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


@dataclass
class EvaluationReport:
    """Ira's self-evaluation report."""
    timestamp: str
    period_days: int

    # Raw metrics
    total_sent: int = 0
    total_replies: int = 0
    reply_rate: float = 0.0
    engagement_rate: float = 0.0
    bounce_rate: float = 0.0

    # Breakdown
    engaged_replies: int = 0
    polite_declines: int = 0
    auto_replies: int = 0
    bounces: int = 0
    silent: int = 0

    # Pattern analysis
    best_performing_stage: Optional[int] = None
    worst_performing_stage: Optional[int] = None
    best_performing_industry: Optional[str] = None
    best_performing_country: Optional[str] = None
    best_subject_patterns: List[str] = field(default_factory=list)

    # Self-reflection
    self_score: int = 0
    what_went_wrong: List[str] = field(default_factory=list)
    what_went_right: List[str] = field(default_factory=list)
    hypotheses: List[str] = field(default_factory=list)
    improvement_ideas: List[str] = field(default_factory=list)

    # Companies
    replied_companies: List[str] = field(default_factory=list)
    silent_companies: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class Strategy:
    """A drip strategy generated from self-evaluation."""
    id: str
    name: str
    description: str
    tactics: List[str]
    target_reply_rate: float
    generated_at: str
    source: str  # "self_evaluation", "dream_reflection", "rushabh_feedback"
    status: str = "proposed"  # "proposed", "active", "retired", "failed"
    results: Optional[Dict] = None

    def to_dict(self) -> Dict:
        return asdict(self)


class CampaignSelfEvaluator:
    """
    Ira's campaign self-evaluation engine.

    She analyzes her drip performance, identifies patterns,
    asks herself hard questions, and generates strategies.
    """

    def __init__(self):
        self.batch_history = self._load_batch_history()
        self.campaign_state = self._load_campaign_state()

    def _load_batch_history(self) -> List[Dict]:
        batches = []
        if BATCH_HISTORY_FILE.exists():
            try:
                for line in BATCH_HISTORY_FILE.read_text().strip().split("\n"):
                    if line.strip():
                        batches.append(json.loads(line))
            except Exception:
                pass
        return batches

    def _load_campaign_state(self) -> Dict:
        if CAMPAIGN_STATE_FILE.exists():
            try:
                return json.loads(CAMPAIGN_STATE_FILE.read_text())
            except Exception:
                pass
        return {}

    def full_evaluation(self, period_days: int = 30) -> EvaluationReport:
        """
        Run a comprehensive self-evaluation.

        Analyzes all batches from the last `period_days`, computes metrics,
        identifies patterns, and generates self-reflection.
        """
        cutoff = (datetime.now() - timedelta(days=period_days)).isoformat()
        recent = [b for b in self.batch_history if b.get("sent_at", "") > cutoff]

        report = EvaluationReport(
            timestamp=datetime.now().isoformat(),
            period_days=period_days,
        )

        if not recent:
            report.what_went_wrong = ["I haven't sent any emails yet. I need to start."]
            return report

        # Aggregate metrics
        all_leads = []
        for batch in recent:
            all_leads.extend(batch.get("leads", []))

        report.total_sent = len(all_leads)

        for lead in all_leads:
            quality = lead.get("reply_quality", "")
            if lead.get("reply_received"):
                report.total_replies += 1
                if quality == "engaged":
                    report.engaged_replies += 1
                    report.replied_companies.append(lead.get("company", ""))
                elif quality == "polite_decline":
                    report.polite_declines += 1
                elif quality == "auto_reply":
                    report.auto_replies += 1
                elif quality == "bounce":
                    report.bounces += 1
            else:
                report.silent += 1
                report.silent_companies.append(lead.get("company", ""))

        if report.total_sent > 0:
            report.reply_rate = report.total_replies / report.total_sent
            report.engagement_rate = report.engaged_replies / report.total_sent
            report.bounce_rate = report.bounces / report.total_sent

        # Deduplicate company lists
        report.replied_companies = list(set(report.replied_companies))
        report.silent_companies = list(set(report.silent_companies))[:30]

        # Pattern analysis by stage
        stage_stats = {}
        for lead in all_leads:
            stage = lead.get("stage", 0)
            if stage not in stage_stats:
                stage_stats[stage] = {"sent": 0, "replied": 0}
            stage_stats[stage]["sent"] += 1
            if lead.get("reply_received") and lead.get("reply_quality") == "engaged":
                stage_stats[stage]["replied"] += 1

        if stage_stats:
            stage_rates = {
                s: d["replied"] / d["sent"] if d["sent"] > 0 else 0
                for s, d in stage_stats.items()
            }
            if stage_rates:
                report.best_performing_stage = max(stage_rates, key=stage_rates.get)
                report.worst_performing_stage = min(stage_rates, key=stage_rates.get)

        # Score: 0-100
        report.self_score = self._calculate_score(report)

        # Self-reflection (the hard questions)
        report.what_went_wrong = self._analyze_failures(report)
        report.what_went_right = self._analyze_successes(report)
        report.hypotheses = self._generate_hypotheses(report)
        report.improvement_ideas = self._generate_ideas(report)

        # Save
        SELF_EVAL_FILE.parent.mkdir(parents=True, exist_ok=True)
        SELF_EVAL_FILE.write_text(json.dumps(report.to_dict(), indent=2))

        # Append to history
        EVAL_HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(EVAL_HISTORY_FILE, "a") as f:
            f.write(json.dumps({
                "timestamp": report.timestamp,
                "score": report.self_score,
                "reply_rate": report.reply_rate,
                "total_sent": report.total_sent,
                "engaged": report.engaged_replies,
            }) + "\n")

        return report

    def _calculate_score(self, report: EvaluationReport) -> int:
        score = 0.0

        # Reply rate component (0-40 points)
        # Industry average cold email reply rate is ~1-5%
        if report.reply_rate >= 0.20:
            score += 40
        elif report.reply_rate >= 0.10:
            score += 30
        elif report.reply_rate >= 0.05:
            score += 20
        elif report.reply_rate >= 0.02:
            score += 10
        elif report.reply_rate > 0:
            score += 5

        # Engagement quality (0-30 points)
        if report.total_replies > 0:
            engaged_ratio = report.engaged_replies / report.total_replies
            score += engaged_ratio * 30

        # Volume consistency (0-15 points)
        if report.total_sent >= 30:
            score += 15
        elif report.total_sent >= 15:
            score += 10
        elif report.total_sent >= 5:
            score += 5

        # Low bounce rate bonus (0-15 points)
        if report.bounce_rate == 0:
            score += 15
        elif report.bounce_rate < 0.05:
            score += 10
        elif report.bounce_rate < 0.10:
            score += 5

        return min(100, int(score))

    def _analyze_failures(self, report: EvaluationReport) -> List[str]:
        """Ask: What went wrong?"""
        failures = []

        if report.reply_rate == 0 and report.total_sent > 5:
            failures.append(
                "Zero replies from {n} emails. My emails might be going to spam, "
                "or my subject lines are not compelling enough to even get opened.".format(n=report.total_sent)
            )
        elif report.reply_rate < 0.02 and report.total_sent > 10:
            failures.append(
                "Almost no replies. I might be too generic — these are European "
                "thermoformers who get pitched by equipment suppliers regularly. "
                "I need to stand out."
            )

        if report.bounces > 0:
            failures.append(
                f"{report.bounces} emails bounced. I'm sending to bad addresses. "
                "I need to verify emails before sending."
            )

        if report.auto_replies > report.engaged_replies:
            failures.append(
                "More auto-replies than real replies. I might be sending at bad "
                "times (holidays, weekends) or to generic info@ addresses."
            )

        if report.polite_declines > report.engaged_replies:
            failures.append(
                "More polite declines than engaged replies. My value proposition "
                "isn't resonating. I need to be more specific about what "
                "Machinecraft can do for THEIR specific situation."
            )

        if report.worst_performing_stage is not None:
            failures.append(
                f"Stage {report.worst_performing_stage} emails are performing worst. "
                "I should rethink the content and approach for this stage."
            )

        return failures

    def _analyze_successes(self, report: EvaluationReport) -> List[str]:
        successes = []

        if report.engaged_replies > 0:
            successes.append(
                f"{report.engaged_replies} companies showed real interest: "
                f"{', '.join(report.replied_companies[:5])}. "
                "I should study what made these emails work."
            )

        if report.best_performing_stage is not None and report.engaged_replies > 0:
            successes.append(
                f"Stage {report.best_performing_stage} emails got the best response. "
                "The content/approach at this stage is working."
            )

        if report.reply_rate >= 0.10:
            successes.append(
                f"Reply rate of {report.reply_rate:.1%} is above industry average "
                "for cold outreach. My personalization is working."
            )

        return successes

    def _generate_hypotheses(self, report: EvaluationReport) -> List[str]:
        """Generate hypotheses about why things are/aren't working."""
        hypotheses = []

        if report.reply_rate < 0.05:
            hypotheses.extend([
                "HYPOTHESIS: My subject lines are too generic. European buyers "
                "see 'thermoforming solutions' pitches daily. I need hooks that "
                "reference their specific situation (expansion, new plant, etc.)",

                "HYPOTHESIS: I'm not leveraging enough social proof. Mentioning "
                "specific European customers (with permission) could build trust.",

                "HYPOTHESIS: My emails are too long. European business culture "
                "values brevity. I should try shorter, punchier emails.",

                "HYPOTHESIS: I should try sending from Rushabh directly for "
                "high-priority leads. A CEO-to-CEO email might get more attention.",

                "HYPOTHESIS: I need to sound more technical and less salesy. "
                "Engineers respond to specs and data, not marketing language.",
            ])

        if report.engaged_replies > 0 and report.silent > report.engaged_replies * 3:
            hypotheses.append(
                "HYPOTHESIS: The companies that replied might share common traits "
                "(industry, size, recent expansion). I should segment and target "
                "similar companies more aggressively."
            )

        if report.polite_declines > 0:
            hypotheses.append(
                "HYPOTHESIS: Companies declining might not be in a buying cycle. "
                "I should research their capex plans and time my outreach to "
                "when they're actually evaluating equipment."
            )

        return hypotheses

    def _generate_ideas(self, report: EvaluationReport) -> List[str]:
        """Generate concrete improvement ideas."""
        ideas = []

        ideas.extend([
            "Try A/B testing: send half the batch with a question-based subject "
            "line and half with a news-hook subject line. Compare reply rates.",

            "For the next batch, research each company's recent news (Iris agent) "
            "and lead with that. Show I'm paying attention to THEM, not just pitching.",

            "Try a 'breakup email' for leads who haven't replied after 3 stages: "
            "'I won't bother you again, but here's what you'd be missing...'",

            "Include a specific, relevant case study number in the subject line: "
            "'How [similar company] saved 18% on cycle times'",
        ])

        if report.reply_rate < 0.05:
            ideas.extend([
                "RADICAL: Try a completely different format — a short 3-line email "
                "with just one question. No pitch, just curiosity.",

                "Try sending at different times. Test 7 AM (before their day starts) "
                "vs 2 PM (post-lunch lull) vs 5 PM (end of day review).",

                "Include a link to a short video (factory tour, machine demo) "
                "instead of a wall of text.",
            ])

        if report.bounce_rate > 0.05:
            ideas.append(
                "URGENT: Implement email verification before sending. "
                "Use a service like ZeroBounce or NeverBounce."
            )

        return ideas

    def generate_new_strategies(self, report: Optional[EvaluationReport] = None) -> List[Strategy]:
        """
        Use LLM to generate new drip strategies based on evaluation.

        This is the "wake up with new ideas" part — Ira synthesizes
        her self-evaluation into concrete, actionable strategies.
        """
        if report is None:
            report = self.full_evaluation()

        if not OPENAI_AVAILABLE:
            return self._generate_fallback_strategies(report)

        try:
            client = openai.OpenAI()
            result = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": (
                        "You are Ira, an AI sales agent for Machinecraft Technologies "
                        "(thermoforming machines, CNC routers). You've been running drip "
                        "email campaigns to European leads and you're evaluating your "
                        "performance. Based on your self-evaluation, generate 3 concrete "
                        "strategies for your next batch of emails.\n\n"
                        "Each strategy should have:\n"
                        "- A short name\n"
                        "- A description of the approach\n"
                        "- 3-5 specific tactics\n"
                        "- A target reply rate improvement\n\n"
                        "Be specific and actionable. Think like a growth hacker who "
                        "also deeply understands B2B industrial sales.\n\n"
                        "Output as JSON array of objects with keys: "
                        "name, description, tactics (array), target_reply_rate_pct"
                    )},
                    {"role": "user", "content": (
                        f"MY SELF-EVALUATION:\n"
                        f"Score: {report.self_score}/100\n"
                        f"Reply rate: {report.reply_rate:.1%}\n"
                        f"Engaged replies: {report.engaged_replies}\n"
                        f"Total sent: {report.total_sent}\n"
                        f"Bounces: {report.bounces}\n\n"
                        f"WHAT WENT WRONG:\n"
                        + "\n".join(f"- {w}" for w in report.what_went_wrong[:5])
                        + f"\n\nWHAT WENT RIGHT:\n"
                        + "\n".join(f"- {w}" for w in report.what_went_right[:5])
                        + f"\n\nMY HYPOTHESES:\n"
                        + "\n".join(f"- {h}" for h in report.hypotheses[:5])
                        + f"\n\nGenerate 3 strategies for my next batch."
                    )},
                ],
                temperature=0.7,
                max_tokens=2000,
                response_format={"type": "json_object"},
            )

            content = result.choices[0].message.content
            data = json.loads(content)
            strategies_data = data.get("strategies", data.get("results", []))
            if isinstance(data, list):
                strategies_data = data

            strategies = []
            for i, s in enumerate(strategies_data[:3]):
                strategy = Strategy(
                    id=f"strat_{datetime.now().strftime('%Y%m%d')}_{i}",
                    name=s.get("name", f"Strategy {i+1}"),
                    description=s.get("description", ""),
                    tactics=s.get("tactics", []),
                    target_reply_rate=s.get("target_reply_rate_pct", 10) / 100,
                    generated_at=datetime.now().isoformat(),
                    source="self_evaluation",
                )
                strategies.append(strategy)

            # Save strategies
            self._save_strategies(strategies)
            return strategies

        except Exception as e:
            logger.warning(f"LLM strategy generation failed: {e}")
            return self._generate_fallback_strategies(report)

    def _generate_fallback_strategies(self, report: EvaluationReport) -> List[Strategy]:
        """Generate strategies without LLM."""
        strategies = []

        if report.reply_rate < 0.05:
            strategies.append(Strategy(
                id=f"strat_{datetime.now().strftime('%Y%m%d')}_0",
                name="Radical Brevity",
                description="Switch to ultra-short 3-line emails with a single question",
                tactics=[
                    "Subject: one specific question about their operation",
                    "Body: 3 lines max — context, question, sign-off",
                    "No attachments, no links, no bullet points",
                    "Send Tuesday/Wednesday 9 AM their local time",
                ],
                target_reply_rate=0.08,
                generated_at=datetime.now().isoformat(),
                source="self_evaluation",
            ))

        strategies.append(Strategy(
            id=f"strat_{datetime.now().strftime('%Y%m%d')}_1",
            name="News-Hook Personalization",
            description="Lead every email with a specific news item about the company",
            tactics=[
                "Use Iris agent to find recent news for each lead",
                "Open with: 'Saw your [news]. Congrats/interesting...'",
                "Connect the news to a Machinecraft capability",
                "End with a specific, easy-to-answer question",
            ],
            target_reply_rate=0.12,
            generated_at=datetime.now().isoformat(),
            source="self_evaluation",
        ))

        strategies.append(Strategy(
            id=f"strat_{datetime.now().strftime('%Y%m%d')}_2",
            name="Technical Authority",
            description="Position emails as technical insights, not sales pitches",
            tactics=[
                "Share a specific technical insight relevant to their industry",
                "Include a data point (cycle time, energy savings, etc.)",
                "Offer a free technical consultation, not a sales call",
                "Sign off as 'Ira, Technical Sales - Machinecraft'",
            ],
            target_reply_rate=0.10,
            generated_at=datetime.now().isoformat(),
            source="self_evaluation",
        ))

        self._save_strategies(strategies)
        return strategies

    def _save_strategies(self, strategies: List[Strategy]):
        existing = {}
        if STRATEGY_FILE.exists():
            try:
                existing = json.loads(STRATEGY_FILE.read_text())
            except Exception:
                pass

        existing["generated_at"] = datetime.now().isoformat()
        existing["proposed_strategies"] = [s.to_dict() for s in strategies]

        # Pick the first one as active by default
        if strategies:
            existing["current_strategy"] = strategies[0].name
            strategies[0].status = "active"

        STRATEGY_FILE.parent.mkdir(parents=True, exist_ok=True)
        STRATEGY_FILE.write_text(json.dumps(existing, indent=2))

    def get_trend(self) -> Dict[str, Any]:
        """Get performance trend over time (for dream reflection)."""
        history = []
        if EVAL_HISTORY_FILE.exists():
            try:
                for line in EVAL_HISTORY_FILE.read_text().strip().split("\n"):
                    if line.strip():
                        history.append(json.loads(line))
            except Exception:
                pass

        if len(history) < 2:
            return {"trend": "insufficient_data", "data_points": len(history)}

        recent = history[-5:]
        scores = [h.get("score", 0) for h in recent]
        rates = [h.get("reply_rate", 0) for h in recent]

        score_trend = scores[-1] - scores[0]
        rate_trend = rates[-1] - rates[0]

        return {
            "trend": "improving" if score_trend > 5 else ("declining" if score_trend < -5 else "stable"),
            "score_change": score_trend,
            "rate_change": round(rate_trend, 4),
            "latest_score": scores[-1],
            "latest_rate": rates[-1],
            "data_points": len(history),
        }


def run_evaluation(period_days: int = 30) -> EvaluationReport:
    """Run a full self-evaluation. Convenience function."""
    evaluator = CampaignSelfEvaluator()
    return evaluator.full_evaluation(period_days)


if __name__ == "__main__":
    import argparse

    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(description="Ira Campaign Self-Evaluator")
    parser.add_argument("--evaluate", action="store_true", help="Run full evaluation")
    parser.add_argument("--strategies", action="store_true", help="Generate new strategies")
    parser.add_argument("--trend", action="store_true", help="Show performance trend")
    parser.add_argument("--days", type=int, default=30, help="Evaluation period")
    args = parser.parse_args()

    evaluator = CampaignSelfEvaluator()

    if args.evaluate:
        report = evaluator.full_evaluation(args.days)
        print(f"\nSelf-Evaluation Report")
        print(f"{'=' * 50}")
        print(f"Score: {report.self_score}/100")
        print(f"Reply rate: {report.reply_rate:.1%}")
        print(f"Engaged: {report.engaged_replies} | Declines: {report.polite_declines} | Bounces: {report.bounces}")
        print(f"\nWhat went wrong:")
        for w in report.what_went_wrong:
            print(f"  - {w}")
        print(f"\nWhat went right:")
        for w in report.what_went_right:
            print(f"  - {w}")
        print(f"\nHypotheses:")
        for h in report.hypotheses:
            print(f"  - {h}")
        print(f"\nImprovement ideas:")
        for i in report.improvement_ideas:
            print(f"  - {i}")

    elif args.strategies:
        strategies = evaluator.generate_new_strategies()
        print(f"\nGenerated {len(strategies)} strategies:")
        for s in strategies:
            print(f"\n  [{s.status.upper()}] {s.name}")
            print(f"  {s.description}")
            for t in s.tactics:
                print(f"    - {t}")

    elif args.trend:
        trend = evaluator.get_trend()
        print(json.dumps(trend, indent=2))

    else:
        parser.print_help()
