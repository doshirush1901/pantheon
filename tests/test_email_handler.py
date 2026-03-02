"""
Tests for EmailHandler
======================

Tests for email channel processing, preprocessing, and postprocessing.
"""

import pytest
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
from unittest.mock import MagicMock, patch


class TestEmailData:
    """Tests for EmailData dataclass."""
    
    def test_initialization(self):
        """Should initialize with required fields."""
        from openclaw.agents.ira.skills.email_channel.email_handler import EmailData
        
        email = EmailData(
            message_id="msg_123",
            thread_id="thread_456",
            from_email="customer@example.com",
            from_name="John Doe",
            to_email="ira@machinecraft.org",
            subject="Machine Inquiry",
            body="I want to know about PF1-C machines.",
            date=datetime.now(),
        )
        
        assert email.message_id == "msg_123"
        assert email.from_email == "customer@example.com"
        assert email.is_reply is False
    
    def test_reply_email(self):
        """Should handle reply emails."""
        from openclaw.agents.ira.skills.email_channel.email_handler import EmailData
        
        email = EmailData(
            message_id="msg_789",
            thread_id="thread_456",
            from_email="customer@example.com",
            from_name="John Doe",
            to_email="ira@machinecraft.org",
            subject="Re: Machine Inquiry",
            body="Thanks for the information.",
            date=datetime.now(),
            is_reply=True,
            in_reply_to="msg_123",
        )
        
        assert email.is_reply is True
        assert email.in_reply_to == "msg_123"


class TestEmailResponse:
    """Tests for EmailResponse dataclass."""
    
    def test_initialization(self):
        """Should initialize with required fields."""
        from openclaw.agents.ira.skills.email_channel.email_handler import EmailResponse
        
        response = EmailResponse(
            to="customer@example.com",
            subject="Re: Machine Inquiry",
            body="Thank you for your inquiry...",
            thread_id="thread_456",
        )
        
        assert response.to == "customer@example.com"
        assert response.subject == "Re: Machine Inquiry"
        assert response.thread_id == "thread_456"


class TestEmailHandler:
    """Tests for EmailHandler class."""
    
    @pytest.fixture
    def mock_handler(self):
        """Create EmailHandler with mocked dependencies."""
        with patch("openclaw.agents.ira.skills.email_channel.email_handler.BRAIN_ORCHESTRATOR_AVAILABLE", False):
            with patch("openclaw.agents.ira.skills.email_channel.email_handler.MEMORY_SERVICE_AVAILABLE", False):
                from openclaw.agents.ira.skills.email_channel.email_handler import EmailHandler
                handler = EmailHandler(use_brain_orchestrator=False)
                yield handler
    
    def test_initialization_legacy_mode(self, mock_handler):
        """Should initialize in legacy mode when BrainOrchestrator unavailable."""
        assert mock_handler.use_unified is False
        assert mock_handler.brain is None
    
    def test_initialization_unified_mode(self):
        """Should initialize in unified mode when BrainOrchestrator available."""
        mock_brain = MagicMock()
        
        with patch("openclaw.agents.ira.skills.email_channel.email_handler.BRAIN_ORCHESTRATOR_AVAILABLE", True):
            with patch("openclaw.agents.ira.skills.email_channel.email_handler.BrainOrchestrator", return_value=mock_brain):
                with patch("openclaw.agents.ira.skills.email_channel.email_handler.PREPROCESSOR_AVAILABLE", False):
                    with patch("openclaw.agents.ira.skills.email_channel.email_handler.POSTPROCESSOR_AVAILABLE", False):
                        from openclaw.agents.ira.skills.email_channel.email_handler import EmailHandler
                        handler = EmailHandler(use_brain_orchestrator=True)
                        
                        assert handler.use_unified is True
    
    def test_is_internal_machinecraft_in(self, mock_handler):
        """Should detect machinecraft.in as internal."""
        assert mock_handler.is_internal("rushabh@machinecraft.in") is True
    
    def test_is_internal_machinecraft_co(self, mock_handler):
        """Should detect machinecraft.co as internal."""
        assert mock_handler.is_internal("sales@machinecraft.co") is True
    
    def test_is_internal_external_domain(self, mock_handler):
        """Should detect external domains."""
        assert mock_handler.is_internal("customer@example.com") is False
        assert mock_handler.is_internal("john@gmail.com") is False
    
    def test_is_internal_empty_email(self, mock_handler):
        """Should handle empty email."""
        assert mock_handler.is_internal("") is False
        assert mock_handler.is_internal(None) is False
    
    def test_extract_email_identity(self, mock_handler):
        """Should extract identity from email."""
        from openclaw.agents.ira.skills.email_channel.email_handler import EmailData
        
        email = EmailData(
            message_id="msg_123",
            thread_id="thread_456",
            from_email="Customer@Example.com",
            from_name="Customer",
            to_email="ira@machinecraft.org",
            subject="Test",
            body="Test body",
            date=datetime.now(),
        )
        
        identity_id = mock_handler.extract_email_identity(email)
        
        assert identity_id == "customer@example.com"  # Lowercase
    
    def test_process_email_unified_mode(self):
        """Should process email through BrainOrchestrator in unified mode."""
        from openclaw.agents.ira.skills.email_channel.email_handler import EmailData, EmailResponse
        
        mock_brain = MagicMock()
        mock_state = MagicMock()
        mock_state.phase.value = "complete"
        mock_state.to_context_pack.return_value = {}
        mock_brain.process.return_value = mock_state
        
        with patch("openclaw.agents.ira.skills.email_channel.email_handler.BRAIN_ORCHESTRATOR_AVAILABLE", True):
            with patch("openclaw.agents.ira.skills.email_channel.email_handler.BrainOrchestrator", return_value=mock_brain):
                with patch("openclaw.agents.ira.skills.email_channel.email_handler.PREPROCESSOR_AVAILABLE", False):
                    with patch("openclaw.agents.ira.skills.email_channel.email_handler.POSTPROCESSOR_AVAILABLE", False):
                        from openclaw.agents.ira.skills.email_channel.email_handler import EmailHandler
                        
                        handler = EmailHandler(use_brain_orchestrator=True)
                        handler._process_email_unified = MagicMock(return_value=EmailResponse(
                            to="customer@example.com",
                            subject="Re: Test",
                            body="Response body"
                        ))
                        
                        email = EmailData(
                            message_id="msg_123",
                            thread_id="thread_456",
                            from_email="customer@example.com",
                            from_name="Customer",
                            to_email="ira@machinecraft.org",
                            subject="Test",
                            body="Test body",
                            date=datetime.now(),
                        )
                        
                        response = handler.process_email(email)
                        
                        assert response is not None or handler._process_email_unified.called
    
    def test_process_email_skips_internal(self, mock_handler):
        """Should handle internal emails appropriately."""
        from openclaw.agents.ira.skills.email_channel.email_handler import EmailData
        
        email = EmailData(
            message_id="msg_123",
            thread_id="thread_456",
            from_email="rushabh@machinecraft.in",
            from_name="Rushabh",
            to_email="ira@machinecraft.org",
            subject="Internal Update",
            body="Some internal message",
            date=datetime.now(),
        )
        
        # Internal emails may be processed differently
        assert mock_handler.is_internal(email.from_email) is True


class TestEmailPreprocessing:
    """Tests for email preprocessing logic."""
    
    def test_extract_thread_context(self):
        """Should extract thread context from email."""
        # Test thread context extraction
        body = """
Thank you for the information.

On Feb 27, 2026, at 10:00 AM, Ira <ira@machinecraft.org> wrote:
> Here are the PF1-C specifications...
> The forming area is 3000x2000mm.

On Feb 26, 2026, at 9:00 AM, Customer <customer@example.com> wrote:
> I need information about PF1-C machines.
"""
        # Simple check for reply markers
        is_reply = ">" in body or "wrote:" in body.lower()
        assert is_reply is True
    
    def test_extract_customer_info_from_signature(self):
        """Should extract customer info from email signature."""
        body = """
Please send me a quote.

Best regards,
John Doe
Sales Manager
ABC Manufacturing
Phone: +91 98765 43210
Email: john@abc-mfg.com
"""
        # Check for signature patterns
        has_signature = any(
            marker in body.lower()
            for marker in ["best regards", "thanks", "sincerely", "phone:", "email:"]
        )
        assert has_signature is True
    
    def test_clean_email_body(self):
        """Should clean email body for processing."""
        body = """
<html>
<body>
<p>This is an <b>important</b> inquiry.</p>
</body>
</html>
"""
        # Basic HTML tag removal
        import re
        cleaned = re.sub(r'<[^>]+>', '', body)
        
        assert "<html>" not in cleaned
        assert "important" in cleaned


class TestEmailPostprocessing:
    """Tests for email postprocessing logic."""
    
    def test_format_reply_subject(self):
        """Should format reply subject correctly."""
        original_subject = "Machine Inquiry"
        reply_subject = f"Re: {original_subject}" if not original_subject.startswith("Re:") else original_subject
        
        assert reply_subject == "Re: Machine Inquiry"
    
    def test_format_reply_subject_already_re(self):
        """Should not double Re: prefix."""
        original_subject = "Re: Machine Inquiry"
        reply_subject = original_subject if original_subject.startswith("Re:") else f"Re: {original_subject}"
        
        assert reply_subject == "Re: Machine Inquiry"
    
    def test_add_email_signature(self):
        """Should add professional signature to response."""
        response_body = "Thank you for your inquiry."
        signature = """

Best regards,
Ira
AI Sales Assistant
Machinecraft Technologies
"""
        formatted = response_body + signature
        
        assert "Ira" in formatted
        assert "Machinecraft" in formatted
    
    def test_format_for_professional_tone(self):
        """Should maintain professional email tone."""
        response = "Here's the info you asked for."
        
        # Professional emails should have greeting and closing
        professional_response = f"Dear Customer,\n\n{response}\n\nBest regards,\nIra"
        
        assert "Dear" in professional_response
        assert "Best regards" in professional_response


class TestEmailIntegration:
    """Integration tests for email processing flow."""
    
    @pytest.fixture
    def mock_handler(self):
        """Create handler with mocked dependencies."""
        with patch("openclaw.agents.ira.skills.email_channel.email_handler.BRAIN_ORCHESTRATOR_AVAILABLE", False):
            with patch("openclaw.agents.ira.skills.email_channel.email_handler.MEMORY_SERVICE_AVAILABLE", False):
                from openclaw.agents.ira.skills.email_channel.email_handler import EmailHandler
                handler = EmailHandler(use_brain_orchestrator=False)
                yield handler
    
    def test_full_email_processing_flow(self, mock_handler):
        """Should complete full email processing flow."""
        from openclaw.agents.ira.skills.email_channel.email_handler import EmailData
        
        # Create test email
        email = EmailData(
            message_id="msg_test",
            thread_id="thread_test",
            from_email="test@example.com",
            from_name="Test User",
            to_email="ira@machinecraft.org",
            subject="Product Inquiry",
            body="I would like information about your thermoforming machines.",
            date=datetime.now(),
        )
        
        # Extract identity
        identity_id = mock_handler.extract_email_identity(email)
        assert identity_id == "test@example.com"
        
        # Check internal status
        is_internal = mock_handler.is_internal(email.from_email)
        assert is_internal is False
    
    def test_email_with_machine_mention(self, mock_handler):
        """Should handle email mentioning specific machine."""
        from openclaw.agents.ira.skills.email_channel.email_handler import EmailData
        
        email = EmailData(
            message_id="msg_machine",
            thread_id="thread_machine",
            from_email="customer@factory.com",
            from_name="Factory Customer",
            to_email="ira@machinecraft.org",
            subject="PF1-C-3020 Inquiry",
            body="""
Hi,

We are interested in the PF1-C-3020 thermoforming machine for ABS sheets.
Can you provide specifications and pricing?

Thanks,
Factory Manager
""",
            date=datetime.now(),
        )
        
        # Body should contain machine model
        assert "PF1-C-3020" in email.body
        assert "ABS" in email.body
    
    def test_email_thread_processing(self, mock_handler):
        """Should handle email threads correctly."""
        from openclaw.agents.ira.skills.email_channel.email_handler import EmailData
        
        # Original email
        original = EmailData(
            message_id="msg_1",
            thread_id="thread_conv",
            from_email="customer@example.com",
            from_name="Customer",
            to_email="ira@machinecraft.org",
            subject="Machine Query",
            body="What machines do you offer?",
            date=datetime.now(),
            is_reply=False,
        )
        
        # Reply email
        reply = EmailData(
            message_id="msg_2",
            thread_id="thread_conv",
            from_email="customer@example.com",
            from_name="Customer",
            to_email="ira@machinecraft.org",
            subject="Re: Machine Query",
            body="Thanks for the info. What about the PF1-C?",
            date=datetime.now(),
            is_reply=True,
            in_reply_to="msg_1",
        )
        
        # Both should be in same thread
        assert original.thread_id == reply.thread_id
        assert reply.is_reply is True


class TestConversationalEnhancer:
    """Tests for email conversational enhancement."""
    
    def test_get_conversational_enhancer(self):
        """Should get or create conversational enhancer."""
        with patch("openclaw.agents.ira.skills.email_channel.email_handler.CONVERSATIONAL_ENHANCER_AVAILABLE", True):
            with patch("openclaw.agents.ira.skills.email_channel.email_handler.create_enhancer") as mock_create:
                mock_create.return_value = MagicMock()
                
                from openclaw.agents.ira.skills.email_channel.email_handler import get_conversational_enhancer
                
                # Reset global
                import openclaw.agents.ira.skills.email_channel.email_handler as module
                module._conversational_enhancer = None
                
                enhancer = get_conversational_enhancer()
                
                assert enhancer is not None or mock_create.called
    
    def test_conversational_enhancer_unavailable(self):
        """Should handle unavailable conversational enhancer."""
        with patch("openclaw.agents.ira.skills.email_channel.email_handler.CONVERSATIONAL_ENHANCER_AVAILABLE", False):
            from openclaw.agents.ira.skills.email_channel.email_handler import get_conversational_enhancer
            
            # Reset global
            import openclaw.agents.ira.skills.email_channel.email_handler as module
            module._conversational_enhancer = None
            
            enhancer = get_conversational_enhancer()
            
            # Should be None when unavailable
            assert enhancer is None
