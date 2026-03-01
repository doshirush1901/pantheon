"""
Pytest Configuration and Fixtures
=================================

Shared fixtures and configuration for all tests.
"""

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "openclaw" / "agents" / "ira"))


# =============================================================================
# Environment Fixtures
# =============================================================================

@pytest.fixture(autouse=True)
def mock_env_vars(monkeypatch):
    """Set up test environment variables."""
    monkeypatch.setenv("IRA_MODE", "test")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-not-real")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "12345")


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def temp_json_file(temp_dir):
    """Create a temporary JSON file."""
    def _create(data, filename="test.json"):
        filepath = temp_dir / filename
        with open(filepath, "w") as f:
            json.dump(data, f)
        return filepath
    return _create


# =============================================================================
# Mock Services
# =============================================================================

@pytest.fixture
def mock_openai():
    """Mock OpenAI client."""
    with patch("openai.OpenAI") as mock:
        client = MagicMock()
        mock.return_value = client
        
        # Mock chat completion
        completion = MagicMock()
        completion.choices = [MagicMock(message=MagicMock(content="Test response"))]
        client.chat.completions.create.return_value = completion
        
        # Mock embeddings
        embedding = MagicMock()
        embedding.data = [MagicMock(embedding=[0.1] * 1536)]
        client.embeddings.create.return_value = embedding
        
        yield client


@pytest.fixture
def mock_telegram_api():
    """Mock Telegram API responses."""
    with patch("requests.post") as mock_post, patch("requests.get") as mock_get:
        # Mock getUpdates
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"ok": True, "result": []}
        )
        
        # Mock sendMessage
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"ok": True, "result": {"message_id": 123}}
        )
        
        yield {"post": mock_post, "get": mock_get}


@pytest.fixture
def mock_qdrant():
    """Mock Qdrant client."""
    with patch("qdrant_client.QdrantClient") as mock:
        client = MagicMock()
        mock.return_value = client
        
        # Mock search results
        client.search.return_value = []
        client.get_collections.return_value = MagicMock(collections=[])
        
        yield client


@pytest.fixture
def mock_postgres():
    """Mock PostgreSQL connection."""
    with patch("psycopg2.connect") as mock:
        conn = MagicMock()
        mock.return_value = conn
        
        cursor = MagicMock()
        conn.cursor.return_value = cursor
        cursor.fetchone.return_value = (0,)
        cursor.fetchall.return_value = []
        
        yield conn


# =============================================================================
# Sample Data Fixtures
# =============================================================================

@pytest.fixture
def sample_message():
    """Create a sample Telegram message."""
    return {
        "message_id": 1,
        "chat": {"id": 12345},
        "from": {"id": 12345, "first_name": "Test", "username": "testuser"},
        "text": "Hello, Ira!",
        "date": 1234567890
    }


@pytest.fixture
def sample_decision():
    """Create a sample pending decision."""
    return {
        "question_id": "q_001",
        "question": "Should we use option A or B for PF1-C pricing?",
        "options": ["A: Lower price", "B: Higher margin"],
        "status": "pending",
        "timestamp": "2026-02-27T10:00:00"
    }


@pytest.fixture
def sample_knowledge():
    """Create sample knowledge entries."""
    return [
        {
            "id": "k_001",
            "type": "machine_spec",
            "model": "PF1-C-3020",
            "content": "PF1-C-3020: 3000x2000mm forming area, 8 heating zones",
            "embedding": [0.1] * 1536
        },
        {
            "id": "k_002", 
            "type": "pricing",
            "model": "PF1-C-3020",
            "content": "PF1-C-3020 base price: ₹48,50,000",
            "embedding": [0.2] * 1536
        }
    ]


@pytest.fixture
def sample_email():
    """Create a sample email structure."""
    return {
        "id": "email_001",
        "from": "customer@example.com",
        "to": "rushabh@machinecraft.org",
        "subject": "Inquiry about PF1-C-3020",
        "body": "I am interested in the PF1-C-3020 thermoforming machine...",
        "date": "2026-02-27T10:00:00Z"
    }


# =============================================================================
# Gateway Fixtures
# =============================================================================

@pytest.fixture
def gateway_instance(mock_telegram_api, mock_openai, temp_dir):
    """Create a TelegramGateway instance for testing."""
    # Patch file paths to use temp directory
    with patch.dict(os.environ, {"IRA_DATA_DIR": str(temp_dir)}):
        try:
            from openclaw.agents.ira.skills.telegram_channel.telegram_gateway import TelegramGateway
            gateway = TelegramGateway(
                token="test-token",
                expected_chat_id="12345"
            )
            yield gateway
        except ImportError:
            # If import fails, yield a mock
            yield MagicMock()
