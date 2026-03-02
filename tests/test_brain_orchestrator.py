"""
Tests for Brain State Classes
=============================

Tests for the core brain state management classes extracted to src/core/brain_state.py.
"""

import pytest
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch, PropertyMock

from src.core.brain_state import ProcessingPhase, BrainState, AttentionManager, FeedbackLearner


class TestProcessingPhase:
    """Tests for ProcessingPhase enum."""
    
    def test_phase_values(self):
        """Should have all expected phases."""
        phases = [p.value for p in ProcessingPhase]
        
        assert "init" in phases
        assert "trigger_evaluation" in phases
        assert "memory_retrieval" in phases
        assert "episodic_retrieval" in phases
        assert "procedural_matching" in phases
        assert "memory_weaving" in phases
        assert "memory_reasoning" in phases
        assert "metacognition" in phases
        assert "attention_filtering" in phases
        assert "complete" in phases
        assert "failed" in phases


class TestBrainState:
    """Tests for BrainState dataclass."""
    
    def test_default_initialization(self):
        """Should initialize with default values."""
        state = BrainState()
        
        assert state.message == ""
        assert state.identity_id is None
        assert state.channel == "telegram"
        assert state.phase == ProcessingPhase.INIT
        assert state.should_retrieve is True
        assert state.user_memories == []
        assert state.entity_memories == []
        assert state.errors == []
    
    def test_initialization_with_values(self):
        """Should initialize with provided values."""
        state = BrainState(
            message="Test message",
            identity_id="user_123",
            channel="email",
        )
        
        assert state.message == "Test message"
        assert state.identity_id == "user_123"
        assert state.channel == "email"
    
    def test_email_specific_fields(self):
        """Should support email-specific context."""
        state = BrainState(
            channel="email",
            thread_id="thread_abc",
            subject="Inquiry about PF1-C",
            is_reply=True,
            from_email="customer@example.com",
            from_name="John Doe",
            is_internal=False,
        )
        
        assert state.thread_id == "thread_abc"
        assert state.subject == "Inquiry about PF1-C"
        assert state.is_reply is True
        assert state.from_email == "customer@example.com"
    
    def test_add_error(self):
        """Should record errors with phase context."""
        state = BrainState()
        state.add_error("retrieval", "Database connection failed")
        
        assert len(state.errors) == 1
        assert "[retrieval]" in state.errors[0]
        assert "Database connection failed" in state.errors[0]
    
    def test_record_timing(self):
        """Should record processing times."""
        state = BrainState()
        state.record_timing("retrieval", 150.5)
        state.record_timing("reasoning", 85.2)
        
        assert state.timings["retrieval"] == 150.5
        assert state.timings["reasoning"] == 85.2
    
    def test_to_context_pack(self):
        """Should convert to context pack format."""
        state = BrainState(
            message="Test",
            user_memories=["memory1"],
            procedure_guidance="Follow step 1",
            reasoning_context="Thinking about...",
        )
        
        pack = state.to_context_pack()
        
        assert pack["user_memories"] == ["memory1"]
        assert pack["procedure_guidance"] == "Follow step 1"
        assert pack["reasoning_context"] == "Thinking about..."
    
    def test_competitor_fields(self):
        """Should support competitor intelligence fields."""
        state = BrainState(
            is_competitor_comparison=True,
            competitors_mentioned=["ILLIG", "Kiefel"],
            competitor_context="Customer comparing with German machines",
        )
        
        assert state.is_competitor_comparison is True
        assert "ILLIG" in state.competitors_mentioned
        assert "German machines" in state.competitor_context
    
    def test_goal_fields(self):
        """Should support goal-directed reasoning fields."""
        state = BrainState(
            active_goal_id="goal_123",
            goal_status={"progress": 50},
            goal_proactive_prompt="Consider next steps",
        )
        
        assert state.active_goal_id == "goal_123"
        assert state.goal_status["progress"] == 50
        assert "next steps" in state.goal_proactive_prompt


class TestAttentionManager:
    """Tests for AttentionManager working memory limits."""
    
    def test_default_capacity(self):
        """Should use default capacity of 7."""
        manager = AttentionManager()
        assert manager.max_items == 7
    
    def test_custom_capacity(self):
        """Should accept custom capacity."""
        manager = AttentionManager(max_items=5)
        assert manager.max_items == 5
    
    def test_prioritize_empty_items(self):
        """Should handle empty items."""
        manager = AttentionManager()
        filtered, num_filtered = manager.prioritize({})
        
        assert filtered == {}
        assert num_filtered == 0
    
    def test_prioritize_within_capacity(self):
        """Should keep all items within capacity."""
        manager = AttentionManager(max_items=5)
        items = {
            "procedure_guidance": "Step 1",
            "reasoning_context": "Thinking",
            "user_memories": ["mem1"],
        }
        
        filtered, num_filtered = manager.prioritize(items)
        
        assert len(filtered) == 3
        assert num_filtered == 0
    
    def test_prioritize_over_capacity(self):
        """Should filter items over capacity by priority."""
        manager = AttentionManager(max_items=3)
        items = {
            "procedure_guidance": "High priority",
            "conflicts": ["conflict1"],
            "metacognitive_guidance": "Medium-high",
            "reasoning_context": "Medium",
            "user_memories": ["mem1"],
            "rag_chunks": ["chunk1"],
        }
        
        filtered, num_filtered = manager.prioritize(items)
        
        assert len(filtered) == 3
        assert num_filtered == 3
        assert "procedure_guidance" in filtered
        assert "conflicts" in filtered
    
    def test_prioritize_skips_empty_values(self):
        """Should skip empty values."""
        manager = AttentionManager()
        items = {
            "procedure_guidance": "Has content",
            "reasoning_context": "",
            "user_memories": [],
            "conflicts": None,
        }
        
        filtered, num_filtered = manager.prioritize(items)
        
        assert len(filtered) == 1
        assert "procedure_guidance" in filtered


class TestFeedbackLearner:
    """Tests for FeedbackLearner calibration."""
    
    def test_initialization(self):
        """Should initialize with empty calibration."""
        with patch.object(FeedbackLearner, '_load_calibration'):
            learner = FeedbackLearner()
            assert learner._calibration_data == {}
    
    def test_get_calibration_adjustment_unknown_type(self):
        """Should return 0 for unknown query types."""
        with patch.object(FeedbackLearner, '_load_calibration'):
            learner = FeedbackLearner()
            adjustment = learner.get_calibration_adjustment("unknown_type")
            assert adjustment == 0.0
    
    def test_get_calibration_adjustment_insufficient_data(self):
        """Should return 0 with insufficient data."""
        with patch.object(FeedbackLearner, '_load_calibration'):
            learner = FeedbackLearner()
            learner._calibration_data = {
                "pricing": {
                    "predictions": [0.8, 0.7],
                    "outcomes": [True, False]
                }
            }
            
            adjustment = learner.get_calibration_adjustment("pricing")
            assert adjustment == 0.0
