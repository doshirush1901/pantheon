"""
Tests for MemoryConsolidator
============================

Tests for the episodic memory consolidation system that learns 
generalized knowledge from conversational history.
"""

import json
import pytest
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List
from unittest.mock import MagicMock, patch, PropertyMock


class TestExtractedPattern:
    """Tests for ExtractedPattern dataclass."""
    
    def test_initialization(self):
        """Should initialize with required fields."""
        from openclaw.agents.ira.skills.memory.memory_consolidator import ExtractedPattern
        
        pattern = ExtractedPattern(
            pattern_type="topic",
            description="Users frequently ask about PF1",
            evidence_count=5,
            example_queries=["What is PF1?", "PF1 pricing"],
            confidence=0.8,
            entities_involved=["PF1"],
            first_seen=datetime.now(),
            last_seen=datetime.now(),
        )
        
        assert pattern.pattern_type == "topic"
        assert pattern.evidence_count == 5
        assert pattern.confidence == 0.8
        assert "PF1" in pattern.entities_involved


class TestConsolidatedKnowledge:
    """Tests for ConsolidatedKnowledge dataclass."""
    
    def test_initialization(self):
        """Should initialize with required fields."""
        from openclaw.agents.ira.skills.memory.memory_consolidator import ConsolidatedKnowledge
        
        knowledge = ConsolidatedKnowledge(
            knowledge_type="semantic_fact",
            content="Automotive dashboards are a common PF1 application",
            source_pattern="topic",
            confidence=0.85,
            metadata={"evidence_count": 5},
        )
        
        assert knowledge.knowledge_type == "semantic_fact"
        assert "Automotive" in knowledge.content
        assert knowledge.confidence == 0.85


class TestConsolidationResult:
    """Tests for ConsolidationResult dataclass."""
    
    def test_default_initialization(self):
        """Should initialize with default values."""
        from openclaw.agents.ira.skills.memory.memory_consolidator import ConsolidationResult
        
        result = ConsolidationResult()
        
        assert result.episodes_reviewed == 0
        assert result.patterns_identified == 0
        assert result.semantic_facts_created == 0
        assert result.procedures_created == 0
        assert result.relationships_created == 0
    
    def test_to_dict(self):
        """Should convert to dictionary."""
        from openclaw.agents.ira.skills.memory.memory_consolidator import ConsolidationResult
        
        result = ConsolidationResult(
            episodes_reviewed=100,
            patterns_identified=10,
            semantic_facts_created=5,
        )
        
        d = result.to_dict()
        
        assert d["episodes_reviewed"] == 100
        assert d["patterns_identified"] == 10
        assert d["semantic_facts_created"] == 5


class TestMemoryConsolidator:
    """Tests for MemoryConsolidator class."""
    
    @pytest.fixture
    def consolidator(self):
        """Create a MemoryConsolidator instance."""
        from openclaw.agents.ira.skills.memory.memory_consolidator import MemoryConsolidator
        return MemoryConsolidator(verbose=False)
    
    @pytest.fixture
    def sample_episodes(self):
        """Create sample episode data."""
        base_time = datetime.now()
        return [
            {
                "id": "ep_001",
                "identity_id": "user1",
                "timestamp": (base_time - timedelta(hours=1)).isoformat(),
                "summary": "User asked about PF1 thermoforming machine pricing",
                "topics": ["PF1", "pricing"],
                "outcome": "Quote provided",
                "channel": "telegram",
            },
            {
                "id": "ep_002",
                "identity_id": "user2",
                "timestamp": (base_time - timedelta(hours=2)).isoformat(),
                "summary": "User asked about PF1 specifications for automotive dashboard",
                "topics": ["PF1", "specifications", "automotive"],
                "outcome": "Specs provided",
                "channel": "email",
            },
            {
                "id": "ep_003",
                "identity_id": "user1",
                "timestamp": (base_time - timedelta(hours=3)).isoformat(),
                "summary": "User asked about PF1 delivery timeline",
                "topics": ["PF1", "delivery"],
                "outcome": "Timeline provided",
                "channel": "telegram",
            },
            {
                "id": "ep_004",
                "identity_id": "user3",
                "timestamp": (base_time - timedelta(hours=4)).isoformat(),
                "summary": "User asked about thermoforming for packaging",
                "topics": ["thermoforming", "packaging"],
                "outcome": "Info provided",
                "channel": "telegram",
            },
            {
                "id": "ep_005",
                "identity_id": "user4",
                "timestamp": (base_time - timedelta(hours=5)).isoformat(),
                "summary": "User asked about PF1 automotive applications",
                "topics": ["PF1", "automotive"],
                "outcome": "Applications listed",
                "channel": "email",
            },
        ]
    
    def test_initialization(self, consolidator):
        """Should initialize with default values."""
        assert consolidator.MIN_PATTERN_OCCURRENCES == 2
        assert consolidator.MIN_CONFIDENCE == 0.6
        assert consolidator.verbose is False
    
    def test_extract_patterns_heuristic_finds_topics(self, consolidator, sample_episodes):
        """Should find topic patterns using heuristics."""
        patterns = consolidator._extract_patterns_heuristic(sample_episodes)
        
        # Should find PF1 as a recurring topic
        topic_patterns = [p for p in patterns if p.pattern_type == "topic"]
        assert len(topic_patterns) > 0
        
        # Check that PF1 is detected
        pf1_patterns = [p for p in topic_patterns if "PF1" in p.description.upper()]
        assert len(pf1_patterns) > 0
    
    def test_extract_patterns_heuristic_respects_min_occurrences(self, consolidator):
        """Should only include patterns that meet minimum occurrence threshold."""
        from openclaw.agents.ira.skills.memory.memory_consolidator import ExtractedPattern
        
        # Create episodes where "rare_topic" only appears once
        episodes = [
            {"id": "1", "summary": "User asked about rare_topic", "topics": []},
            {"id": "2", "summary": "User asked about PF1", "topics": []},
            {"id": "3", "summary": "User asked about PF1", "topics": []},
        ]
        
        patterns = consolidator._extract_patterns_heuristic(episodes)
        
        # Should not include rare_topic (only 1 occurrence)
        rare_patterns = [p for p in patterns if "rare_topic" in p.description.lower()]
        assert len(rare_patterns) == 0
    
    def test_synthesize_knowledge_creates_facts(self, consolidator):
        """Should synthesize patterns into semantic facts."""
        from openclaw.agents.ira.skills.memory.memory_consolidator import ExtractedPattern
        
        patterns = [
            ExtractedPattern(
                pattern_type="topic",
                description="Users frequently ask about PF1",
                evidence_count=5,
                example_queries=["What is PF1?"],
                confidence=0.8,
                entities_involved=["PF1"],
                first_seen=datetime.now(),
                last_seen=datetime.now(),
            ),
        ]
        
        knowledge = consolidator._synthesize_knowledge(patterns)
        
        assert len(knowledge) > 0
        assert knowledge[0].knowledge_type == "semantic_fact"
    
    def test_synthesize_knowledge_filters_low_confidence(self, consolidator):
        """Should filter out low-confidence patterns."""
        from openclaw.agents.ira.skills.memory.memory_consolidator import ExtractedPattern
        
        patterns = [
            ExtractedPattern(
                pattern_type="topic",
                description="Low confidence pattern",
                evidence_count=2,
                example_queries=[],
                confidence=0.3,  # Below MIN_CONFIDENCE
                entities_involved=[],
                first_seen=datetime.now(),
                last_seen=datetime.now(),
            ),
        ]
        
        knowledge = consolidator._synthesize_knowledge(patterns)
        
        assert len(knowledge) == 0
    
    def test_synthesize_knowledge_creates_relationships(self, consolidator):
        """Should create relationships from entity_relationship patterns."""
        from openclaw.agents.ira.skills.memory.memory_consolidator import ExtractedPattern
        
        patterns = [
            ExtractedPattern(
                pattern_type="entity_relationship",
                description="PF1 used for Automotive Dashboards",
                evidence_count=5,
                example_queries=[],
                confidence=0.8,
                entities_involved=["PF1", "Automotive Dashboards"],
                first_seen=datetime.now(),
                last_seen=datetime.now(),
            ),
        ]
        
        knowledge = consolidator._synthesize_knowledge(patterns)
        
        relationships = [k for k in knowledge if k.knowledge_type == "relationship"]
        assert len(relationships) > 0
    
    def test_synthesize_knowledge_creates_procedures(self, consolidator):
        """Should create procedures from workflow patterns."""
        from openclaw.agents.ira.skills.memory.memory_consolidator import ExtractedPattern
        
        patterns = [
            ExtractedPattern(
                pattern_type="workflow",
                description="Workflow pattern: handle_quote - triggered by 'quote request'",
                evidence_count=5,
                example_queries=["Check inventory", "Get pricing", "Format quote"],
                confidence=0.75,
                entities_involved=[],
                first_seen=datetime.now(),
                last_seen=datetime.now(),
            ),
        ]
        
        knowledge = consolidator._synthesize_knowledge(patterns)
        
        procedures = [k for k in knowledge if k.knowledge_type == "procedural"]
        assert len(procedures) > 0
    
    def test_convert_llm_result_to_patterns(self, consolidator):
        """Should convert LLM output to ExtractedPattern objects."""
        llm_result = {
            "topic_patterns": [
                {"topic": "PF1", "frequency": 5, "examples": ["What is PF1?", "PF1 price"]}
            ],
            "intent_patterns": [
                {"intent": "get_quote", "frequency": 3, "typical_resolution": "Provide quote"}
            ],
            "workflow_patterns": [
                {"name": "quote_flow", "trigger": "quote", "steps": ["check", "price", "send"], "frequency": 4}
            ],
            "entity_relationships": [
                {"entity1": "PF1", "relation": "used_for", "entity2": "Automotive", "frequency": 3}
            ],
            "generalized_facts": [
                {"fact": "PF1 is popular for automotive", "confidence": 0.8, "evidence_count": 5}
            ],
        }
        
        patterns = consolidator._convert_llm_result_to_patterns(llm_result)
        
        # Should have patterns of each type
        types = {p.pattern_type for p in patterns}
        assert "topic" in types
        assert "intent" in types
        assert "workflow" in types
        assert "entity_relationship" in types
        assert "fact" in types
    
    def test_consolidate_with_too_few_episodes(self, consolidator):
        """Should return early if too few episodes."""
        consolidator._fetch_episodes = MagicMock(return_value=[
            {"id": "1", "summary": "Test"},
            {"id": "2", "summary": "Test"},
        ])
        
        result = consolidator.consolidate_episodic_memories(days_to_review=7)
        
        assert result.episodes_reviewed == 2
        assert result.patterns_identified == 0
    
    def test_consolidate_full_pipeline(self, consolidator, sample_episodes):
        """Should run full consolidation pipeline."""
        # Mock dependencies
        consolidator._fetch_episodes = MagicMock(return_value=sample_episodes)
        consolidator._extract_patterns_with_llm = MagicMock(return_value=[])
        consolidator._synthesize_knowledge = MagicMock(return_value=[])
        
        result = consolidator.consolidate_episodic_memories(days_to_review=7)
        
        assert result.episodes_reviewed == len(sample_episodes)
        consolidator._extract_patterns_with_llm.assert_called_once()
    
    def test_store_semantic_fact_calls_controller(self, consolidator):
        """Should store semantic facts via memory controller."""
        from openclaw.agents.ira.skills.memory.memory_consolidator import ConsolidatedKnowledge
        
        mock_controller = MagicMock()
        mock_controller.process.return_value = {"action": "create"}
        consolidator._get_memory_controller = MagicMock(return_value=mock_controller)
        
        knowledge = ConsolidatedKnowledge(
            knowledge_type="semantic_fact",
            content="Test fact",
            source_pattern="topic",
            confidence=0.8,
        )
        
        result = consolidator._store_semantic_fact(knowledge)
        
        assert result is True
        mock_controller.process.assert_called_once()
    
    def test_store_procedure_creates_workflow(self, consolidator):
        """Should store procedures via procedural store."""
        from openclaw.agents.ira.skills.memory.memory_consolidator import ConsolidatedKnowledge
        
        mock_proc_store = MagicMock()
        mock_proc_store.store_procedure.return_value = "proc_123"
        consolidator._get_procedural_store = MagicMock(return_value=mock_proc_store)
        
        knowledge = ConsolidatedKnowledge(
            knowledge_type="procedural",
            content="Workflow pattern: handle_quote - triggered by 'quote'",
            source_pattern="workflow",
            confidence=0.75,
            metadata={"steps": ["Check inventory", "Get pricing", "Send quote"]},
        )
        
        result = consolidator._store_procedure(knowledge)
        
        assert result is True
        mock_proc_store.store_procedure.assert_called_once()
    
    def test_store_relationship_adds_edge(self, consolidator):
        """Should store relationships via relationship store."""
        from openclaw.agents.ira.skills.memory.memory_consolidator import ConsolidatedKnowledge
        
        mock_rel_store = MagicMock()
        mock_rel_store.add_relationship.return_value = True
        consolidator._get_relationship_store = MagicMock(return_value=mock_rel_store)
        
        knowledge = ConsolidatedKnowledge(
            knowledge_type="relationship",
            content="PF1 used for Automotive",
            source_pattern="entity_relationship",
            confidence=0.8,
            metadata={"entities": ["PF1", "Automotive"]},
        )
        
        result = consolidator._store_relationship(knowledge)
        
        assert result is True
        mock_rel_store.add_relationship.assert_called_once()


class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""
    
    def test_get_memory_consolidator_singleton(self):
        """Should return singleton instance."""
        from openclaw.agents.ira.skills.memory.memory_consolidator import get_memory_consolidator
        
        c1 = get_memory_consolidator()
        c2 = get_memory_consolidator()
        
        assert c1 is c2
    
    def test_run_memory_consolidation(self):
        """Should run consolidation via convenience function."""
        from openclaw.agents.ira.skills.memory.memory_consolidator import run_memory_consolidation
        
        with patch("openclaw.agents.ira.skills.memory.memory_consolidator.MemoryConsolidator") as MockClass:
            mock_instance = MagicMock()
            mock_instance.consolidate_episodic_memories.return_value = MagicMock(
                episodes_reviewed=10,
                patterns_identified=3,
            )
            MockClass.return_value = mock_instance
            
            result = run_memory_consolidation(days=7, verbose=True)
            
            MockClass.assert_called_once_with(verbose=True)
            mock_instance.consolidate_episodic_memories.assert_called_once_with(days_to_review=7)


class TestDreamModeIntegration:
    """Tests for MemoryConsolidator integration with DreamMode."""
    
    def test_consolidate_episodic_to_semantic_method_exists(self):
        """Should have the consolidation method in DreamMode."""
        from openclaw.agents.ira.skills.brain.dream_mode import IntegratedDreamMode
        
        dream = IntegratedDreamMode()
        assert hasattr(dream, "_consolidate_episodic_to_semantic")
    
    def test_consolidate_episodic_to_semantic_returns_dict(self):
        """Should return dict with expected keys."""
        from openclaw.agents.ira.skills.brain.dream_mode import IntegratedDreamMode
        
        with patch("openclaw.agents.ira.skills.brain.dream_mode.MEMORY_CONSOLIDATOR_AVAILABLE", False):
            dream = IntegratedDreamMode()
            result = dream._consolidate_episodic_to_semantic(days=7)
        
        assert isinstance(result, dict)
        assert "episodes_reviewed" in result
        assert "patterns_found" in result
        assert "facts_created" in result
        assert "procedures_created" in result
        assert "relationships_created" in result
    
    def test_consolidate_episodic_to_semantic_uses_consolidator(self):
        """Should use MemoryConsolidator when available."""
        from openclaw.agents.ira.skills.brain.dream_mode import IntegratedDreamMode
        
        with patch("openclaw.agents.ira.skills.brain.dream_mode.MEMORY_CONSOLIDATOR_AVAILABLE", True):
            with patch("openclaw.agents.ira.skills.brain.dream_mode.MemoryConsolidator") as MockConsolidator:
                mock_result = MagicMock()
                mock_result.episodes_reviewed = 50
                mock_result.patterns_identified = 5
                mock_result.semantic_facts_created = 3
                mock_result.procedures_created = 1
                mock_result.relationships_created = 2
                mock_result.new_knowledge = []
                
                mock_instance = MagicMock()
                mock_instance.consolidate_episodic_memories.return_value = mock_result
                MockConsolidator.return_value = mock_instance
                
                dream = IntegratedDreamMode()
                result = dream._consolidate_episodic_to_semantic(days=7)
                
                assert result["episodes_reviewed"] == 50
                assert result["patterns_found"] == 5
                assert result["facts_created"] == 3


class TestPatternApprovalWorkflow:
    """Tests for pattern approval workflow."""
    
    @pytest.fixture
    def consolidator_with_approval(self, tmp_path):
        """Create consolidator with approval mode and temp files."""
        from openclaw.agents.ira.skills.memory.memory_consolidator import MemoryConsolidator
        
        with patch.object(MemoryConsolidator, 'PENDING_FILE', tmp_path / "pending.json"):
            with patch.object(MemoryConsolidator, 'USAGE_STATS_FILE', tmp_path / "usage.json"):
                consolidator = MemoryConsolidator(verbose=False, require_approval=True)
                yield consolidator
    
    def test_require_approval_mode(self, consolidator_with_approval):
        """Should enable approval mode."""
        assert consolidator_with_approval.require_approval is True
    
    def test_queue_for_approval(self, consolidator_with_approval):
        """Should queue patterns for approval."""
        from openclaw.agents.ira.skills.memory.memory_consolidator import ExtractedPattern, ConsolidatedKnowledge
        
        pattern = ExtractedPattern(
            pattern_type="topic",
            description="Test pattern",
            evidence_count=5,
            example_queries=["query1"],
            confidence=0.7,
            entities_involved=["PF1"],
            first_seen=datetime.now(),
            last_seen=datetime.now(),
        )
        
        knowledge = ConsolidatedKnowledge(
            knowledge_type="semantic_fact",
            content="Test fact",
            source_pattern="topic",
            confidence=0.7,
        )
        
        pattern_id = consolidator_with_approval._queue_for_approval(pattern, knowledge)
        
        assert pattern_id is not None
        pending = consolidator_with_approval.get_pending_patterns("pending")
        assert len(pending) == 1
        assert pending[0].proposed_knowledge == "Test fact"
    
    def test_approve_pattern(self, consolidator_with_approval):
        """Should approve a pending pattern."""
        from openclaw.agents.ira.skills.memory.memory_consolidator import ExtractedPattern, ConsolidatedKnowledge
        
        pattern = ExtractedPattern(
            pattern_type="topic",
            description="Test pattern",
            evidence_count=5,
            example_queries=["query1"],
            confidence=0.7,
            entities_involved=["PF1"],
            first_seen=datetime.now(),
            last_seen=datetime.now(),
        )
        
        knowledge = ConsolidatedKnowledge(
            knowledge_type="semantic_fact",
            content="Test fact for approval",
            source_pattern="topic",
            confidence=0.7,
        )
        
        pattern_id = consolidator_with_approval._queue_for_approval(pattern, knowledge)
        
        # Mock the storage
        consolidator_with_approval._store_semantic_fact = MagicMock(return_value=True)
        
        result = consolidator_with_approval.approve_pattern(pattern_id, "Looks good")
        
        assert result is True
        pending = consolidator_with_approval.get_pending_patterns("pending")
        assert len(pending) == 0
        
        approved = consolidator_with_approval.get_pending_patterns("approved")
        assert len(approved) == 1
    
    def test_reject_pattern(self, consolidator_with_approval):
        """Should reject a pending pattern."""
        from openclaw.agents.ira.skills.memory.memory_consolidator import ExtractedPattern, ConsolidatedKnowledge
        
        pattern = ExtractedPattern(
            pattern_type="topic",
            description="Bad pattern",
            evidence_count=2,
            example_queries=[],
            confidence=0.6,
            entities_involved=[],
            first_seen=datetime.now(),
            last_seen=datetime.now(),
        )
        
        knowledge = ConsolidatedKnowledge(
            knowledge_type="semantic_fact",
            content="Not accurate",
            source_pattern="topic",
            confidence=0.6,
        )
        
        pattern_id = consolidator_with_approval._queue_for_approval(pattern, knowledge)
        
        result = consolidator_with_approval.reject_pattern(pattern_id, "Not accurate")
        
        assert result is True
        rejected = consolidator_with_approval.get_pending_patterns("rejected")
        assert len(rejected) == 1
        assert rejected[0].review_notes == "Not accurate"


class TestQualityScoring:
    """Tests for quality scoring and usage tracking."""
    
    @pytest.fixture
    def consolidator_with_stats(self, tmp_path):
        """Create consolidator with temp stats file."""
        from openclaw.agents.ira.skills.memory.memory_consolidator import MemoryConsolidator
        
        with patch.object(MemoryConsolidator, 'USAGE_STATS_FILE', tmp_path / "usage.json"):
            with patch.object(MemoryConsolidator, 'PENDING_FILE', tmp_path / "pending.json"):
                consolidator = MemoryConsolidator(verbose=False)
                yield consolidator
    
    def test_track_knowledge_created(self, consolidator_with_stats):
        """Should track newly created knowledge."""
        from openclaw.agents.ira.skills.memory.memory_consolidator import ConsolidatedKnowledge
        
        knowledge = ConsolidatedKnowledge(
            knowledge_type="semantic_fact",
            content="Test knowledge",
            source_pattern="topic",
            confidence=0.8,
        )
        
        consolidator_with_stats._track_knowledge_created(knowledge, "test_123")
        
        assert "test_123" in consolidator_with_stats._usage_stats
        stats = consolidator_with_stats._usage_stats["test_123"]
        assert stats.times_retrieved == 0
        assert stats.usefulness_score == 0.5  # Neutral
    
    def test_record_knowledge_retrieval(self, consolidator_with_stats):
        """Should record retrieval events."""
        from openclaw.agents.ira.skills.memory.memory_consolidator import ConsolidatedKnowledge
        
        knowledge = ConsolidatedKnowledge(
            knowledge_type="semantic_fact",
            content="Test knowledge",
            source_pattern="topic",
            confidence=0.8,
        )
        
        consolidator_with_stats._track_knowledge_created(knowledge, "test_456")
        
        # Record some retrievals
        consolidator_with_stats.record_knowledge_retrieval("test_456", was_helpful=True)
        consolidator_with_stats.record_knowledge_retrieval("test_456", was_helpful=True)
        consolidator_with_stats.record_knowledge_retrieval("test_456", was_helpful=False)
        
        stats = consolidator_with_stats._usage_stats["test_456"]
        assert stats.times_retrieved == 3
        assert stats.times_helpful == 2
        assert stats.times_not_helpful == 1
        assert stats.usefulness_score == 2/3
    
    def test_quality_report(self, consolidator_with_stats):
        """Should generate quality report."""
        from openclaw.agents.ira.skills.memory.memory_consolidator import ConsolidatedKnowledge
        
        # Create some test knowledge
        for i in range(3):
            knowledge = ConsolidatedKnowledge(
                knowledge_type="semantic_fact",
                content=f"Knowledge {i}",
                source_pattern="topic",
                confidence=0.8,
            )
            consolidator_with_stats._track_knowledge_created(knowledge, f"k_{i}")
        
        # Add some feedback
        consolidator_with_stats.record_knowledge_retrieval("k_0", was_helpful=True)
        consolidator_with_stats.record_knowledge_retrieval("k_1", was_helpful=False)
        
        report = consolidator_with_stats.get_quality_report()
        
        assert report["total_knowledge"] == 3
        assert report["total_retrievals"] == 2
        assert report["total_helpful_feedback"] == 1
        assert report["total_not_helpful_feedback"] == 1


class TestExportCapabilities:
    """Tests for export functionality."""
    
    @pytest.fixture
    def consolidator_with_data(self, tmp_path):
        """Create consolidator with test data."""
        from openclaw.agents.ira.skills.memory.memory_consolidator import MemoryConsolidator, ConsolidatedKnowledge
        
        exports_dir = tmp_path / "exports"
        exports_dir.mkdir()
        
        with patch.object(MemoryConsolidator, 'EXPORTS_DIR', exports_dir):
            with patch.object(MemoryConsolidator, 'USAGE_STATS_FILE', tmp_path / "usage.json"):
                with patch.object(MemoryConsolidator, 'PENDING_FILE', tmp_path / "pending.json"):
                    with patch.object(MemoryConsolidator, 'AUDIT_FILE', tmp_path / "audit.json"):
                        consolidator = MemoryConsolidator(verbose=False)
                        
                        # Add some test data
                        for i in range(3):
                            knowledge = ConsolidatedKnowledge(
                                knowledge_type="semantic_fact",
                                content=f"Test fact {i}",
                                source_pattern="topic",
                                confidence=0.8,
                            )
                            consolidator._track_knowledge_created(knowledge, f"fact_{i}")
                        
                        yield consolidator
    
    def test_export_to_csv(self, consolidator_with_data):
        """Should export to CSV file."""
        filepath = consolidator_with_data.export_to_csv()
        
        assert filepath.exists()
        assert filepath.suffix == ".csv"
        
        content = filepath.read_text()
        assert "fact_0" in content or "Test fact" in content
    
    def test_export_to_csv_custom_filename(self, consolidator_with_data):
        """Should use custom filename."""
        filepath = consolidator_with_data.export_to_csv("custom_export.csv")
        
        assert filepath.name == "custom_export.csv"


class TestPendingPattern:
    """Tests for PendingPattern dataclass."""
    
    def test_to_dict(self):
        """Should convert to dictionary."""
        from openclaw.agents.ira.skills.memory.memory_consolidator import PendingPattern
        
        pending = PendingPattern(
            id="test_123",
            pattern_type="topic",
            description="Test description",
            proposed_knowledge="Test knowledge",
            knowledge_type="semantic_fact",
            confidence=0.8,
            evidence_count=5,
            example_queries=["q1", "q2"],
            entities_involved=["PF1"],
            created_at="2024-01-01T00:00:00",
        )
        
        d = pending.to_dict()
        
        assert d["id"] == "test_123"
        assert d["confidence"] == 0.8
        assert d["status"] == "pending"
    
    def test_from_dict(self):
        """Should create from dictionary."""
        from openclaw.agents.ira.skills.memory.memory_consolidator import PendingPattern
        
        d = {
            "id": "test_456",
            "pattern_type": "workflow",
            "description": "Workflow pattern",
            "proposed_knowledge": "When X happens, do Y",
            "knowledge_type": "procedural",
            "confidence": 0.75,
            "evidence_count": 3,
            "example_queries": [],
            "entities_involved": [],
            "created_at": "2024-01-01",
            "status": "approved",
        }
        
        pending = PendingPattern.from_dict(d)
        
        assert pending.id == "test_456"
        assert pending.status == "approved"


class TestKnowledgeUsageStats:
    """Tests for KnowledgeUsageStats dataclass."""
    
    def test_usefulness_score_no_feedback(self):
        """Should return neutral score with no feedback."""
        from openclaw.agents.ira.skills.memory.memory_consolidator import KnowledgeUsageStats
        
        stats = KnowledgeUsageStats(
            knowledge_id="test",
            content="Test",
            knowledge_type="fact",
            created_at="2024-01-01",
        )
        
        assert stats.usefulness_score == 0.5
    
    def test_usefulness_score_with_feedback(self):
        """Should calculate score from feedback."""
        from openclaw.agents.ira.skills.memory.memory_consolidator import KnowledgeUsageStats
        
        stats = KnowledgeUsageStats(
            knowledge_id="test",
            content="Test",
            knowledge_type="fact",
            created_at="2024-01-01",
            times_helpful=8,
            times_not_helpful=2,
        )
        
        assert stats.usefulness_score == 0.8


class TestQualityTrackingIntegration:
    """Tests for quality tracking integration with retriever and generate_answer."""
    
    def test_citation_has_quality_tracking_fields(self):
        """Citation should have consolidated knowledge fields."""
        try:
            from openclaw.agents.ira.skills.brain.qdrant_retriever import Citation
            
            citation = Citation(
                text="Test text",
                filename="test.pdf",
                is_consolidated_knowledge=True,
                knowledge_id="test_knowledge_123",
            )
            
            assert citation.is_consolidated_knowledge is True
            assert citation.knowledge_id == "test_knowledge_123"
        except ImportError:
            pytest.skip("qdrant_retriever not available")
    
    def test_response_object_has_knowledge_ids(self):
        """ResponseObject should have consolidated_knowledge_ids field."""
        try:
            from openclaw.agents.ira.skills.brain.generate_answer import (
                ResponseObject, ResponseMode, ConfidenceLevel
            )
            
            response = ResponseObject(
                text="Test response",
                mode=ResponseMode.GENERAL,
                confidence=ConfidenceLevel.HIGH,
                consolidated_knowledge_ids=["id1", "id2"],
            )
            
            assert response.consolidated_knowledge_ids == ["id1", "id2"]
            
            d = response.to_dict()
            assert "consolidated_knowledge_ids" in d
            assert d["consolidated_knowledge_ids"] == ["id1", "id2"]
        except ImportError:
            pytest.skip("generate_answer not available")
    
    def test_response_object_record_feedback_method(self):
        """ResponseObject should have record_feedback method."""
        try:
            from openclaw.agents.ira.skills.brain.generate_answer import (
                ResponseObject, ResponseMode, ConfidenceLevel
            )
            
            response = ResponseObject(
                text="Test response",
                mode=ResponseMode.GENERAL,
                confidence=ConfidenceLevel.HIGH,
                consolidated_knowledge_ids=[],
            )
            
            assert hasattr(response, 'record_feedback')
            assert callable(response.record_feedback)
            
            count = response.record_feedback(was_helpful=True)
            assert count == 0
        except ImportError:
            pytest.skip("generate_answer not available")
    
    def test_get_consolidated_knowledge_ids(self):
        """Should extract knowledge IDs from citations."""
        try:
            from openclaw.agents.ira.skills.brain.qdrant_retriever import (
                Citation, get_consolidated_knowledge_ids
            )
            
            citations = [
                Citation(text="t1", filename="f1", is_consolidated_knowledge=True, knowledge_id="k1"),
                Citation(text="t2", filename="f2", is_consolidated_knowledge=False, knowledge_id="k2"),
                Citation(text="t3", filename="f3", is_consolidated_knowledge=True, knowledge_id="k3"),
            ]
            
            ids = get_consolidated_knowledge_ids(citations)
            
            assert ids == ["k1", "k3"]
        except ImportError:
            pytest.skip("qdrant_retriever not available")
    
    def test_record_feedback_functions_exist(self):
        """Quality tracking functions should exist."""
        try:
            from openclaw.agents.ira.skills.brain.qdrant_retriever import (
                record_knowledge_feedback,
                record_feedback_for_citations,
                get_consolidated_knowledge_ids,
            )
            
            assert callable(record_knowledge_feedback)
            assert callable(record_feedback_for_citations)
            assert callable(get_consolidated_knowledge_ids)
        except ImportError:
            pytest.skip("qdrant_retriever not available")
    
    def test_generate_answer_exports_feedback_functions(self):
        """generate_answer module should export feedback functions."""
        try:
            from openclaw.agents.ira.skills.brain.generate_answer import (
                record_response_feedback,
                record_feedback_by_ids,
            )
            
            assert callable(record_response_feedback)
            assert callable(record_feedback_by_ids)
        except ImportError:
            pytest.skip("generate_answer not available")
