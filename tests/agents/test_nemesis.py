"""
Tests for the Nemesis correction-learning agent.

Covers: correction ingestion, failure ingestion, Telegram feedback parsing,
category classification, and error handling.
"""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

import pytest


@pytest.fixture
def nemesis():
    """Create a Nemesis instance with mocked dependencies."""
    with patch("openclaw.agents.ira.src.agents.nemesis.agent.store") as mock_store, \
         patch("openclaw.agents.ira.src.agents.nemesis.agent.CONFIG_AVAILABLE", False):
        mock_store.record_correction.return_value = "corr_001"
        mock_store.record_failure.return_value = "fail_001"
        mock_store.get_corrections.return_value = []
        mock_store.get_unapplied_corrections.return_value = []

        from openclaw.agents.ira.src.agents.nemesis.agent import Nemesis
        n = Nemesis()
        n._client = MagicMock()
        n._mem0 = MagicMock()
        n._mem0.add.return_value = True
        yield n, mock_store


class TestNemesisIngestCorrection:

    def test_ingest_correction_stores_and_returns_id(self, nemesis):
        n, mock_store = nemesis

        with patch.object(n, "_store_in_mem0", return_value=True), \
             patch.object(n, "_flag_qdrant_contradictions"):
            result = n.ingest_correction(
                wrong_info="Customer-A owes X.XX Cr",
                correct_info="Customer-A only has Y Cr pending",
                source="telegram_feedback",
                entity="Customer-A",
                category="customer",
                severity="critical",
            )

        assert "correction_id" in result
        assert result["entity"] == "Customer-A"
        assert result["category"] == "customer"
        assert result["severity"] == "critical"

    def test_ingest_correction_auto_classifies_category(self, nemesis):
        n, mock_store = nemesis

        with patch.object(n, "_classify_category", return_value="pricing") as mock_classify, \
             patch.object(n, "_extract_entity", return_value="PF1-C-2015") as mock_entity, \
             patch.object(n, "_store_in_mem0", return_value=True), \
             patch.object(n, "_flag_qdrant_contradictions"):
            result = n.ingest_correction(
                wrong_info="PF1-C-2015 costs 50L",
                correct_info="PF1-C-2015 costs 60L",
                source="telegram_feedback",
            )

        mock_classify.assert_called_once()
        mock_entity.assert_called_once()
        assert result["correction_id"] == "corr_001"

    def test_ingest_correction_invalidates_researcher_cache(self, nemesis):
        n, _ = nemesis

        with patch.object(n, "_store_in_mem0", return_value=True), \
             patch.object(n, "_flag_qdrant_contradictions"), \
             patch("openclaw.agents.ira.src.agents.researcher.agent.invalidate_cache") as mock_inv:
            n.ingest_correction(
                wrong_info="wrong",
                correct_info="right",
                entity="TestCo",
            )
            mock_inv.assert_called_once_with(entity="TestCo")


class TestNemesisIngestFailure:

    def test_ingest_failure_records_and_returns(self, nemesis):
        n, mock_store = nemesis

        with patch.object(n, "_extract_corrections_from_issues", return_value=0):
            result = n.ingest_failure(
                query="What's our order book?",
                response="Outstanding: ₹XX.XX Cr...",
                issues=["PRICING_DISCLAIMER_MISSING"],
                quality_score=0.6,
                source="sophia_reflection",
            )

        assert result["failure_id"] == "fail_001"
        assert result["issues"] == ["PRICING_DISCLAIMER_MISSING"]
        mock_store.record_failure.assert_called_once()

    def test_ingest_failure_extracts_corrections_from_issues(self, nemesis):
        n, mock_store = nemesis

        with patch.object(n, "_extract_corrections_from_issues", return_value=2) as mock_extract:
            result = n.ingest_failure(
                query="test",
                response="test response",
                issues=["WRONG_PRICE", "WRONG_MODEL"],
            )

        assert result["corrections_extracted"] == 2
        mock_extract.assert_called_once()


class TestNemesisErrorHandling:

    def test_ingest_correction_handles_mem0_failure(self, nemesis):
        n, mock_store = nemesis

        with patch.object(n, "_store_in_mem0", side_effect=Exception("Mem0 down")), \
             patch.object(n, "_flag_qdrant_contradictions"):
            try:
                result = n.ingest_correction(
                    wrong_info="wrong",
                    correct_info="right",
                    entity="TestCo",
                )
            except Exception:
                pass
            mock_store.record_correction.assert_called_once()

    def test_ingest_failure_handles_no_issues(self, nemesis):
        n, mock_store = nemesis

        result = n.ingest_failure(
            query="test",
            response="test response",
            issues=None,
        )

        assert result["failure_id"] == "fail_001"
        assert result["corrections_extracted"] == 0
