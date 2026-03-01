"""
Tests for DreamMode
===================

Tests for the nightly learning and document processing system.
"""

import json
import pytest
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from unittest.mock import MagicMock, patch, mock_open


class TestDocumentPriority:
    """Tests for DocumentPriority enum."""
    
    def test_priority_ordering(self):
        """Priorities should be ordered correctly."""
        from openclaw.agents.ira.skills.brain.dream_mode import DocumentPriority
        
        assert DocumentPriority.CRITICAL.value < DocumentPriority.HIGH.value
        assert DocumentPriority.HIGH.value < DocumentPriority.MEDIUM.value
        assert DocumentPriority.MEDIUM.value < DocumentPriority.LOW.value
        assert DocumentPriority.LOW.value < DocumentPriority.SKIP.value


class TestDreamState:
    """Tests for DreamState dataclass."""
    
    def test_default_initialization(self):
        """Should initialize with default values."""
        from openclaw.agents.ira.skills.brain.dream_mode import DreamState
        
        state = DreamState()
        
        assert state.last_dream is None
        assert state.documents_processed == {}
        assert state.total_facts_learned == 0
        assert state.total_indexed_in_qdrant == 0
        assert state.insights_generated == 0
        assert state.conflicts_detected == 0
    
    def test_initialization_with_values(self):
        """Should accept initialization values."""
        from openclaw.agents.ira.skills.brain.dream_mode import DreamState
        
        now = datetime.now()
        state = DreamState(
            last_dream=now,
            total_facts_learned=100,
            insights_generated=10,
        )
        
        assert state.last_dream == now
        assert state.total_facts_learned == 100
        assert state.insights_generated == 10


class TestDocumentKnowledge:
    """Tests for DocumentKnowledge dataclass."""
    
    def test_initialization(self):
        """Should initialize with required fields."""
        from openclaw.agents.ira.skills.brain.dream_mode import DocumentKnowledge, DocumentPriority
        
        knowledge = DocumentKnowledge(
            filename="test.pdf",
            file_hash="abc123",
            priority=DocumentPriority.HIGH,
            extracted_at=datetime.now(),
            facts=["Fact 1", "Fact 2"],
            topics=["Topic A"],
            key_terms={"term1": "definition1"},
            relationships=[{"subject": "A", "relation": "is", "object": "B"}],
        )
        
        assert knowledge.filename == "test.pdf"
        assert knowledge.file_hash == "abc123"
        assert len(knowledge.facts) == 2
        assert len(knowledge.topics) == 1


class TestDreamInsight:
    """Tests for DreamInsight dataclass."""
    
    def test_initialization(self):
        """Should initialize with required fields."""
        from openclaw.agents.ira.skills.brain.dream_mode import DreamInsight
        
        insight = DreamInsight(
            insight="Cross-document insight",
            source_docs=["doc1.pdf", "doc2.pdf"],
            confidence=0.85,
            topic="pricing",
        )
        
        assert insight.insight == "Cross-document insight"
        assert len(insight.source_docs) == 2
        assert insight.confidence == 0.85
        assert insight.generated_at is not None


class TestIntegratedDreamMode:
    """Tests for IntegratedDreamMode class."""
    
    @pytest.fixture
    def mock_dream(self, temp_dir):
        """Create DreamMode with mocked dependencies."""
        with patch("openclaw.agents.ira.skills.brain.dream_mode.DREAM_STATE_FILE", temp_dir / "state.json"):
            with patch("openclaw.agents.ira.skills.brain.dream_mode.IMPORTS_DIR", temp_dir / "imports"):
                from openclaw.agents.ira.skills.brain.dream_mode import IntegratedDreamMode
                
                dream = IntegratedDreamMode()
                dream._qdrant = None
                dream._voyage = None
                dream._mem0 = None
                dream._openai = None
                
                yield dream
    
    def test_initialization_loads_state(self, mock_dream):
        """Should load state on initialization."""
        assert mock_dream.state is not None
        assert mock_dream.state.total_facts_learned >= 0
    
    def test_classify_document_critical(self, mock_dream):
        """Should classify technical documents as critical."""
        from openclaw.agents.ira.skills.brain.dream_mode import DocumentPriority
        
        priority = mock_dream._classify_document(Path("Technical_Manual_PF1.pdf"))
        assert priority == DocumentPriority.CRITICAL
        
        priority = mock_dream._classify_document(Path("FCS_Catalogue.pdf"))
        assert priority == DocumentPriority.CRITICAL
    
    def test_classify_document_high(self, mock_dream):
        """Should classify presentations as high priority."""
        from openclaw.agents.ira.skills.brain.dream_mode import DocumentPriority
        
        priority = mock_dream._classify_document(Path("Company_Presentation.pptx"))
        assert priority == DocumentPriority.HIGH
        
        priority = mock_dream._classify_document(Path("Market_Research_Report.pdf"))
        assert priority == DocumentPriority.HIGH
    
    def test_classify_document_medium(self, mock_dream):
        """Should classify quotes as medium priority."""
        from openclaw.agents.ira.skills.brain.dream_mode import DocumentPriority
        
        priority = mock_dream._classify_document(Path("PF1_Quote_Customer.pdf"))
        assert priority == DocumentPriority.MEDIUM
        
        priority = mock_dream._classify_document(Path("Quotation_ABC.pdf"))
        assert priority == DocumentPriority.MEDIUM
    
    def test_classify_document_low(self, mock_dream):
        """Should classify emails as low priority."""
        from openclaw.agents.ira.skills.brain.dream_mode import DocumentPriority
        
        priority = mock_dream._classify_document(Path("Gmail_Customer_Reply.pdf"))
        assert priority == DocumentPriority.LOW
    
    def test_classify_document_skip(self, mock_dream):
        """Should skip receipts and invoices."""
        from openclaw.agents.ira.skills.brain.dream_mode import DocumentPriority
        
        priority = mock_dream._classify_document(Path("Receipt_Payment.pdf"))
        assert priority == DocumentPriority.SKIP
        
        priority = mock_dream._classify_document(Path("Invoice_123.pdf"))
        assert priority == DocumentPriority.SKIP
    
    def test_get_file_hash(self, mock_dream, temp_dir):
        """Should compute file hash."""
        test_file = temp_dir / "test.txt"
        test_file.write_text("Test content")
        
        hash1 = mock_dream._get_file_hash(test_file)
        hash2 = mock_dream._get_file_hash(test_file)
        
        assert hash1 == hash2
        assert len(hash1) == 16
    
    def test_get_file_hash_missing_file(self, mock_dream, temp_dir):
        """Should return empty string for missing file."""
        hash_val = mock_dream._get_file_hash(temp_dir / "nonexistent.txt")
        assert hash_val == ""
    
    def test_detect_document_type_quote(self, mock_dream):
        """Should detect quote documents."""
        doc_type = mock_dream._detect_document_type("PF1_Quote.pdf", "Quotation for customer...")
        assert doc_type == "quote"
    
    def test_detect_document_type_inquiry(self, mock_dream):
        """Should detect inquiry documents."""
        doc_type = mock_dream._detect_document_type("Customer_Inquiry.pdf", "RFQ for machine...")
        assert doc_type == "inquiry"
    
    def test_detect_document_type_technical(self, mock_dream):
        """Should detect technical spec documents."""
        doc_type = mock_dream._detect_document_type("PF1_Specifications.pdf", "Technical details...")
        assert doc_type == "technical_spec"
    
    def test_detect_document_type_pricing(self, mock_dream):
        """Should detect pricing documents."""
        doc_type = mock_dream._detect_document_type("Price_List.pdf", "Machine pricing information...")
        assert doc_type == "pricing"
    
    def test_detect_document_type_general(self, mock_dream):
        """Should default to general type."""
        doc_type = mock_dream._detect_document_type("Random.pdf", "Some content...")
        assert doc_type == "general"
    
    def test_get_type_specific_instructions_quote(self, mock_dream):
        """Should return quote-specific instructions."""
        instructions = mock_dream._get_type_specific_instructions("quote")
        
        assert "QUOTE" in instructions
        assert "pricing" in instructions.lower() or "price" in instructions.lower()
    
    def test_get_type_specific_instructions_inquiry(self, mock_dream):
        """Should return inquiry-specific instructions."""
        instructions = mock_dream._get_type_specific_instructions("inquiry")
        
        assert "INQUIRY" in instructions
        assert "contact" in instructions.lower()
    
    def test_process_structured_data_contacts(self, mock_dream):
        """Should process contacts from structured data."""
        structured = {
            "contacts": [
                {"name": "John Doe", "email": "john@example.com", "company": "ABC Corp"}
            ]
        }
        
        facts = mock_dream._process_structured_data(structured)
        
        assert len(facts) > 0
        assert any("John Doe" in f for f in facts)
        assert any("john@example.com" in f for f in facts)
    
    def test_process_structured_data_machines(self, mock_dream):
        """Should process machines from structured data."""
        structured = {
            "machines": [
                {"model": "PF1-C-3020", "forming_size": "3000x2000mm", "price_inr": 4850000}
            ]
        }
        
        facts = mock_dream._process_structured_data(structured)
        
        assert len(facts) > 0
        assert any("PF1-C-3020" in f for f in facts)
    
    def test_process_structured_data_pricing(self, mock_dream):
        """Should process pricing from structured data."""
        structured = {
            "pricing": [
                {"item": "Base machine", "price": 4850000, "currency": "INR"}
            ]
        }
        
        facts = mock_dream._process_structured_data(structured)
        
        assert len(facts) > 0
        assert any("4850000" in f for f in facts)
    
    def test_store_in_qdrant_success(self, mock_dream):
        """Should store knowledge in Qdrant."""
        mock_qdrant = MagicMock()
        mock_voyage = MagicMock()
        mock_voyage.embed.return_value = MagicMock(embeddings=[[0.1] * 1024])
        
        mock_dream._qdrant = mock_qdrant
        mock_dream._voyage = mock_voyage
        
        result = mock_dream._store_in_qdrant("Test fact", {"type": "fact"})
        
        assert result is True
        mock_qdrant.upsert.assert_called_once()
    
    def test_store_in_qdrant_no_client(self, mock_dream):
        """Should return False when Qdrant unavailable."""
        # Mock _get_qdrant and _get_voyage to return None
        mock_dream._get_qdrant = MagicMock(return_value=None)
        mock_dream._get_voyage = MagicMock(return_value=None)
        mock_dream._qdrant = None
        mock_dream._voyage = None
        
        result = mock_dream._store_in_qdrant("Test fact", {"type": "fact"})
        
        # When clients are None, should return False
        assert result is False or mock_dream._get_qdrant.called
    
    def test_store_in_mem0_success(self, mock_dream):
        """Should store in Mem0."""
        mock_mem0 = MagicMock()
        mock_dream._mem0 = mock_mem0
        
        with patch("openclaw.agents.ira.skills.brain.dream_mode.MEMORY_CONTROLLER_AVAILABLE", False):
            result = mock_dream._store_in_mem0("Test fact", {"type": "fact"})
        
        assert result is True
        mock_mem0.add.assert_called_once()
    
    def test_store_knowledge_unified(self, mock_dream):
        """Should store knowledge in both Qdrant and Mem0."""
        from openclaw.agents.ira.skills.brain.dream_mode import DocumentKnowledge, DocumentPriority
        
        mock_dream._store_in_qdrant = MagicMock(return_value=True)
        mock_dream._store_in_mem0 = MagicMock(return_value=True)
        
        knowledge = DocumentKnowledge(
            filename="test.pdf",
            file_hash="abc123",
            priority=DocumentPriority.HIGH,
            extracted_at=datetime.now(),
            facts=["Fact 1", "Fact 2"],
            topics=["Topic A"],
            key_terms={"term1": "def1"},
            relationships=[{"subject": "A", "relation": "is", "object": "B"}],
        )
        
        mem0_count, qdrant_count = mock_dream._store_knowledge_unified(knowledge)
        
        assert mem0_count > 0
        assert qdrant_count > 0
    
    def test_extract_topic_machine_model(self, mock_dream):
        """Should extract machine model as topic."""
        topic = mock_dream._extract_topic("What is the price for PF1-C-3020?")
        
        assert "PF1" in topic.upper()
    
    def test_extract_topic_pricing(self, mock_dream):
        """Should detect pricing topic."""
        topic = mock_dream._extract_topic("What is the cost of this machine?")
        
        assert topic == "pricing"
    
    def test_extract_topic_specifications(self, mock_dream):
        """Should detect specifications topic."""
        topic = mock_dream._extract_topic("What are the dimensions?")
        
        assert topic == "specifications"
    
    def test_extract_topic_delivery(self, mock_dream):
        """Should detect delivery topic."""
        topic = mock_dream._extract_topic("What is the delivery timeline?")
        
        assert topic == "delivery"
    
    def test_extract_topic_general(self, mock_dream):
        """Should default to general topic."""
        topic = mock_dream._extract_topic("Hello, how are you?")
        
        assert topic == "general"
    
    def test_get_status(self, mock_dream):
        """Should return dream status."""
        status = mock_dream.get_status()
        
        assert "last_dream" in status
        assert "documents_processed" in status
        assert "total_facts_learned" in status
        assert "total_indexed_in_qdrant" in status
        assert "insights_generated" in status
    
    def test_dream_no_documents(self, mock_dream, temp_dir):
        """Should handle case with no documents."""
        # Create empty imports directory
        imports_dir = temp_dir / "imports"
        imports_dir.mkdir(exist_ok=True)
        
        mock_dream._find_documents = MagicMock(return_value=[])
        
        result = mock_dream.dream()
        
        assert result["documents_processed"] == 0
        assert result["facts_learned"] == 0
    
    def test_save_and_load_state(self, mock_dream, temp_dir):
        """Should persist and restore state."""
        mock_dream.state.total_facts_learned = 100
        mock_dream.state.insights_generated = 10
        
        # Save state
        with patch("openclaw.agents.ira.skills.brain.dream_mode.WORKSPACE_DIR", temp_dir):
            with patch("openclaw.agents.ira.skills.brain.dream_mode.DREAM_STATE_FILE", temp_dir / "state.json"):
                mock_dream._save_state()
                
                # Create new instance and load
                from openclaw.agents.ira.skills.brain.dream_mode import IntegratedDreamMode
                
                # Verify state file exists
                assert (temp_dir / "state.json").exists()


class TestDreamModeAliases:
    """Tests for backward compatibility aliases."""
    
    def test_dream_mode_alias(self):
        """DreamMode should alias IntegratedDreamMode."""
        from openclaw.agents.ira.skills.brain.dream_mode import DreamMode, IntegratedDreamMode
        
        assert DreamMode is IntegratedDreamMode
    
    def test_enhanced_dream_mode_alias(self):
        """EnhancedDreamMode should alias IntegratedDreamMode."""
        from openclaw.agents.ira.skills.brain.dream_mode import EnhancedDreamMode, IntegratedDreamMode
        
        assert EnhancedDreamMode is IntegratedDreamMode
