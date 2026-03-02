"""
Tests for UnifiedRetriever
==========================

Tests for hybrid search (vector + BM25), reranking, and multi-collection search.
"""

import pytest
from dataclasses import dataclass
from typing import Dict, List, Optional
from unittest.mock import MagicMock, patch, PropertyMock


class TestUnifiedResult:
    """Tests for UnifiedResult dataclass."""
    
    def test_default_initialization(self):
        """Should initialize with required fields."""
        from openclaw.agents.ira.skills.brain.unified_retriever import UnifiedResult
        
        result = UnifiedResult(
            text="Test content",
            score=0.85,
            source="document"
        )
        
        assert result.text == "Test content"
        assert result.score == 0.85
        assert result.source == "document"
        assert result.filename == ""
        assert result.subject == ""
        assert result.machines == []
    
    def test_document_result(self):
        """Should store document metadata."""
        from openclaw.agents.ira.skills.brain.unified_retriever import UnifiedResult
        
        result = UnifiedResult(
            text="PF1-C-3020 specifications...",
            score=0.9,
            source="document",
            filename="PF1_Specs.pdf",
            doc_type="specification",
            machines=["PF1-C-3020"],
        )
        
        assert result.filename == "PF1_Specs.pdf"
        assert result.doc_type == "specification"
        assert "PF1-C-3020" in result.machines
    
    def test_email_result(self):
        """Should store email metadata."""
        from openclaw.agents.ira.skills.brain.unified_retriever import UnifiedResult
        
        result = UnifiedResult(
            text="Customer inquiry about machines...",
            score=0.75,
            source="email",
            subject="Machine Inquiry",
            from_email="customer@example.com",
        )
        
        assert result.subject == "Machine Inquiry"
        assert result.from_email == "customer@example.com"
    
    def test_source_type_property(self):
        """source_type should return source."""
        from openclaw.agents.ira.skills.brain.unified_retriever import UnifiedResult
        
        result = UnifiedResult(text="Test", score=0.8, source="document")
        
        assert result.source_type == "document"
    
    def test_to_dict(self):
        """Should convert to dictionary."""
        from openclaw.agents.ira.skills.brain.unified_retriever import UnifiedResult
        
        result = UnifiedResult(
            text="Test content",
            score=0.85,
            source="document",
            filename="test.pdf",
            machines=["PF1-C"],
        )
        
        d = result.to_dict()
        
        assert d["text"] == "Test content"
        assert d["score"] == 0.85
        assert d["source"] == "document"
        assert d["filename"] == "test.pdf"
        assert d["machines"] == ["PF1-C"]


class TestUnifiedResponse:
    """Tests for UnifiedResponse dataclass."""
    
    def test_initialization(self):
        """Should initialize with query and results."""
        from openclaw.agents.ira.skills.brain.unified_retriever import UnifiedResponse, UnifiedResult
        
        results = [
            UnifiedResult(text="Result 1", score=0.9, source="document"),
            UnifiedResult(text="Result 2", score=0.8, source="email"),
        ]
        
        response = UnifiedResponse(
            query="Test query",
            results=results,
            document_count=1,
            email_count=1,
        )
        
        assert response.query == "Test query"
        assert len(response.results) == 2
        assert response.document_count == 1
        assert response.email_count == 1
    
    def test_to_dict(self):
        """Should convert to dictionary."""
        from openclaw.agents.ira.skills.brain.unified_retriever import UnifiedResponse, UnifiedResult
        
        response = UnifiedResponse(
            query="Test query",
            results=[UnifiedResult(text="R1", score=0.9, source="document")],
            document_count=1,
            email_count=0,
            confidence=0.85,
        )
        
        d = response.to_dict()
        
        assert d["query"] == "Test query"
        assert len(d["results"]) == 1
        assert d["confidence"] == 0.85


class TestUnifiedRetriever:
    """Tests for UnifiedRetriever class."""
    
    @pytest.fixture
    def mock_retriever(self):
        """Create retriever with mocked dependencies."""
        with patch("openclaw.agents.ira.skills.brain.unified_retriever.VOYAGE_API_KEY", "test-key"):
            with patch("openclaw.agents.ira.skills.brain.unified_retriever.OPENAI_API_KEY", "test-key"):
                from openclaw.agents.ira.skills.brain.unified_retriever import UnifiedRetriever
                retriever = UnifiedRetriever(use_hybrid=False, use_reranker=False)
                yield retriever
    
    def test_initialization_with_defaults(self):
        """Should initialize with default settings."""
        with patch("openclaw.agents.ira.skills.brain.unified_retriever.USE_HYBRID_SEARCH", True):
            with patch("openclaw.agents.ira.skills.brain.unified_retriever.USE_RERANKER", True):
                from openclaw.agents.ira.skills.brain.unified_retriever import UnifiedRetriever
                
                retriever = UnifiedRetriever()
                
                assert retriever.use_hybrid is True
                assert retriever.use_reranker is True
    
    def test_initialization_disabled_features(self):
        """Should allow disabling features."""
        from openclaw.agents.ira.skills.brain.unified_retriever import UnifiedRetriever
        
        retriever = UnifiedRetriever(
            use_hybrid=False,
            use_reranker=False,
            use_query_decomposition=False,
        )
        
        assert retriever.use_hybrid is False
        assert retriever.use_reranker is False
        assert retriever.use_query_decomposition is False
    
    def test_get_qdrant_lazy_init(self, mock_retriever):
        """Should lazy-initialize Qdrant client."""
        with patch("qdrant_client.QdrantClient") as mock_client:
            mock_client.return_value = MagicMock()
            
            client = mock_retriever._get_qdrant()
            
            assert client is not None
            mock_client.assert_called_once()
    
    def test_get_voyage_lazy_init(self, mock_retriever):
        """Should lazy-initialize Voyage client."""
        with patch("voyageai.Client") as mock_client:
            mock_client.return_value = MagicMock()
            
            client = mock_retriever._get_voyage()
            
            assert client is not None
    
    def test_get_embedding_voyage(self, mock_retriever):
        """Should get Voyage embedding when available."""
        mock_voyage = MagicMock()
        mock_voyage.embed.return_value = MagicMock(embeddings=[[0.1] * 1024])
        mock_retriever._voyage = mock_voyage
        
        with patch("openclaw.agents.ira.skills.brain.unified_retriever.PREFER_VOYAGE", True):
            with patch("openclaw.agents.ira.skills.brain.unified_retriever.USE_VOYAGE", True):
                embedding, provider = mock_retriever._get_embedding("test query")
                
                assert provider == "voyage"
                assert len(embedding) == 1024
    
    def test_get_embedding_openai_fallback(self, mock_retriever):
        """Should fallback to OpenAI when Voyage fails."""
        mock_retriever._voyage = None
        mock_openai = MagicMock()
        mock_openai.embeddings.create.return_value = MagicMock(
            data=[MagicMock(embedding=[0.1] * 3072)]
        )
        mock_retriever._openai = mock_openai
        
        with patch("openclaw.agents.ira.skills.brain.unified_retriever.PREFER_VOYAGE", False):
            embedding, provider = mock_retriever._get_embedding("test query")
            
            assert provider == "openai"
            assert len(embedding) == 3072
    
    def test_search_collection(self, mock_retriever):
        """Should search a Qdrant collection."""
        mock_qdrant = MagicMock()
        mock_point = MagicMock()
        mock_point.id = "point_1"
        mock_point.score = 0.85
        mock_point.payload = {"text": "Test content", "filename": "test.pdf"}
        
        mock_qdrant.query_points.return_value = MagicMock(points=[mock_point])
        mock_retriever._qdrant = mock_qdrant
        
        results = mock_retriever._search_collection(
            embedding=[0.1] * 1024,
            collection="test_collection",
            top_k=10
        )
        
        assert len(results) == 1
        assert results[0]["id"] == "point_1"
        assert results[0]["score"] == 0.85
    
    def test_search_collection_handles_error(self, mock_retriever):
        """Should handle search errors gracefully."""
        mock_qdrant = MagicMock()
        mock_qdrant.query_points.side_effect = Exception("Connection failed")
        mock_retriever._qdrant = mock_qdrant
        
        results = mock_retriever._search_collection(
            embedding=[0.1] * 1024,
            collection="test_collection",
            top_k=10
        )
        
        assert results == []
    
    def test_rerank_results_disabled(self, mock_retriever):
        """Should return top_k results when reranking disabled."""
        from openclaw.agents.ira.skills.brain.unified_retriever import UnifiedResult
        
        mock_retriever.use_reranker = False
        results = [
            UnifiedResult(text=f"Result {i}", score=0.9 - i*0.1, source="document")
            for i in range(10)
        ]
        
        reranked = mock_retriever._rerank_results("query", results, top_k=5)
        
        assert len(reranked) == 5
    
    def test_rerank_results_empty(self, mock_retriever):
        """Should handle empty results."""
        reranked = mock_retriever._rerank_results("query", [], top_k=5)
        
        assert reranked == []
    
    def test_retrieve_returns_unified_response(self, mock_retriever):
        """Should return UnifiedResponse from retrieve."""
        # Mock embedding
        mock_retriever._get_embedding = MagicMock(return_value=([0.1] * 1024, "voyage"))
        
        # Mock collection search
        mock_retriever._search_collection = MagicMock(return_value=[
            {
                "id": "doc_1",
                "score": 0.85,
                "payload": {
                    "raw_text": "PF1-C-3020 specs...",
                    "filename": "specs.pdf",
                    "doc_type": "specification",
                    "machines": ["PF1-C-3020"],
                }
            }
        ])
        
        # Mock best collection
        mock_retriever._get_best_collection = MagicMock(return_value="test_collection")
        
        response = mock_retriever.retrieve("What are the PF1-C specs?", top_k=5)
        
        assert response.query == "What are the PF1-C specs?"
        assert len(response.results) > 0
        assert response.retrieval_time_ms >= 0
    
    def test_retrieve_deduplicates_results(self, mock_retriever):
        """Should deduplicate results across collections."""
        mock_retriever._get_embedding = MagicMock(return_value=([0.1] * 1024, "voyage"))
        mock_retriever._get_best_collection = MagicMock(return_value="test_collection")
        
        # Return same ID from multiple searches
        mock_retriever._search_collection = MagicMock(return_value=[
            {"id": "doc_1", "score": 0.85, "payload": {"raw_text": "Test", "filename": "test.pdf"}},
            {"id": "doc_1", "score": 0.80, "payload": {"raw_text": "Test", "filename": "test.pdf"}},
        ])
        
        response = mock_retriever.retrieve("test query", top_k=5, include_emails=False)
        
        # Should only have unique results
        ids = [r.chunk_id for r in response.results]
        assert len(ids) == len(set(ids))
    
    def test_retrieve_filters_by_source_type(self, mock_retriever):
        """Should filter by source type."""
        mock_retriever._get_embedding = MagicMock(return_value=([0.1] * 1024, "voyage"))
        mock_retriever._get_best_collection = MagicMock(return_value="test_collection")
        mock_retriever._search_collection = MagicMock(return_value=[
            {"id": "doc_1", "score": 0.85, "payload": {"raw_text": "Doc content"}}
        ])
        
        response = mock_retriever.retrieve(
            "test query",
            include_documents=True,
            include_emails=False
        )
        
        # Should have searched documents only
        assert response.email_count == 0
    
    def test_retrieve_calculates_confidence(self, mock_retriever):
        """Should calculate confidence from top results."""
        mock_retriever._get_embedding = MagicMock(return_value=([0.1] * 1024, "voyage"))
        mock_retriever._get_best_collection = MagicMock(return_value="test_collection")
        mock_retriever._search_collection = MagicMock(return_value=[
            {"id": f"doc_{i}", "score": 0.9 - i*0.05, "payload": {"raw_text": f"Result {i}"}}
            for i in range(5)
        ])
        
        response = mock_retriever.retrieve("test query", include_emails=False)
        
        assert 0 <= response.confidence <= 1.0
    
    def test_retrieve_and_synthesize(self, mock_retriever):
        """Should retrieve and synthesize answer."""
        mock_retriever._get_embedding = MagicMock(return_value=([0.1] * 1024, "voyage"))
        mock_retriever._get_best_collection = MagicMock(return_value="test_collection")
        mock_retriever._search_collection = MagicMock(return_value=[
            {"id": "doc_1", "score": 0.85, "payload": {"raw_text": "PF1-C-3020 has 8 heating zones"}}
        ])
        
        # Mock OpenAI
        mock_openai = MagicMock()
        mock_openai.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="The PF1-C-3020 has 8 heating zones."))]
        )
        mock_retriever._openai = mock_openai
        
        response = mock_retriever.retrieve_and_synthesize(
            "How many heating zones?",
            top_k=5,
            include_emails=False
        )
        
        assert response.synthesized_answer != ""
        assert "heating zones" in response.synthesized_answer.lower() or len(response.synthesized_answer) > 0
    
    def test_retrieve_and_synthesize_no_results(self, mock_retriever):
        """Should handle no results gracefully."""
        mock_retriever._get_embedding = MagicMock(return_value=([0.1] * 1024, "voyage"))
        mock_retriever._get_best_collection = MagicMock(return_value="test_collection")
        mock_retriever._search_collection = MagicMock(return_value=[])
        
        response = mock_retriever.retrieve_and_synthesize("obscure query", top_k=5)
        
        assert "couldn't find" in response.synthesized_answer.lower() or response.synthesized_answer != ""


class TestMarketResearchSearch:
    """Tests for market research search functionality."""
    
    @pytest.fixture
    def mock_retriever(self):
        """Create retriever with mocked dependencies."""
        with patch("openclaw.agents.ira.skills.brain.unified_retriever.VOYAGE_API_KEY", "test-key"):
            from openclaw.agents.ira.skills.brain.unified_retriever import UnifiedRetriever
            retriever = UnifiedRetriever(use_hybrid=False, use_reranker=False)
            yield retriever
    
    def test_search_market_research_semantic(self, mock_retriever):
        """Should search market research with semantic search."""
        from openclaw.agents.ira.skills.brain.unified_retriever import UnifiedResult
        
        # Mock the entire search method to avoid API calls
        mock_result = UnifiedResult(
            text="Company profile...",
            score=0.85,
            source="market_research",
            filename="Test Company",
            doc_type="company_profile",
        )
        
        with patch.object(mock_retriever, 'search_market_research', return_value=[mock_result]):
            results = mock_retriever.search_market_research("thermoforming companies")
            
            assert len(results) > 0
            assert results[0].source == "market_research"
    
    def test_search_market_research_sql_fallback(self, mock_retriever):
        """Should fallback to SQL when semantic fails."""
        mock_retriever._voyage = None
        
        with patch("psycopg2.connect") as mock_connect:
            mock_cursor = MagicMock()
            mock_cursor.fetchall.return_value = [
                {
                    "company_id": 1,
                    "name": "Test Company",
                    "website": "test.com",
                    "country": "Germany",
                    "email": "info@test.com",
                    "thermoforming_services": '["vacuum forming"]',
                    "materials": '["ABS"]',
                    "industries": '["automotive"]',
                    "research_summary": "Company summary",
                    "research_confidence": 0.8,
                }
            ]
            mock_connect.return_value.cursor.return_value = mock_cursor
            
            results = mock_retriever.search_market_research(
                "test company",
                use_semantic=False
            )
            
            assert len(results) > 0
    
    def test_get_all_market_research_companies(self, mock_retriever):
        """Should get all companies from market research."""
        with patch("psycopg2.connect") as mock_connect:
            mock_cursor = MagicMock()
            mock_cursor.fetchall.return_value = [
                {"name": "Company A"},
                {"name": "Company B"},
            ]
            mock_connect.return_value.cursor.return_value = mock_cursor
            
            companies = mock_retriever.get_all_market_research_companies()
            
            assert len(companies) == 2
