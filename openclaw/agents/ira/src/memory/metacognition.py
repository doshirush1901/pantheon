#!/usr/bin/env python3
"""
META-COGNITION - Knowing What You Know (and Don't Know)

╔════════════════════════════════════════════════════════════════════╗
║  Current Ira: Answers everything confidently (even when wrong)     ║
║  With Meta-cognition: "I'm not sure about this" / "Let me verify"  ║
╚════════════════════════════════════════════════════════════════════╝

Meta-cognition enables:
- Calibrated uncertainty ("I'm 90% sure" vs "I think, but not certain")
- Knowledge gap detection ("I don't have information about X")
- Source awareness ("User told me" vs "I inferred")
- Conflict detection ("I have contradictory information")

Based on neuroscience:
- Prefrontal cortex monitors confidence
- "Tip of tongue" feeling = partial retrieval
- Feeling of knowing (FOK) predicts retrieval success
"""

import json
import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

# Import from centralized config
try:
    from config import DATABASE_URL
except ImportError:
    import os
    DATABASE_URL = os.environ.get("DATABASE_URL", "")


# =============================================================================
# KNOWLEDGE STATES
# =============================================================================

class KnowledgeState(Enum):
    """
    States of knowledge about a query.
    
    Based on cognitive psychology's "feeling of knowing" research.
    """
    KNOW_VERIFIED = "know_verified"      # Have verified, high-confidence info
    KNOW_UNVERIFIED = "know_unverified"  # Have info, but not verified
    PARTIAL = "partial"                   # Have related info, not exact answer
    UNCERTAIN = "uncertain"               # Have some info, low confidence
    CONFLICTING = "conflicting"          # Have contradictory information
    UNKNOWN = "unknown"                   # No relevant information
    OUT_OF_SCOPE = "out_of_scope"        # Outside knowledge domain


class SourceType(Enum):
    """
    Where knowledge came from.
    
    Source monitoring is crucial for reliability assessment.
    """
    USER_STATED = "user_stated"          # User explicitly said this
    DOCUMENT = "document"                 # Read from knowledge base
    INFERRED = "inferred"                 # Deduced from context
    CORRECTED = "corrected"              # User corrected a previous belief
    SYSTEM = "system"                     # System/default knowledge
    EXTERNAL = "external"                 # External API/source


@dataclass
class KnowledgeAssessment:
    """
    Assessment of knowledge state for a query.
    """
    state: KnowledgeState
    confidence: float                      # 0-1 scale
    sources: List[SourceType] = field(default_factory=list)
    evidence: List[str] = field(default_factory=list)  # Supporting facts
    conflicts: List[str] = field(default_factory=list)  # Conflicting facts
    gaps: List[str] = field(default_factory=list)       # What we don't know
    suggested_action: str = ""             # What to do about this
    
    def to_dict(self) -> Dict:
        return {
            "state": self.state.value,
            "confidence": self.confidence,
            "sources": [s.value for s in self.sources],
            "evidence": self.evidence,
            "conflicts": self.conflicts,
            "gaps": self.gaps,
            "suggested_action": self.suggested_action,
        }
    
    def get_response_prefix(self) -> str:
        """
        Get appropriate response prefix based on knowledge state.
        
        This makes Ira's uncertainty explicit in responses.
        """
        if self.state == KnowledgeState.KNOW_VERIFIED:
            if self.confidence > 0.9:
                return ""  # No prefix needed, confident
            return "Based on my records, "
        
        elif self.state == KnowledgeState.KNOW_UNVERIFIED:
            return "I believe, though I haven't verified recently, "
        
        elif self.state == KnowledgeState.PARTIAL:
            return "I have some related information: "
        
        elif self.state == KnowledgeState.UNCERTAIN:
            return "I'm not entirely sure, but "
        
        elif self.state == KnowledgeState.CONFLICTING:
            return "I have some conflicting information on this. "
        
        elif self.state == KnowledgeState.UNKNOWN:
            return "I don't have specific information about this. "
        
        elif self.state == KnowledgeState.OUT_OF_SCOPE:
            return "This is outside my usual knowledge area, but "
        
        return ""
    
    def should_hedge(self) -> bool:
        """Should we hedge our response?"""
        return self.state in [
            KnowledgeState.UNCERTAIN,
            KnowledgeState.PARTIAL,
            KnowledgeState.CONFLICTING,
            KnowledgeState.KNOW_UNVERIFIED
        ] or self.confidence < 0.7
    
    def should_ask_clarification(self) -> bool:
        """Should we ask for clarification?"""
        return self.state == KnowledgeState.PARTIAL or len(self.gaps) > 0
    
    def should_verify(self) -> bool:
        """Should we verify with user before acting?"""
        return self.state == KnowledgeState.CONFLICTING or self.confidence < 0.5


# =============================================================================
# META-COGNITION ENGINE
# =============================================================================

class MetaCognition:
    """
    Assesses knowledge state and confidence for queries.
    
    Key methods:
    - assess(): Evaluate knowledge state for a query
    - detect_gaps(): Find what we don't know
    - resolve_conflicts(): Handle contradictory information
    """
    
    # Domain keywords for scope detection
    DOMAIN_KEYWORDS = {
        "business": ["price", "quote", "order", "customer", "product", "machine", "spec"],
        "technical": ["feature", "specification", "how does", "what is", "compare"],
        "support": ["problem", "issue", "not working", "help", "error"],
        "personal": ["remember", "know about me", "my", "i told you"],
    }
    
    # Out of scope patterns
    OUT_OF_SCOPE_PATTERNS = [
        r"weather",
        r"sports score",
        r"stock (price|market)",
        r"what time is it",
        r"tell me a joke",
        r"who (won|is winning)",
    ]
    
    def __init__(self):
        self._scope_patterns = [re.compile(p, re.IGNORECASE) for p in self.OUT_OF_SCOPE_PATTERNS]
    
    def assess(
        self,
        query: str,
        user_memories: List[Any] = None,
        entity_memories: List[Any] = None,
        rag_chunks: List[Dict] = None,
        context: Dict = None
    ) -> KnowledgeAssessment:
        """
        Assess knowledge state for a query.
        
        Args:
            query: The user's question/request
            user_memories: Retrieved user memories
            entity_memories: Retrieved entity memories
            rag_chunks: Retrieved document chunks
            context: Additional context
        
        Returns:
            KnowledgeAssessment with state, confidence, and guidance
        """
        user_memories = user_memories or []
        entity_memories = entity_memories or []
        rag_chunks = rag_chunks or []
        
        # Check if out of scope
        if self._is_out_of_scope(query):
            return KnowledgeAssessment(
                state=KnowledgeState.OUT_OF_SCOPE,
                confidence=0.0,
                suggested_action="Acknowledge limitation and redirect"
            )
        
        # Gather evidence
        evidence = []
        sources = []
        
        # From user memories
        for mem in user_memories:
            text = mem.memory_text if hasattr(mem, 'memory_text') else mem.get('memory_text', '')
            if text:
                evidence.append(text)
                source = mem.source_channel if hasattr(mem, 'source_channel') else 'user'
                if source in ['telegram', 'email']:
                    sources.append(SourceType.USER_STATED)
                else:
                    sources.append(SourceType.INFERRED)
        
        # From entity memories
        for mem in entity_memories:
            text = mem.memory_text if hasattr(mem, 'memory_text') else mem.get('memory_text', '')
            if text:
                evidence.append(text)
                sources.append(SourceType.DOCUMENT)
        
        # From RAG chunks
        for chunk in rag_chunks:
            text = chunk.get('text', '')
            if text:
                evidence.append(text[:200])
                sources.append(SourceType.DOCUMENT)
        
        # Detect conflicts
        conflicts = self._detect_conflicts(evidence)
        
        # Detect gaps
        gaps = self._detect_gaps(query, evidence)
        
        # Determine state and confidence
        state, confidence = self._determine_state(
            query=query,
            evidence=evidence,
            conflicts=conflicts,
            gaps=gaps,
            sources=sources
        )
        
        # Generate suggested action
        suggested_action = self._suggest_action(state, confidence, gaps)
        
        return KnowledgeAssessment(
            state=state,
            confidence=confidence,
            sources=list(set(sources)),
            evidence=evidence[:5],  # Top 5 pieces of evidence
            conflicts=conflicts,
            gaps=gaps,
            suggested_action=suggested_action,
        )
    
    def _is_out_of_scope(self, query: str) -> bool:
        """Check if query is outside our domain."""
        for pattern in self._scope_patterns:
            if pattern.search(query):
                return True
        return False
    
    def _detect_conflicts(self, evidence: List[str]) -> List[str]:
        """Detect conflicting information in evidence."""
        conflicts = []
        
        # Simple heuristic: look for contradictions
        for i, e1 in enumerate(evidence):
            for e2 in evidence[i+1:]:
                # Check for negation patterns
                if self._are_conflicting(e1, e2):
                    conflicts.append(f"'{e1[:50]}...' vs '{e2[:50]}...'")
        
        return conflicts[:3]  # Return top 3 conflicts
    
    def _are_conflicting(self, text1: str, text2: str) -> bool:
        """Check if two pieces of evidence conflict."""
        t1 = text1.lower()
        t2 = text2.lower()
        
        # Check for explicit negation
        negation_pairs = [
            ("is", "is not"),
            ("does", "does not"),
            ("can", "cannot"),
            ("will", "will not"),
            ("prefers", "does not prefer"),
        ]
        
        for pos, neg in negation_pairs:
            if pos in t1 and neg in t2:
                # Check if about same subject
                words1 = set(t1.split())
                words2 = set(t2.split())
                if len(words1 & words2) > 3:  # Significant overlap
                    return True
        
        # Check for contradictory numbers
        nums1 = re.findall(r'\$?[\d,]+(?:\.\d+)?', t1)
        nums2 = re.findall(r'\$?[\d,]+(?:\.\d+)?', t2)
        
        if nums1 and nums2:
            # If talking about same thing with different numbers
            words1 = set(t1.split()) - set(nums1)
            words2 = set(t2.split()) - set(nums2)
            if len(words1 & words2) > 3:  # Same context, different numbers
                if nums1[0] != nums2[0]:
                    return True
        
        return False
    
    def _detect_gaps(self, query: str, evidence: List[str]) -> List[str]:
        """Detect what information is missing to answer the query."""
        gaps = []
        query_lower = query.lower()
        
        # Check for specific information requests
        info_patterns = [
            (r"price|cost|how much", "pricing information"),
            (r"when|date|time", "timing/date information"),
            (r"where|location", "location information"),
            (r"who|contact|person", "contact information"),
            (r"why|reason", "reasoning/justification"),
            (r"how (to|do|can)", "procedural steps"),
            (r"spec|feature|capability", "technical specifications"),
        ]
        
        for pattern, info_type in info_patterns:
            if re.search(pattern, query_lower):
                # Check if evidence contains this type of info
                has_info = False
                for e in evidence:
                    if re.search(pattern, e.lower()):
                        has_info = True
                        break
                if not has_info:
                    gaps.append(f"Missing {info_type}")
        
        return gaps[:3]  # Return top 3 gaps
    
    def _determine_state(
        self,
        query: str,
        evidence: List[str],
        conflicts: List[str],
        gaps: List[str],
        sources: List[SourceType]
    ) -> Tuple[KnowledgeState, float]:
        """Determine knowledge state and confidence."""
        
        # No evidence at all
        if not evidence:
            return KnowledgeState.UNKNOWN, 0.0
        
        # Have conflicts
        if conflicts:
            return KnowledgeState.CONFLICTING, 0.4
        
        # Calculate base confidence from evidence count and source quality
        evidence_score = min(len(evidence) / 5, 1.0)  # More evidence = higher confidence
        
        # Source quality scoring
        source_scores = {
            SourceType.USER_STATED: 0.9,      # User told us directly
            SourceType.CORRECTED: 0.95,        # User corrected us (very reliable)
            SourceType.DOCUMENT: 0.8,          # From verified documents
            SourceType.INFERRED: 0.5,          # We inferred this
            SourceType.SYSTEM: 0.7,            # System default
            SourceType.EXTERNAL: 0.6,          # External source
        }
        
        if sources:
            source_quality = sum(source_scores.get(s, 0.5) for s in sources) / len(sources)
        else:
            source_quality = 0.5
        
        # Combine scores
        confidence = (evidence_score * 0.4 + source_quality * 0.6)
        
        # Adjust for gaps
        if gaps:
            confidence *= (1 - 0.15 * len(gaps))  # Each gap reduces confidence
        
        # Determine state
        if confidence > 0.8 and SourceType.USER_STATED in sources:
            return KnowledgeState.KNOW_VERIFIED, confidence
        elif confidence > 0.7:
            return KnowledgeState.KNOW_UNVERIFIED, confidence
        elif confidence > 0.4:
            return KnowledgeState.PARTIAL, confidence
        else:
            return KnowledgeState.UNCERTAIN, confidence
    
    def _suggest_action(
        self,
        state: KnowledgeState,
        confidence: float,
        gaps: List[str]
    ) -> str:
        """Suggest what action to take based on knowledge state."""
        
        if state == KnowledgeState.KNOW_VERIFIED:
            return "Respond confidently"
        
        elif state == KnowledgeState.KNOW_UNVERIFIED:
            return "Respond with soft hedge, offer to verify"
        
        elif state == KnowledgeState.PARTIAL:
            if gaps:
                return f"Ask about: {', '.join(gaps)}"
            return "Provide what we know, ask for clarification"
        
        elif state == KnowledgeState.UNCERTAIN:
            return "Acknowledge uncertainty, ask clarifying questions"
        
        elif state == KnowledgeState.CONFLICTING:
            return "Ask user to clarify which information is correct"
        
        elif state == KnowledgeState.UNKNOWN:
            return "Acknowledge lack of information, offer to help find out"
        
        elif state == KnowledgeState.OUT_OF_SCOPE:
            return "Politely redirect to core capabilities"
        
        return "Proceed with caution"
    
    # =========================================================================
    # PROMPT INTEGRATION
    # =========================================================================
    
    def get_metacognitive_guidance(self, assessment: KnowledgeAssessment) -> str:
        """
        Generate guidance for LLM based on knowledge assessment.
        
        This goes into the system prompt to calibrate response confidence.
        """
        lines = ["KNOWLEDGE ASSESSMENT:"]
        lines.append(f"State: {assessment.state.value}")
        lines.append(f"Confidence: {assessment.confidence:.0%}")
        
        if assessment.evidence:
            lines.append(f"Evidence items: {len(assessment.evidence)}")
        
        if assessment.conflicts:
            lines.append(f"⚠️ CONFLICTS DETECTED: {len(assessment.conflicts)}")
            for c in assessment.conflicts[:2]:
                lines.append(f"  - {c}")
        
        if assessment.gaps:
            lines.append(f"📭 INFORMATION GAPS:")
            for g in assessment.gaps:
                lines.append(f"  - {g}")
        
        lines.append(f"\nGUIDANCE: {assessment.suggested_action}")
        
        # Response calibration
        if assessment.should_hedge():
            lines.append("\n⚡ CALIBRATION: Use hedging language (\"I believe\", \"Based on my understanding\")")
        
        if assessment.should_ask_clarification():
            lines.append("⚡ CALIBRATION: Ask clarifying questions before giving definitive answer")
        
        if assessment.should_verify():
            lines.append("⚡ CALIBRATION: Verify with user before taking action")
        
        return "\n".join(lines)


# Singleton
_metacognition: Optional[MetaCognition] = None


def get_metacognition() -> MetaCognition:
    global _metacognition
    if _metacognition is None:
        _metacognition = MetaCognition()
    return _metacognition


def assess_knowledge(
    query: str,
    user_memories: List[Any] = None,
    entity_memories: List[Any] = None,
    rag_chunks: List[Dict] = None
) -> KnowledgeAssessment:
    """
    Quick helper to assess knowledge state.
    
    Usage:
        assessment = assess_knowledge(query, memories, chunks)
        if assessment.should_hedge():
            response = assessment.get_response_prefix() + response
    """
    return get_metacognition().assess(query, user_memories, entity_memories, rag_chunks)


# =============================================================================
# CLI for OpenClaw skill
# =============================================================================

if __name__ == "__main__":
    import argparse
    import json
    
    parser = argparse.ArgumentParser(description="Meta-cognition Assessment Skill")
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    assess_parser = subparsers.add_parser("assess", help="Assess confidence for a text")
    assess_parser.add_argument("--text", required=True, help="Text to assess confidence for")
    assess_parser.add_argument("--json", action="store_true", help="Output as JSON")
    
    args = parser.parse_args()
    
    mc = get_metacognition()
    
    if args.command == "assess":
        assessment = mc.assess(query=args.text, user_memories=[], rag_chunks=[])
        
        if args.json:
            print(json.dumps({
                "state": assessment.state.value,
                "confidence": assessment.confidence,
                "should_hedge": assessment.should_hedge(),
                "should_verify": assessment.should_verify(),
                "suggested_action": assessment.suggested_action,
                "response_prefix": assessment.get_response_prefix(),
            }, indent=2))
        else:
            print(f"State: {assessment.state.value}")
            print(f"Confidence: {assessment.confidence:.0%}")
            print(f"Suggested: {assessment.suggested_action}")
            if assessment.should_hedge():
                print(f"Prefix: {assessment.get_response_prefix()}")
