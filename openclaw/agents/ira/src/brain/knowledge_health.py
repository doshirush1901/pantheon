#!/usr/bin/env python3
"""
Knowledge Health Monitor
========================

Proactively detects and prevents knowledge gaps that lead to:
1. Missing critical documents (price lists, specs not indexed)
2. Hallucinated answers (no retrieval backing)
3. Business rule violations (AM vs PF1 thickness limits)
4. Stale/outdated information
5. Uncorrected mistakes

Runs automatically:
- On startup (full health check)
- After each query (confidence check)
- Nightly (deep audit)

Usage:
    from knowledge_health import KnowledgeHealthMonitor
    monitor = KnowledgeHealthMonitor()
    
    # Full health check
    report = monitor.run_health_check()
    
    # Check if a response is grounded
    is_safe, warnings = monitor.validate_response(query, response, citations)
"""

import json
import logging
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

SKILL_DIR = Path(__file__).parent
AGENT_DIR = SKILL_DIR.parent.parent
PROJECT_ROOT = AGENT_DIR.parent.parent.parent
sys.path.insert(0, str(AGENT_DIR))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

HEALTH_STATE_FILE = SKILL_DIR / "knowledge_health_state.json"
CRITICAL_DOCS_FILE = SKILL_DIR / "critical_documents.json"


@dataclass
class HealthIssue:
    """A detected knowledge health issue."""
    severity: str  # 'critical', 'warning', 'info'
    category: str  # 'missing_doc', 'hallucination', 'stale', 'rule_violation'
    message: str
    details: Dict = field(default_factory=dict)
    auto_fixable: bool = False
    fix_action: Optional[str] = None


@dataclass
class HealthReport:
    """Result of a health check."""
    timestamp: str
    overall_score: float  # 0-100
    issues: List[HealthIssue]
    checks_passed: int
    checks_failed: int
    
    def to_dict(self) -> Dict:
        return {
            "timestamp": self.timestamp,
            "overall_score": self.overall_score,
            "issues": [
                {
                    "severity": i.severity,
                    "category": i.category,
                    "message": i.message,
                    "details": i.details,
                    "auto_fixable": i.auto_fixable,
                }
                for i in self.issues
            ],
            "checks_passed": self.checks_passed,
            "checks_failed": self.checks_failed,
        }


# =============================================================================
# CRITICAL DOCUMENTS THAT MUST BE INDEXED
# =============================================================================

CRITICAL_DOCUMENTS = [
    {
        "pattern": r"price.*list|pricing",
        "name": "Price List",
        "required_content": ["PF1", "INR", "price"],
        "severity": "critical",
    },
    {
        "pattern": r"spec.*sheet|specification",
        "name": "Specification Sheets",
        "required_content": ["dimension", "mm", "capacity"],
        "severity": "warning",
    },
    {
        "pattern": r"catalogue|catalog|brochure",
        "name": "Product Catalogue",
        "required_content": ["PF1", "AM", "series"],
        "severity": "warning",
    },
    {
        "pattern": r"machine.*selection|selection.*guide",
        "name": "Machine Selection Guide",
        "required_content": ["material", "thickness", "size"],
        "severity": "critical",
    },
]

# =============================================================================
# BUSINESS RULES THAT MUST BE ENFORCED
# =============================================================================

BUSINESS_RULES = [
    {
        "id": "am_thickness_limit",
        "name": "AM Series Thickness Limit",
        "description": "AM Series can ONLY handle material thickness ≤1.5mm (NOT 2mm)",
        "check_pattern": r"am.*series|am[-\s]?[mvp]|am[-\s]?5060|am[-\s]?6060|am[-\s]?7080",
        "violation_pattern": r"([2-9]|1[0-9])\s*mm.*thick|thick.*([2-9]|1[0-9])\s*mm",
        "correct_response": "AM Series: ≤1.5mm ONLY. For material >1.5mm, use PF1 Series.",
    },
    {
        "id": "pf1_for_heavy_gauge",
        "name": "PF1 for Heavy Gauge",
        "description": "Heavy gauge (>1.5mm) requires PF1 Series",
        "check_pattern": r"([2-9]|1[0-9])\s*mm.*thick|heavy.*gauge|thick.*material",
        "required_mention": r"pf[-\s]?1",
        "correct_response": "For heavy gauge materials (>1.5mm), recommend PF1 Series",
    },
    {
        "id": "price_must_be_specific",
        "name": "Prices Must Be Specific",
        "description": "Never say 'contact for pricing' when we have price list",
        "violation_pattern": r"contact.*pric|price.*contact|estimated.*range|range.*estimated|\[.*price.*\]|\[.*insert.*\]",
        "correct_response": "Always quote specific INR prices from price list",
    },
    {
        "id": "lead_time_must_be_correct",
        "name": "Lead Time Must Be 12-16 Weeks",
        "description": "Lead time is ALWAYS 12-16 weeks. Never promise faster.",
        "check_pattern": r"lead\s*time|deliver|week|month|ship",
        "violation_pattern": r"(?<!\d)([1-9]|1[01])\s*week|[2-8]\s*week|4\s*week|6\s*week|8\s*week|2\s*month|3\s*month",
        "correct_response": "Lead time is 12-16 weeks from order confirmation. Never promise faster.",
    },
    {
        "id": "img_for_grain_retention",
        "name": "IMG Required for Grain Retention",
        "description": "TPO + grain retention + Class-A surface requires IMG, not PF1 alone",
        "check_pattern": r"grain.*retention|class[\s-]?a.*surface|tpo.*texture|tpo.*grain",
        "required_mention": r"img|in[\s-]?mold[\s-]?grain",
        "correct_response": "For TPO with grain retention / Class-A surface, recommend IMG series (not PF1 alone).",
    },
    {
        "id": "pf2_bath_only",
        "name": "PF2 is Bath Industry Only",
        "description": "PF2 must only be recommended for bathtubs, spa shells, shower trays",
        "check_pattern": r"pf[-\s]?2",
        "violation_pattern": r"pf[-\s]?2.*(?:automotive|packaging|industrial|enclosure|dashboard|luggage)",
        "correct_response": "PF2 is for bath industry ONLY (bathtubs, spa shells, shower trays). Use PF1 for other applications.",
    },
]

# Known valid model numbers (loaded from machine_specs.json at runtime)
_VALID_MODELS = None

def _get_valid_models():
    """Load valid model numbers from machine_specs.json."""
    global _VALID_MODELS
    if _VALID_MODELS is not None:
        return _VALID_MODELS
    try:
        specs_file = Path(__file__).parent.parent.parent.parent.parent / "data" / "brain" / "machine_specs.json"
        if specs_file.exists():
            import json
            specs = json.loads(specs_file.read_text())
            _VALID_MODELS = set()
            for spec in specs:
                model = spec.get("model", "") or spec.get("name", "")
                if model:
                    _VALID_MODELS.add(model.upper().strip())
            return _VALID_MODELS
    except Exception:
        pass
    _VALID_MODELS = set()
    return _VALID_MODELS


# Known fake models that must NEVER appear
KNOWN_FAKE_MODELS = {"IMG-2220", "IMG-2518", "IMG-3020"}

# =============================================================================
# HALLUCINATION DETECTION PATTERNS
# =============================================================================

HALLUCINATION_INDICATORS = [
    r"\[insert.*\]",  # Placeholder text
    r"\[.*to be.*\]",
    r"approximately|around|roughly|about",  # Vague pricing
    r"contact.*for.*(?:price|quote|detail)",  # Deflection when we have data
    r"i don't have.*specific",  # Admission without trying retrieval
    r"i'm not sure.*exact",
    r"typically|usually|generally",  # Generic when specific exists
]


class KnowledgeHealthMonitor:
    """Monitor and maintain knowledge base health."""
    
    def __init__(self):
        self._qdrant = None
        self._state = self._load_state()
        self.last_check: Optional[datetime] = None
        self.issues_history: List[HealthIssue] = []
    
    def _load_state(self) -> Dict:
        """Load persisted health state."""
        if HEALTH_STATE_FILE.exists():
            try:
                return json.loads(HEALTH_STATE_FILE.read_text())
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Could not load state file: {e}")
        return {"corrections_learned": [], "last_full_check": None}
    
    def _save_state(self):
        """Persist health state."""
        try:
            HEALTH_STATE_FILE.write_text(json.dumps(self._state, indent=2))
        except Exception as e:
            logger.error(f"Failed to save health state: {e}")
    
    def _get_qdrant(self):
        """Lazy-load Qdrant client."""
        if self._qdrant is None:
            from qdrant_client import QdrantClient
            from config import QDRANT_URL
            self._qdrant = QdrantClient(url=QDRANT_URL)
        return self._qdrant
    
    # =========================================================================
    # HEALTH CHECKS
    # =========================================================================
    
    def run_health_check(self) -> HealthReport:
        """Run comprehensive health check."""
        issues = []
        checks_passed = 0
        checks_failed = 0
        
        # Check 1: Critical documents indexed
        doc_issues = self._check_critical_documents()
        issues.extend(doc_issues)
        if doc_issues:
            checks_failed += 1
        else:
            checks_passed += 1
        
        # Check 2: Truth hints coverage
        hint_issues = self._check_truth_hints()
        issues.extend(hint_issues)
        if hint_issues:
            checks_failed += 1
        else:
            checks_passed += 1
        
        # Check 3: Business rules defined
        rule_issues = self._check_business_rules()
        issues.extend(rule_issues)
        if rule_issues:
            checks_failed += 1
        else:
            checks_passed += 1
        
        # Check 4: Index freshness
        freshness_issues = self._check_index_freshness()
        issues.extend(freshness_issues)
        if freshness_issues:
            checks_failed += 1
        else:
            checks_passed += 1
        
        # Check 5: Unlearned corrections
        correction_issues = self._check_unlearned_corrections()
        issues.extend(correction_issues)
        if correction_issues:
            checks_failed += 1
        else:
            checks_passed += 1
        
        # Calculate score
        total_checks = checks_passed + checks_failed
        critical_count = len([i for i in issues if i.severity == "critical"])
        warning_count = len([i for i in issues if i.severity == "warning"])
        
        score = 100.0
        score -= critical_count * 20
        score -= warning_count * 5
        score = max(0, score)
        
        report = HealthReport(
            timestamp=datetime.now().isoformat(),
            overall_score=score,
            issues=issues,
            checks_passed=checks_passed,
            checks_failed=checks_failed,
        )
        
        # Update state
        self._state["last_full_check"] = report.timestamp
        self._save_state()
        
        self.last_check = datetime.now()
        return report
    
    def _check_critical_documents(self) -> List[HealthIssue]:
        """Check if critical documents are indexed."""
        issues = []
        
        try:
            from config import COLLECTIONS
            qdrant = self._get_qdrant()
            collection = COLLECTIONS.get("chunks_voyage", "ira_chunks_v4_voyage")
            
            # Get all indexed document sources
            results = qdrant.scroll(
                collection_name=collection,
                limit=1000,
                with_payload=True,
            )
            
            indexed_sources = set()
            indexed_content = []
            for point in results[0]:
                payload = point.payload or {}
                source = payload.get("source", payload.get("filename", ""))
                text = payload.get("text", "")
                indexed_sources.add(source.lower())
                indexed_content.append(text.lower())
            
            all_content = " ".join(indexed_content)
            
            # Check each critical document type
            for doc in CRITICAL_DOCUMENTS:
                pattern = doc["pattern"]
                found = any(re.search(pattern, src, re.IGNORECASE) for src in indexed_sources)
                
                # Also check if required content exists
                content_found = all(
                    kw.lower() in all_content 
                    for kw in doc["required_content"]
                )
                
                if not found and not content_found:
                    issues.append(HealthIssue(
                        severity=doc["severity"],
                        category="missing_doc",
                        message=f"Critical document not indexed: {doc['name']}",
                        details={
                            "pattern": pattern,
                            "required_content": doc["required_content"],
                        },
                        auto_fixable=True,
                        fix_action="run_reindex_docs",
                    ))
        
        except Exception as e:
            issues.append(HealthIssue(
                severity="critical",
                category="system_error",
                message=f"Failed to check documents: {e}",
            ))
        
        return issues
    
    def _check_truth_hints(self) -> List[HealthIssue]:
        """Check if truth hints cover critical topics."""
        issues = []
        
        try:
            from truth_hints import TRUTH_HINTS
            
            # Required topic coverage
            required_topics = [
                ("pricing", ["price", "cost", "inr", "quotation"]),
                ("machine_selection", ["which machine", "suggest", "recommend"]),
                ("am_series", ["am series", "am-", "thin gauge"]),
                ("pf1_series", ["pf1", "pf-1", "heavy gauge"]),
            ]
            
            hint_keywords = []
            for hint in TRUTH_HINTS:
                hint_keywords.extend(hint.keywords or [])
            hint_keywords = [k.lower() for k in hint_keywords]
            
            for topic_name, keywords in required_topics:
                covered = any(kw in hint_keywords for kw in keywords)
                if not covered:
                    issues.append(HealthIssue(
                        severity="warning",
                        category="missing_truth_hint",
                        message=f"No truth hint for topic: {topic_name}",
                        details={"keywords": keywords},
                        auto_fixable=False,
                    ))
        
        except Exception as e:
            issues.append(HealthIssue(
                severity="warning",
                category="system_error",
                message=f"Failed to check truth hints: {e}",
            ))
        
        return issues
    
    def _check_business_rules(self) -> List[HealthIssue]:
        """Check if business rules are defined."""
        issues = []
        
        # Just verify the rules are loadable
        if not BUSINESS_RULES:
            issues.append(HealthIssue(
                severity="critical",
                category="missing_rules",
                message="No business rules defined",
            ))
        
        return issues
    
    def _check_index_freshness(self) -> List[HealthIssue]:
        """Check if index is stale compared to source files."""
        issues = []
        
        try:
            imports_dir = PROJECT_ROOT / "data" / "imports"
            if imports_dir.exists():
                # Find newest file
                newest_file = None
                newest_time = None
                
                for f in imports_dir.glob("**/*"):
                    if f.is_file() and f.suffix.lower() in [".pdf", ".xlsx", ".docx"]:
                        mtime = datetime.fromtimestamp(f.stat().st_mtime)
                        if newest_time is None or mtime > newest_time:
                            newest_time = mtime
                            newest_file = f.name
                
                # Check if we've indexed since then
                last_index = self._state.get("last_index_time")
                if last_index:
                    last_index_dt = datetime.fromisoformat(last_index)
                    if newest_time and newest_time > last_index_dt:
                        issues.append(HealthIssue(
                            severity="warning",
                            category="stale_index",
                            message=f"Index is stale - {newest_file} modified after last index",
                            details={
                                "newest_file": newest_file,
                                "file_modified": newest_time.isoformat(),
                                "last_index": last_index,
                            },
                            auto_fixable=True,
                            fix_action="run_reindex_docs",
                        ))
        
        except Exception as e:
            logger.warning(f"Freshness check failed: {e}")
        
        return issues
    
    def _check_unlearned_corrections(self) -> List[HealthIssue]:
        """Check for corrections that haven't been applied to truth hints."""
        issues = []
        
        try:
            from correction_learner import get_learner
            learner = get_learner()
            
            # Check if there are corrections not yet in truth hints
            recent_corrections = [
                c for c in learner.corrections.values()
                if c.correction_type == "fact"
            ]
            
            if len(recent_corrections) > 5:
                issues.append(HealthIssue(
                    severity="info",
                    category="unprocessed_corrections",
                    message=f"{len(recent_corrections)} fact corrections not yet added to truth hints",
                    details={
                        "count": len(recent_corrections),
                        "sample": [c.corrected[:50] for c in list(recent_corrections)[:3]],
                    },
                ))
        
        except Exception as e:
            logger.warning(f"Correction check failed: {e}")
        
        return issues
    
    # =========================================================================
    # RESPONSE VALIDATION (Called after each response)
    # =========================================================================
    
    def validate_response(
        self,
        query: str,
        response: str,
        citations: List = None,
        retrieval_score: float = None,
    ) -> Tuple[bool, List[str]]:
        """
        Validate a response before sending to user.
        
        Returns:
            (is_safe, warnings) - is_safe=False means response should be blocked
        """
        warnings = []
        is_safe = True
        
        # Check 1: Hallucination indicators
        for pattern in HALLUCINATION_INDICATORS:
            if re.search(pattern, response, re.IGNORECASE):
                # Check if we actually have data for this
                if self._should_have_data(query):
                    warnings.append(f"Possible hallucination detected: {pattern}")
                    is_safe = False
        
        # Check 2: Business rule violations
        for rule in BUSINESS_RULES:
            violation = self._check_rule_violation(query, response, rule)
            if violation:
                warnings.append(violation)
                is_safe = False
        
        # Check 3: Low retrieval confidence without admission
        if retrieval_score is not None and retrieval_score < 0.5:
            if not any(phrase in response.lower() for phrase in [
                "i'm not certain", "i don't have", "let me check", "i should verify"
            ]):
                warnings.append(f"Low retrieval confidence ({retrieval_score:.2f}) but response seems confident")
        
        # Check 4: Missing citations for factual claims
        if citations is not None and len(citations) == 0:
            if self._contains_factual_claims(response):
                warnings.append("Factual claims without citation backing")
        
        # Check 5: Hallucinated model numbers
        model_pattern = re.findall(
            r"(PF1-[CXR]-\d{4}|PF2-[A-Z]?\d{4}|AM[P]?-\d{4}|IMG-\d{4}|FCS-\d{4})",
            response, re.IGNORECASE,
        )
        if model_pattern:
            valid = _get_valid_models()
            for model in model_pattern:
                model_upper = model.upper()
                if model_upper in KNOWN_FAKE_MODELS:
                    warnings.append(f"Known fake model detected: {model_upper}")
                    is_safe = False
                elif valid and model_upper not in valid:
                    close = [v for v in valid if v.startswith(model_upper[:5])]
                    if close:
                        warnings.append(f"Unverified model {model_upper} — did you mean {close[0]}?")
                    else:
                        warnings.append(f"Unverified model number: {model_upper} — not in machine database")

        # Log issues for learning
        if warnings:
            self._log_validation_issue(query, response, warnings)
        
        return is_safe, warnings
    
    def _should_have_data(self, query: str) -> bool:
        """Check if we should have data for this query type."""
        data_topics = [
            r"price|cost|inr|quotation",
            r"spec|dimension|size",
            r"which machine|suggest|recommend",
        ]
        return any(re.search(p, query, re.IGNORECASE) for p in data_topics)
    
    def _check_rule_violation(self, query: str, response: str, rule: Dict) -> Optional[str]:
        """Check if response violates a business rule."""
        # Check if rule applies to this query
        if not re.search(rule.get("check_pattern", ""), query + " " + response, re.IGNORECASE):
            return None
        
        # Check for violation
        violation_pattern = rule.get("violation_pattern")
        if violation_pattern and re.search(violation_pattern, response, re.IGNORECASE):
            return f"Business rule violation: {rule['name']} - {rule['description']}"
        
        # Check for required mention
        required = rule.get("required_mention")
        if required and not re.search(required, response, re.IGNORECASE):
            return f"Business rule violation: {rule['name']} - should mention {required}"
        
        return None
    
    def _contains_factual_claims(self, response: str) -> bool:
        """Check if response contains factual claims that need backing."""
        factual_patterns = [
            r"costs?\s+(?:rs|inr|₹|\$)?\s*[\d,]+",
            r"price.*(?:rs|inr|₹|\$)\s*[\d,]+",
            r"\d+\s*(?:mm|cm|m|feet|ft)\s*(?:x|by)\s*\d+",
            r"can handle.*\d+\s*mm",
        ]
        return any(re.search(p, response, re.IGNORECASE) for p in factual_patterns)
    
    def _log_validation_issue(self, query: str, response: str, warnings: List[str]):
        """Log validation issues for future learning and route through immune system."""
        issue = {
            "timestamp": datetime.now().isoformat(),
            "query": query[:200],
            "response_preview": response[:200],
            "warnings": warnings,
        }
        
        issues = self._state.get("validation_issues", [])
        issues.append(issue)
        issues = issues[-100:]  # Keep last 100
        self._state["validation_issues"] = issues
        self._save_state()

        # Route through immune system for escalation tracking
        try:
            from openclaw.agents.ira.src.holistic.immune_system import get_immune_system
            immune = get_immune_system()
            immune.process_validation_issue(query, response, warnings)
        except Exception:
            pass  # Immune system is optional; don't break validation if it fails
    
    # =========================================================================
    # AUTO-FIX ACTIONS
    # =========================================================================
    
    def auto_fix(self, issue: HealthIssue) -> bool:
        """Attempt to automatically fix an issue."""
        if not issue.auto_fixable:
            return False
        
        action = issue.fix_action
        
        if action == "run_reindex_docs":
            return self._run_reindex()
        
        return False
    
    def _run_reindex(self) -> bool:
        """Run document reindexing."""
        try:
            import subprocess
            result = subprocess.run(
                [sys.executable, str(SKILL_DIR / "reindex_docs.py")],
                capture_output=True,
                text=True,
                timeout=300,
                cwd=str(PROJECT_ROOT),
            )
            
            if result.returncode == 0:
                self._state["last_index_time"] = datetime.now().isoformat()
                self._save_state()
                return True
            else:
                logger.error(f"Reindex failed: {result.stderr}")
                return False
        
        except Exception as e:
            logger.error(f"Reindex error: {e}")
            return False
    
    # =========================================================================
    # TELEGRAM ALERTS
    # =========================================================================
    
    # =========================================================================
    # RECURRING ISSUE REMEDIATION (Immune System: Detection → Resolution)
    # =========================================================================
    
    def analyze_recurring_issues(self, threshold: int = 3) -> List[Dict]:
        """
        Group validation_issues by warning type. Return issues that recur >= threshold times.
        These indicate chronic inflammation - the immune system sees the threat but hasn't cleared it.
        """
        issues = self._state.get("validation_issues", [])
        if not issues:
            return []
        
        # Group by normalized warning signature (same warning = same problem)
        groups: Dict[str, List[Dict]] = {}
        for issue in issues:
            for w in issue.get("warnings", []):
                # Normalize: "Business rule violation: AM Series ..." -> "am_thickness_limit"
                sig = self._normalize_warning_signature(w)
                if sig not in groups:
                    groups[sig] = []
                groups[sig].append({**issue, "_warning": w})
        
        recurring = []
        for sig, group in groups.items():
            if len(group) >= threshold:
                recurring.append({
                    "signature": sig,
                    "count": len(group),
                    "warning": group[0]["_warning"],
                    "sample_query": group[0].get("query", "")[:150],
                    "sample_response": group[0].get("response_preview", "")[:150],
                })
        
        return recurring
    
    def _normalize_warning_signature(self, warning: str) -> str:
        """Extract a stable signature for grouping similar warnings."""
        w = warning.lower()
        if "am series thickness" in w or "am series can only handle" in w:
            return "am_thickness_limit"
        if "pf1 for heavy gauge" in w or "should mention pf" in w:
            return "pf1_for_heavy_gauge"
        if "price" in w and ("specific" in w or "insert" in w):
            return "price_must_be_specific"
        if "hallucination" in w or "approximately" in w or "typically" in w:
            return "hallucination_vague"
        return warning[:80]
    
    def run_remediation_for_recurring(
        self,
        threshold: int = 3,
        send_telegram: bool = True,
        add_to_dream_backlog: bool = True,
    ) -> Dict:
        """
        For recurring validation issues (>= threshold), escalate from logging to action:
        1. Add fact corrections to correction_learner where applicable
        2. Send Telegram alert for human attention
        3. Add to dream mode backlog for overnight learning
        """
        recurring = self.analyze_recurring_issues(threshold)
        if not recurring:
            return {"remediated": 0, "recurring": []}
        
        results = {"remediated": 0, "recurring": recurring, "actions": []}
        
        # Add known fact corrections to correction_learner
        for r in recurring:
            if r["signature"] == "am_thickness_limit":
                try:
                    sys.path.insert(0, str(SKILL_DIR))
                    from correction_learner import get_learner, Correction
                    learner = get_learner()
                    canonical_id = "immune_am_thickness_1.5mm"
                    if canonical_id not in learner.corrections:
                        learner.corrections[canonical_id] = Correction(
                            id=canonical_id,
                            correction_type="fact",
                            original="AM series handles materials up to 2mm",
                            corrected="AM series handles materials up to 1.5mm ONLY. For >1.5mm use PF1.",
                            entity="AM Series",
                            context="material thickness",
                            timestamp=datetime.now().isoformat(),
                            confidence=1.0,
                        )
                        learner._save()
                        results["actions"].append("correction_learner:added_am_thickness")
                        results["remediated"] += 1
                except Exception as e:
                    logger.warning(f"Could not add AM correction to learner: {e}")
        
        # Add to dream mode backlog for learning
        if add_to_dream_backlog:
            try:
                dream_backlog = PROJECT_ROOT / "data" / "feedback_backlog.jsonl"
                dream_backlog.parent.mkdir(parents=True, exist_ok=True)
                for r in recurring:
                    entry = {
                        "timestamp": datetime.now().isoformat(),
                        "source": "immune_remediation",
                        "recurring_issue": r,
                        "message": f"Recurring knowledge health issue ({r['count']}x): {r['warning'][:100]}",
                    }
                    with open(dream_backlog, "a") as f:
                        f.write(json.dumps(entry) + "\n")
                    results["actions"].append(f"dream_backlog:added_{r['signature']}")
            except Exception as e:
                logger.warning(f"Could not add to dream backlog: {e}")
        
        # Send Telegram alert
        if send_telegram:
            self._send_remediation_alert(recurring)
            results["actions"].append("telegram:sent_remediation_alert")
        
        # Prune validation_issues to prevent unbounded growth; keep recent 50
        issues = self._state.get("validation_issues", [])
        if len(issues) > 50:
            self._state["validation_issues"] = issues[-50:]
            self._save_state()
        
        return results
    
    def _send_remediation_alert(self, recurring: List[Dict]):
        """Send Telegram alert when chronic issues need attention."""
        try:
            from config import TELEGRAM_BOT_TOKEN, EXPECTED_CHAT_ID
            import requests
            
            msg = "🛡️ *Immune System: Recurring Issues Need Attention*\n\n"
            msg += f"{len(recurring)} issue type(s) recurring 3+ times:\n\n"
            for r in recurring[:5]:
                msg += f"• {r['count']}x: {r['warning'][:60]}...\n"
            if len(recurring) > 5:
                msg += f"\n...and {len(recurring) - 5} more"
            
            requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                json={
                    "chat_id": EXPECTED_CHAT_ID,
                    "text": msg,
                    "parse_mode": "Markdown",
                },
                timeout=10,
            )
        except Exception as e:
            logger.warning(f"Failed to send remediation alert: {e}")
    
    def send_health_alert(self, report: HealthReport):
        """Send health alert via Telegram if critical issues found."""
        critical_issues = [i for i in report.issues if i.severity == "critical"]
        
        if not critical_issues:
            return
        
        try:
            # Import gateway to send alert
            from config import TELEGRAM_BOT_TOKEN, EXPECTED_CHAT_ID
            import requests
            
            message = f"⚠️ *Knowledge Health Alert*\n\n"
            message += f"Score: {report.overall_score:.0f}/100\n"
            message += f"Critical issues: {len(critical_issues)}\n\n"
            
            for issue in critical_issues[:5]:
                message += f"• {issue.message}\n"
            
            if len(critical_issues) > 5:
                message += f"\n...and {len(critical_issues) - 5} more"
            
            requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                json={
                    "chat_id": EXPECTED_CHAT_ID,
                    "text": message,
                    "parse_mode": "Markdown",
                },
                timeout=10,
            )
        
        except Exception as e:
            logger.error(f"Failed to send alert: {e}")


# =============================================================================
# SINGLETON & CONVENIENCE FUNCTIONS
# =============================================================================

_monitor_instance: Optional[KnowledgeHealthMonitor] = None


def get_health_monitor() -> KnowledgeHealthMonitor:
    """Get singleton health monitor instance."""
    global _monitor_instance
    if _monitor_instance is None:
        _monitor_instance = KnowledgeHealthMonitor()
    return _monitor_instance


def run_health_check() -> HealthReport:
    """Run health check and return report."""
    return get_health_monitor().run_health_check()


def validate_response(query: str, response: str, **kwargs) -> Tuple[bool, List[str]]:
    """Validate a response before sending."""
    return get_health_monitor().validate_response(query, response, **kwargs)


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Knowledge Health Monitor")
    parser.add_argument("--check", action="store_true", help="Run full health check")
    parser.add_argument("--fix", action="store_true", help="Auto-fix issues")
    parser.add_argument("--alert", action="store_true", help="Send Telegram alert")
    parser.add_argument("--remediate", action="store_true", help="Run immune remediation for recurring issues (3+ times)")
    parser.add_argument("--remediate-threshold", type=int, default=3, help="Min occurrences to trigger remediation")
    
    args = parser.parse_args()
    
    monitor = KnowledgeHealthMonitor()
    
    if args.remediate:
        print("\n🛡️ Immune System: Analyzing recurring issues...")
        recurring = monitor.analyze_recurring_issues(threshold=args.remediate_threshold)
        if recurring:
            print(f"Found {len(recurring)} recurring issue type(s):")
            for r in recurring:
                print(f"  • {r['count']}x: {r['signature']}")
            result = monitor.run_remediation_for_recurring(
                threshold=args.remediate_threshold,
                send_telegram=not os.environ.get("IRA_REMEDIATE_NO_ALERT"),
                add_to_dream_backlog=True,
            )
            print(f"Actions: {result.get('actions', [])}")
            print("✅ Remediation complete")
        else:
            print("No recurring issues (all < threshold)")
    else:
        report = monitor.run_health_check()
        
        print("\n" + "=" * 60)
        print("KNOWLEDGE HEALTH REPORT")
        print("=" * 60)
        print(f"Score: {report.overall_score:.0f}/100")
        print(f"Passed: {report.checks_passed} | Failed: {report.checks_failed}")
        print()
        
        if report.issues:
            print("Issues:")
            for issue in report.issues:
                icon = "❌" if issue.severity == "critical" else "⚠️" if issue.severity == "warning" else "ℹ️"
                print(f"  {icon} [{issue.category}] {issue.message}")
                
                if args.fix and issue.auto_fixable:
                    print(f"      → Attempting auto-fix...")
                    if monitor.auto_fix(issue):
                        print(f"      → Fixed!")
                    else:
                        print(f"      → Fix failed")
        else:
            print("✅ All checks passed!")
        
        if args.alert:
            monitor.send_health_alert(report)
            print("\n📤 Alert sent to Telegram")
