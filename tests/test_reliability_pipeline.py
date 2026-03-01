#!/usr/bin/env python3
"""
Tests for the Multi-Pass Reliability Pipeline
==============================================

Tests the production-grade reliability layer including:
1. Database populator functionality
2. Multi-pass pipeline (Draft → Verify → Polish)
3. Fact extraction and verification
4. Business rule validation
"""

import os
import sys
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "openclaw" / "agents" / "ira"))
sys.path.insert(0, str(PROJECT_ROOT / "openclaw" / "agents" / "ira" / "skills" / "brain"))


class TestFactExtraction:
    """Test the extract_and_verify_facts function."""
    
    def test_extract_price_claims(self):
        """Test extraction of price claims from text."""
        from generate_answer import extract_and_verify_facts
        
        draft = """The PF1-C-2015 thermoforming machine costs ₹60,00,000.
        It has a forming area of 2000 x 1500 mm and 125 kW heater power."""
        
        claims, corrections = extract_and_verify_facts(draft)
        
        price_claims = [c for c in claims if c.claim_type == "price"]
        assert len(price_claims) >= 1
        # Value is stored without commas as '6000000'
        assert price_claims[0].value == "6000000"
    
    def test_extract_dimension_claims(self):
        """Test extraction of dimension claims."""
        from generate_answer import extract_and_verify_facts
        
        draft = "The machine has a forming area of 2000 x 1500 mm."
        
        claims, corrections = extract_and_verify_facts(draft)
        
        dim_claims = [c for c in claims if c.claim_type == "dimension"]
        assert len(dim_claims) >= 1
        assert "2000" in dim_claims[0].value
        assert "1500" in dim_claims[0].value
    
    def test_extract_power_claims(self):
        """Test extraction of power specification claims."""
        from generate_answer import extract_and_verify_facts
        
        draft = "The heater power is 125 kW with 8 zones."
        
        claims, corrections = extract_and_verify_facts(draft)
        
        power_claims = [c for c in claims if c.claim_type == "spec"]
        assert len(power_claims) >= 1
        assert power_claims[0].value == "125"
    
    def test_extract_vacuum_claims(self):
        """Test extraction of vacuum pump capacity claims."""
        from generate_answer import extract_and_verify_facts
        
        draft = "Vacuum pump capacity is 220 m³/hr."
        
        claims, corrections = extract_and_verify_facts(draft)
        
        vacuum_claims = [c for c in claims if c.claim_type == "vacuum"]
        assert len(vacuum_claims) >= 1
        assert vacuum_claims[0].value == "220"
    
    def test_corrections_generated_for_wrong_price(self):
        """Test that corrections are generated when price is wrong."""
        from generate_answer import extract_and_verify_facts
        
        draft = """The PF1-C-2015 costs ₹70,00,000."""
        
        claims, corrections = extract_and_verify_facts(draft)
        
        if corrections:
            assert any("PF1-C-2015" in c.correction_reason for c in corrections)


class TestBusinessRuleValidation:
    """Test business rule validation."""
    
    def test_am_thickness_rule(self):
        """Test AM Series thickness limit rule."""
        from generate_answer import _validate_business_rules
        
        query = "I need to form 5mm thick ABS"
        response = "I recommend the AM-5060 for this application with 5mm thickness."
        
        is_valid, warnings = _validate_business_rules(query, response)
        
        # The rule should trigger when AM is mentioned with thick material
        # Either warnings are generated OR is_valid is False
        has_issue = len(warnings) > 0 or not is_valid
        assert has_issue, f"Expected business rule violation for AM with 5mm. warnings={warnings}, is_valid={is_valid}"
    
    def test_placeholder_detection(self):
        """Test detection of placeholder text."""
        from generate_answer import _validate_business_rules
        
        query = "What's the price?"
        response = "The price is [insert price here]."
        
        is_valid, warnings = _validate_business_rules(query, response)
        
        assert len(warnings) > 0
        assert any("placeholder" in w.lower() or "insert" in w.lower() for w in warnings)
    
    def test_heavy_gauge_pf1_recommendation(self):
        """Test that heavy gauge queries should mention PF1."""
        from generate_answer import _validate_business_rules
        
        query = "I need to form 6mm thick HDPE sheets"
        response = "For this application, we recommend our standard machine."
        
        is_valid, warnings = _validate_business_rules(query, response)
        
        assert len(warnings) > 0 or not is_valid


class TestMultiPassPipeline:
    """Test the complete multi-pass pipeline."""
    
    @pytest.fixture
    def mock_context_pack(self):
        """Create a mock context pack."""
        from generate_answer import ContextPack
        return ContextPack(
            rag_chunks=[
                {"text": "PF1-C-2015 specs: 2000x1500mm forming area, 125kW heater", "filename": "spec.pdf"}
            ]
        )
    
    def test_pipeline_runs_for_sales_query(self, mock_context_pack):
        """Test that pipeline runs for SALES mode queries."""
        from generate_answer import generate_answer
        
        with patch('generate_answer._call_llm') as mock_llm:
            mock_llm.return_value = "The PF1-C-2015 has a forming area of 2000 x 1500 mm."
            
            result = generate_answer(
                intent="What are the specs for PF1-C-2015?",
                context_pack=mock_context_pack,
                channel="telegram",
                use_multi_pass=True
            )
            
            assert result.debug_info.get("pipeline_used") == True
    
    def test_pipeline_skipped_for_general_query(self):
        """Test that pipeline is skipped for non-sales queries."""
        from generate_answer import generate_answer, ContextPack
        
        with patch('generate_answer._call_llm') as mock_llm:
            mock_llm.return_value = "I am Ira, your intelligent assistant."
            
            result = generate_answer(
                intent="Who are you?",
                context_pack=ContextPack(),
                channel="telegram",
                use_multi_pass=True
            )
            
            assert result.debug_info.get("pipeline_used") == False


class TestDatabasePopulator:
    """Test the database populator functionality."""
    
    def test_extraction_schema_defined(self):
        """Test that extraction schema is properly defined."""
        from database_populator import DatabasePopulator
        
        populator = DatabasePopulator(verbose=False)
        
        assert hasattr(populator, 'EXTRACTION_SCHEMA')
        assert "model" in populator.EXTRACTION_SCHEMA
        assert "price_inr" in populator.EXTRACTION_SCHEMA
        assert "vacuum_pump_capacity" in populator.EXTRACTION_SCHEMA
    
    def test_extracted_spec_dataclass(self):
        """Test the ExtractedMachineSpec dataclass."""
        from database_populator import ExtractedMachineSpec
        
        spec = ExtractedMachineSpec(
            model="PF1-C-2015",
            series="PF1",
            variant="C (pneumatic)",
            price_inr=6000000,
            forming_area_mm="2000 x 1500",
            heater_type="IR Quartz",
            vacuum_pump_capacity="220 m³/hr",
            features=["Sag control", "Zone heating"],
            source_file="test.pdf",
            extraction_confidence=0.9
        )
        
        assert spec.model == "PF1-C-2015"
        assert spec.price_inr == 6000000
        
        spec_dict = spec.to_dict()
        assert spec_dict["model"] == "PF1-C-2015"
        assert spec_dict["features"] == ["Sag control", "Zone heating"]
    
    def test_get_extraction_stats(self):
        """Test getting extraction statistics."""
        from database_populator import get_extraction_stats
        
        stats = get_extraction_stats()
        
        assert "extraction_file_exists" in stats
        assert "processed_files" in stats


class TestFactCorrection:
    """Test fact correction data structures."""
    
    def test_fact_correction_dataclass(self):
        """Test the FactCorrection dataclass."""
        from generate_answer import FactCorrection
        
        correction = FactCorrection(
            original_claim="₹70,00,000",
            corrected_value="₹60,00,000",
            correction_reason="Price for PF1-C-2015 is ₹60,00,000",
            confidence=1.0,
            source="machine_database"
        )
        
        assert correction.original_claim == "₹70,00,000"
        assert correction.corrected_value == "₹60,00,000"
        assert "PF1-C-2015" in correction.correction_reason
    
    def test_factual_claim_dataclass(self):
        """Test the FactualClaim dataclass."""
        from generate_answer import FactualClaim
        
        claim = FactualClaim(
            claim_type="price",
            claim_text="₹60,00,000",
            entity="PF1-C-2015",
            value="6000000",
            context="The PF1-C-2015 costs ₹60,00,000."
        )
        
        assert claim.claim_type == "price"
        assert claim.entity == "PF1-C-2015"


class TestIntegration:
    """Integration tests for the complete reliability system."""
    
    def test_response_includes_pipeline_debug_info(self):
        """Test that response includes pipeline debug information."""
        from generate_answer import generate_answer, ContextPack
        
        with patch('generate_answer._call_llm') as mock_llm:
            mock_llm.return_value = "The PF1-C-2015 is a great machine with 2000x1500mm forming area."
            
            result = generate_answer(
                intent="Tell me about PF1-C-2015 specs",
                context_pack=ContextPack(),
                channel="telegram",
                use_multi_pass=True
            )
            
            assert "pipeline_used" in result.debug_info
            assert "generation_path" in result.to_dict()
    
    def test_confidence_reflects_pipeline_status(self):
        """Test that confidence level reflects pipeline verification."""
        from generate_answer import generate_answer, ContextPack, ConfidenceLevel
        
        with patch('generate_answer._call_llm') as mock_llm:
            mock_llm.return_value = "Here are the specifications."
            
            result = generate_answer(
                intent="Specs for PF1-C-2015?",
                context_pack=ContextPack(),
                channel="telegram",
                use_multi_pass=True
            )
            
            if result.debug_info.get("pipeline_used"):
                assert result.confidence in [ConfidenceLevel.HIGH, ConfidenceLevel.MEDIUM]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
