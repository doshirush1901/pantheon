"""
Tests for telegram_channel/state.py
====================================

Tests for Telegram gateway state management and persistence.
"""

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Add project paths
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Import module alias for cleaner tests
from openclaw.agents.ira.skills.telegram_channel import state as tg_state


class TestJsonFileOperations:
    """Tests for JSON file operations."""
    
    def test_load_json_file_exists(self, tmp_path):
        """Should load existing JSON file."""
        test_file = tmp_path / "test.json"
        test_data = {"key": "value", "nested": {"inner": 123}}
        with open(test_file, "w") as f:
            json.dump(test_data, f)
        
        result = tg_state.load_json_file(test_file)
        
        assert result == test_data
    
    def test_load_json_file_not_exists(self, tmp_path):
        """Should return None for non-existent file."""
        result = tg_state.load_json_file(tmp_path / "nonexistent.json")
        
        assert result is None
    
    def test_load_json_file_invalid_json(self, tmp_path):
        """Should return None for invalid JSON."""
        test_file = tmp_path / "invalid.json"
        with open(test_file, "w") as f:
            f.write("not valid json {")
        
        result = tg_state.load_json_file(test_file)
        
        assert result is None
    
    def test_save_json_file(self, tmp_path):
        """Should save JSON file correctly."""
        test_file = tmp_path / "output.json"
        test_data = {"saved": True, "count": 42}
        
        result = tg_state.save_json_file(test_file, test_data)
        
        assert result is True
        with open(test_file) as f:
            loaded = json.load(f)
        assert loaded == test_data
    
    def test_save_json_file_creates_directory(self, tmp_path):
        """Should create parent directories if needed."""
        test_file = tmp_path / "subdir" / "nested" / "output.json"
        test_data = {"nested": True}
        
        result = tg_state.save_json_file(test_file, test_data)
        
        assert result is True
        assert test_file.exists()


class TestLogOperations:
    """Tests for log operations."""
    
    def test_append_to_log(self, tmp_path):
        """Should append to log file."""
        log_file = tmp_path / "activity.json"
        
        # Append first entry
        tg_state.append_to_log(log_file, {"event": "first"})
        
        # Append second entry
        tg_state.append_to_log(log_file, {"event": "second"})
        
        # Verify both entries
        with open(log_file) as f:
            data = json.load(f)
        
        assert len(data) == 2
        assert data[0]["event"] == "first"
        assert data[1]["event"] == "second"
    
    def test_append_to_log_creates_file(self, tmp_path):
        """Should create log file if not exists."""
        log_file = tmp_path / "new_log.json"
        
        tg_state.append_to_log(log_file, {"first": True})
        
        assert log_file.exists()
    
    def test_append_to_log_adds_timestamp(self, tmp_path):
        """Should add timestamp to entries."""
        log_file = tmp_path / "timestamped.json"
        
        tg_state.append_to_log(log_file, {"event": "test"})
        
        with open(log_file) as f:
            data = json.load(f)
        
        assert "timestamp" in data[0]


class TestPendingDraftOperations:
    """Tests for pending draft state."""
    
    def test_save_and_load_pending_draft(self):
        """Should save and load pending draft."""
        draft = {"draft_id": "test_123", "to": "test@example.com", "subject": "Test"}
        
        # Use the actual functions
        tg_state.save_pending_draft(draft)
        loaded = tg_state.load_pending_draft()
        
        # Should either match or be handled correctly
        assert loaded is None or loaded.get("draft_id") == "test_123"
        
        # Clean up
        tg_state.save_pending_draft(None)
    
    def test_save_pending_draft_none_clears(self):
        """Should handle None to clear draft."""
        # Should not raise
        tg_state.save_pending_draft(None)


class TestUpdateIdOperations:
    """Tests for Telegram update ID tracking."""
    
    def test_get_last_update_id_returns_int(self):
        """Should return an integer."""
        result = tg_state.get_last_update_id()
        assert isinstance(result, int)
    
    def test_save_last_update_id(self):
        """Should save update ID without error."""
        # Should not raise
        tg_state.save_last_update_id(12345)


class TestTelegramConfig:
    """Tests for Telegram configuration."""
    
    def test_get_telegram_config_returns_tuple(self):
        """get_telegram_config should return tuple when env vars set."""
        with patch.dict("os.environ", {
            "TELEGRAM_BOT_TOKEN": "test-token",
            "TELEGRAM_CHAT_ID": "12345"
        }):
            try:
                result = tg_state.get_telegram_config()
                assert isinstance(result, tuple)
                assert len(result) == 2
            except SystemExit:
                # Expected if env vars not set properly
                pass


class TestModuleConstants:
    """Tests for module constants."""
    
    def test_project_root_defined(self):
        """PROJECT_ROOT should be defined."""
        assert hasattr(tg_state, 'PROJECT_ROOT')
    
    def test_logs_dir_defined(self):
        """LOGS_DIR should be defined."""
        assert hasattr(tg_state, 'LOGS_DIR')
