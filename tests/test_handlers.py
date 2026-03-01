"""
Tests for Telegram Handlers
===========================

Tests for the modular handler modules.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add project paths for imports
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "openclaw" / "agents" / "ira"))
sys.path.insert(0, str(PROJECT_ROOT / "openclaw" / "agents" / "ira" / "skills" / "telegram_channel"))


class TestCommandHandlers:
    """Tests for basic command handlers."""
    
    def test_help_text_constant(self):
        """HELP_TEXT should be defined."""
        # Import using full path to avoid relative import issues
        from openclaw.agents.ira.skills.telegram_channel.handlers.commands import HELP_TEXT
        
        assert HELP_TEXT is not None
        assert len(HELP_TEXT) > 100
        assert "IRA" in HELP_TEXT
    
    def test_welcome_text_constant(self):
        """WELCOME_TEXT should be defined."""
        from openclaw.agents.ira.skills.telegram_channel.handlers.commands import WELCOME_TEXT
        
        assert WELCOME_TEXT is not None
        assert "Welcome" in WELCOME_TEXT
    
    def test_gateway_response_creation(self):
        """GatewayResponse should be creatable."""
        from openclaw.agents.ira.skills.telegram_channel.handlers.commands import GatewayResponse
        
        response = GatewayResponse(text="Test message")
        
        assert response.text == "Test message"
        assert response.success is True
    
    def test_gateway_response_with_failure(self):
        """GatewayResponse should support failure state."""
        from openclaw.agents.ira.skills.telegram_channel.handlers.commands import GatewayResponse
        
        response = GatewayResponse(text="Error", success=False)
        
        assert response.text == "Error"
        assert response.success is False


class TestDecisionParsing:
    """Tests for decision parsing logic."""
    
    def test_single_decision_not_multi(self):
        """Single letter should not be multi-decision."""
        # Test the logic directly
        text = "A"
        lines = [l.strip() for l in text.strip().split('\n') if l.strip()]
        assert len(lines) < 2
    
    def test_multi_line_is_multi(self):
        """Multiple lines should be multi-decision."""
        text = """PF1-C B
ATF A
PF1-X B"""
        lines = [l.strip() for l in text.strip().split('\n') if l.strip()]
        assert len(lines) >= 2


class TestHandlerModulesExist:
    """Tests that handler modules can be imported."""
    
    def test_commands_module_exists(self):
        """commands.py should be importable."""
        from openclaw.agents.ira.skills.telegram_channel.handlers import commands
        assert commands is not None
    
    def test_keyboards_module_exists(self):
        """keyboards.py should be importable."""
        from openclaw.agents.ira.skills.telegram_channel import keyboards
        assert keyboards is not None
    
    def test_state_module_exists(self):
        """state.py should be importable."""
        from openclaw.agents.ira.skills.telegram_channel import state
        assert state is not None


class TestKeyboardBuilders:
    """Tests for keyboard building functions."""
    
    def test_build_main_menu_keyboard(self):
        """build_main_menu_keyboard should return dict."""
        from openclaw.agents.ira.skills.telegram_channel.keyboards import build_main_menu_keyboard
        
        result = build_main_menu_keyboard()
        
        assert isinstance(result, dict)
        assert "inline_keyboard" in result
    
    def test_build_error_keyboard(self):
        """build_error_keyboard should return dict."""
        from openclaw.agents.ira.skills.telegram_channel.keyboards import build_error_keyboard
        
        result = build_error_keyboard()
        
        assert isinstance(result, dict)
        assert "inline_keyboard" in result


class TestStateOperations:
    """Tests for state operations via module."""
    
    def test_load_json_file_function(self, tmp_path):
        """load_json_file should work."""
        import json
        from openclaw.agents.ira.skills.telegram_channel.state import load_json_file
        
        test_file = tmp_path / "test.json"
        with open(test_file, "w") as f:
            json.dump({"test": True}, f)
        
        result = load_json_file(test_file)
        assert result == {"test": True}
    
    def test_save_json_file_function(self, tmp_path):
        """save_json_file should work."""
        import json
        from openclaw.agents.ira.skills.telegram_channel.state import save_json_file
        
        test_file = tmp_path / "output.json"
        
        result = save_json_file(test_file, {"saved": True})
        
        assert result is True
        with open(test_file) as f:
            data = json.load(f)
        assert data == {"saved": True}


class TestHandlerInit:
    """Tests for handler initialization patterns."""
    
    def test_command_handlers_class_exists(self):
        """CommandHandlers class should exist."""
        from openclaw.agents.ira.skills.telegram_channel.handlers.commands import CommandHandlers
        
        assert CommandHandlers is not None
    
    def test_command_handlers_init(self):
        """CommandHandlers should initialize with gateway."""
        from openclaw.agents.ira.skills.telegram_channel.handlers.commands import CommandHandlers
        
        gateway = MagicMock()
        handler = CommandHandlers(gateway)
        
        assert handler.gateway is gateway
    
    def test_handle_help_method(self):
        """handle_help should return GatewayResponse."""
        from openclaw.agents.ira.skills.telegram_channel.handlers.commands import CommandHandlers
        
        gateway = MagicMock()
        handler = CommandHandlers(gateway)
        
        response = handler.handle_help()
        
        assert response is not None
        assert response.success is True
        assert len(response.text) > 50
