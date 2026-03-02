#!/usr/bin/env python3
"""
Telegram Gateway - Primary Interface to OpenClaw Ira

Interactive console mode for Ira via Telegram. Handles:
- Decision replies (A/B/C)
- Draft approval commands (PREVIEW, APPROVE, SEND, CANCEL)
- Control commands (/help, /status, /next, /apply, /brief, /email)
- Free text queries with knowledge retrieval

Usage:
    python telegram_gateway.py --loop --interval 2
    python telegram_gateway.py --once
"""

import argparse
import base64
import json
import logging
import os
import re
import sqlite3
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Set

import requests

# Modular components — stubs for functions that were planned to be extracted
# but modules were never created. Functions defined inline below or as stubs.
# The core state functions (load_json_file, save_json_file, etc.) are defined
# later in this file. Keyboard/handler classes are stubbed here.

def build_decision_keyboard(options=None):
    """Build inline keyboard for decision options."""
    if not options:
        options = ["Approve", "Edit", "Reject"]
    buttons = [[{"text": opt, "callback_data": f"decision_{opt.lower()}"}] for opt in options]
    return {"inline_keyboard": buttons}

def build_draft_keyboard(draft_id="current"):
    """Build inline keyboard for draft actions."""
    return {"inline_keyboard": [
        [{"text": "✅ Approve & Send", "callback_data": f"draft_approve_{draft_id}"},
         {"text": "✏️ Edit", "callback_data": f"draft_edit_{draft_id}"}],
        [{"text": "❌ Reject", "callback_data": f"draft_reject_{draft_id}"}],
    ]}

def build_main_menu_keyboard():
    """Build main menu inline keyboard."""
    return {"inline_keyboard": [
        [{"text": "📊 Status", "callback_data": "menu_status"},
         {"text": "📧 Email", "callback_data": "menu_email"}],
        [{"text": "🔍 Research", "callback_data": "menu_research"},
         {"text": "💡 Help", "callback_data": "menu_help"}],
    ]}

def build_error_keyboard(retry_action="retry"):
    """Build error recovery keyboard."""
    return {"inline_keyboard": [
        [{"text": "🔄 Retry", "callback_data": f"error_{retry_action}"},
         {"text": "💬 Help", "callback_data": "error_help"}],
    ]}

def build_onboarding_keyboard(step="welcome"):
    """Build onboarding step keyboard."""
    if step == "done":
        return {"inline_keyboard": [[{"text": "🚀 Get Started", "callback_data": "onboard_start"}]]}
    return {"inline_keyboard": [[{"text": "Next →", "callback_data": f"onboard_{step}"}]]}

HELP_TEXT = """Available commands:
/help - Show this help
/status - System status
/memory - Memory operations
/research - Research tools
/personality - Personality traits
/boost [trait] - Boost a trait
"""

def _is_multi_decision(text):
    """Check if text contains multiple decision points."""
    return False

class CommandHandlers:
    """Stub — command handling is done inline in TelegramGateway."""
    pass

class DecisionHandlers:
    """Stub — decision handling is done inline in TelegramGateway."""
    pass

class DraftHandlers:
    """Stub — draft handling is done inline in TelegramGateway."""
    pass

class MemoryHandlers:
    """Stub — memory handling is done inline in TelegramGateway."""
    pass

class CRMHandlers:
    """Stub — CRM handling is done inline in TelegramGateway."""
    pass

class ResearchHandlers:
    """Stub — research handling is done inline in TelegramGateway."""
    pass

class StatusHandlers:
    """Stub — status handling is done inline in TelegramGateway."""
    pass

def log_activity(activity_type, data=None):
    """Log activity to activity log file."""
    pass

# =============================================================================
# LOGGING SETUP
# =============================================================================
LOG_DIR = Path(__file__).parent.parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

# Configure logging to both file and console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / "telegram_gateway.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("telegram_gateway")


TELEGRAM_API_BASE = "https://api.telegram.org/bot{token}"

PROJECT_ROOT = Path(__file__).parent.parent.parent
AGENT_DIR = PROJECT_ROOT / "openclaw" / "agents" / "ira"
BRAIN_DIR = AGENT_DIR / "src" / "brain"

# Add project root and agent source directories to path
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(AGENT_DIR))  # For config.py
sys.path.insert(0, str(BRAIN_DIR))
sys.path.insert(0, str(AGENT_DIR / "src" / "core"))
sys.path.insert(0, str(AGENT_DIR / "src" / "memory"))
sys.path.insert(0, str(AGENT_DIR / "src" / "conversation"))
sys.path.insert(0, str(AGENT_DIR / "src" / "identity"))
sys.path.insert(0, str(AGENT_DIR / "src" / "common"))
sys.path.insert(0, str(AGENT_DIR / "core"))

# Import centralized config
try:
    from config import (
        DATABASE_URL, OPENAI_API_KEY, QDRANT_URL,
        RATE_LIMITS, MESSAGE_LIMITS, TIMEOUTS, RETRY_CONFIG
    )
    CONFIG_AVAILABLE = True
except ImportError:
    CONFIG_AVAILABLE = False
    DATABASE_URL = None
    OPENAI_API_KEY = None
    QDRANT_URL = None
    RATE_LIMITS = {"telegram_api_seconds": 1.0}
    MESSAGE_LIMITS = {"telegram_max_age_seconds": 600, "telegram_max_length": 4000}
    TIMEOUTS = {"http_default": 30, "http_short": 10}
    RETRY_CONFIG = {"max_retries": 3}

# Persistent Memory (ChatGPT-style user memory)
try:
    from persistent_memory import get_persistent_memory, PersistentMemory
    PERSISTENT_MEMORY_AVAILABLE = True
except ImportError:
    PERSISTENT_MEMORY_AVAILABLE = False
    logger.warning("Persistent memory not available")

# Memory Trigger - Intelligent memory access control
try:
    from memory_trigger import should_retrieve_memory, get_memory_trigger
    MEMORY_TRIGGER_AVAILABLE = True
except ImportError:
    MEMORY_TRIGGER_AVAILABLE = False
    logger.warning("Memory trigger not available")

# Memory Weaver - How memories influence responses
try:
    from memory_weaver import get_memory_weaver, WovenContext
    MEMORY_WEAVER_AVAILABLE = True
except ImportError:
    MEMORY_WEAVER_AVAILABLE = False
    logger.warning("Memory weaver not available")

# Memory Reasoning - Think with memories before responding
try:
    from memory_reasoning import reason_with_memories, ReasoningTrace
    MEMORY_REASONING_AVAILABLE = True
except ImportError:
    MEMORY_REASONING_AVAILABLE = False
    logger.warning("Memory reasoning not available")

# Episodic Memory - Events with temporal context
try:
    from episodic_memory import get_episodic_memory, EpisodeType, EmotionalValence
    EPISODIC_MEMORY_AVAILABLE = True
except ImportError:
    EPISODIC_MEMORY_AVAILABLE = False
    logger.warning("Episodic memory not available")

# Meta-cognition - Knowing what you know
try:
    from metacognition import assess_knowledge, KnowledgeState
    METACOGNITION_AVAILABLE = True
except ImportError:
    METACOGNITION_AVAILABLE = False
    logger.warning("Meta-cognition not available")

# Brain Orchestrator - Unified cognitive processing pipeline
try:
    from openclaw.agents.ira.src.core.brain_orchestrator import BrainOrchestrator, get_brain
    from openclaw.agents.ira.src.core.brain_state import BrainState, ProcessingPhase
    BRAIN_ORCHESTRATOR_AVAILABLE = True
except ImportError as _bo_err:
    try:
        from brain_orchestrator import BrainOrchestrator, BrainState, get_brain
        BRAIN_ORCHESTRATOR_AVAILABLE = True
    except ImportError:
        BRAIN_ORCHESTRATOR_AVAILABLE = False
        logger.warning(f"Brain orchestrator not available: {_bo_err}")

# Error Monitor - Production error tracking & alerting
try:
    from error_monitor import track_error, track_warning, alert_critical, with_error_tracking
    ERROR_MONITOR_AVAILABLE = True
except ImportError:
    ERROR_MONITOR_AVAILABLE = False
    def track_error(component, error, context=None, severity="error"): pass
    def track_warning(component, message, context=None): pass
    def alert_critical(message, context=None): pass
    def with_error_tracking(component): return lambda f: f
    logger.warning("Error monitor not available")

# Mem0 - Modern AI Memory Layer (replaces PostgreSQL for user memories)
try:
    from mem0_memory import get_mem0_service as _get_mem0_svc, Mem0MemoryService
    MEM0_AVAILABLE = True
except ImportError:
    MEM0_AVAILABLE = False
    logger.warning("Mem0 memory not available")

# Memory Controller - Intelligent memory orchestration (NEW)
try:
    from memory_controller import remember_conversation, get_memory_controller
    MEMORY_CONTROLLER_AVAILABLE = True
except ImportError:
    MEMORY_CONTROLLER_AVAILABLE = False
    logger.warning("Memory controller not available")

# Knowledge Health Monitor - Prevents hallucinations and missing data
try:
    from knowledge_health import get_health_monitor, validate_response as validate_health
    KNOWLEDGE_HEALTH_AVAILABLE = True
except ImportError:
    KNOWLEDGE_HEALTH_AVAILABLE = False
    logger.warning("Knowledge health monitor not available")

_mem0_service_instance = None

def _get_mem0():
    """Get or create Mem0 service instance."""
    global _mem0_service_instance
    if _mem0_service_instance is None and MEM0_AVAILABLE:
        try:
            _mem0_service_instance = _get_mem0_svc()
        except Exception as e:
            logger.error(f"Failed to init Mem0: {e}")
    return _mem0_service_instance

# Replika-inspired Conversational Enhancer
try:
    from replika_integration import ConversationalEnhancer, create_enhancer
    CONVERSATIONAL_ENHANCER_AVAILABLE = True
    _conversational_enhancer = None  # Lazy init
except ImportError:
    CONVERSATIONAL_ENHANCER_AVAILABLE = False
    _conversational_enhancer = None
    logger.warning("Conversational enhancer not available")

# Structured Logging with Request Tracing
try:
    from structured_logger import (
        get_logger, start_trace, end_trace, log_event,
        log_error, traced, PerformanceTimer, log_request
    )
    STRUCTURED_LOGGING_AVAILABLE = True
    _gateway_logger = get_logger("ira.gateway")
except ImportError:
    STRUCTURED_LOGGING_AVAILABLE = False
    _gateway_logger = None
    logger.warning("Structured logging not available")

# Embedding Cache for faster responses
try:
    from embedding_cache import get_cache, cache_openai_embedding
    EMBEDDING_CACHE_AVAILABLE = True
    _embedding_cache = get_cache()
except ImportError:
    EMBEDDING_CACHE_AVAILABLE = False
    _embedding_cache = None
    logger.warning("Embedding cache not available")

# Feedback Learner for continuous improvement
try:
    from feedback_learner import (
        process_correction, enhance_response_with_learning, get_learning_stats
    )
    FEEDBACK_LEARNER_AVAILABLE = True
except ImportError:
    FEEDBACK_LEARNER_AVAILABLE = False
    logger.warning("Feedback learner not available")

# Quality tracking for consolidated knowledge
try:
    from generate_answer import record_feedback_by_ids
    QUALITY_TRACKING_AVAILABLE = True
except ImportError:
    QUALITY_TRACKING_AVAILABLE = False
    logger.debug("Quality tracking not available")
    def record_feedback_by_ids(knowledge_ids, was_helpful): return 0


def get_conversational_enhancer():
    """Get or create the conversational enhancer singleton."""
    global _conversational_enhancer
    if CONVERSATIONAL_ENHANCER_AVAILABLE and _conversational_enhancer is None:
        try:
            _conversational_enhancer = create_enhancer()
            logger.info("Conversational enhancer initialized")
        except Exception as e:
            logger.error(f"Failed to init conversational enhancer: {e}")
    return _conversational_enhancer

LOGS_DIR = PROJECT_ROOT / "crm" / "logs"
KNOWLEDGE_DIR = AGENT_DIR / "knowledge"
KNOWLEDGE_DB = PROJECT_ROOT / "crm" / "knowledge_index.db"

TELEGRAM_ACTIVITY_LOG = LOGS_DIR / "telegram_activity_log.json"
PENDING_DECISIONS_FILE = LOGS_DIR / "pending_decisions.json"
DECISION_LOG_FILE = LOGS_DIR / "decision_log.json"
REVIEW_QUEUE_FILE = LOGS_DIR / "review_queue.json"
SCORE_HISTORY_FILE = LOGS_DIR / "brain_score_history.json"
LAST_UPDATE_FILE = LOGS_DIR / ".telegram_gateway_last_update_id"

PRICEBOOK_FILE = KNOWLEDGE_DIR / "master_pricebook.json"
CATALOG_FILE = KNOWLEDGE_DIR / "master_catalog.json"

# Use centralized config values with fallbacks
MAX_MESSAGE_AGE_SECONDS = MESSAGE_LIMITS.get("telegram_max_age_seconds", 600) if CONFIG_AVAILABLE else 600
RATE_LIMIT_SECONDS = RATE_LIMITS.get("telegram_api_seconds", 1.0) if CONFIG_AVAILABLE else 1.0

# Debug mode - only show debug traces when explicitly enabled
# Set IRA_DEBUG=true to enable debug traces in responses
SHOW_DEBUG = os.environ.get("IRA_DEBUG", "false").lower() == "true"

VALID_DECISION_ANSWERS = {"A", "B", "C"}
SAFE_NUMBERS = {1976, 2019, 47, 100, 1000, 8}

HIGH_COMPLEXITY_KEYWORDS = ["strategy", "pricing", "positioning", "risk", "confidential", "contract", "negotiat"]
MEDIUM_COMPLEXITY_KEYWORDS = ["compare", "summarize", "machines", "specs", "specifications", "quote", "offer"]

MODEL_MAP = {
    "LOW": "gpt-4o-mini",
    "MEDIUM": "gpt-4o",
    "HIGH": "gpt-4o",
}


def load_env_file() -> None:
    """Load environment variables from .env file.
    
    Note: With config.py integration, this is only needed for
    channel-specific variables like TELEGRAM_BOT_TOKEN.
    """
    if CONFIG_AVAILABLE:
        # Core config loaded via config.py, only load telegram-specific vars
        env_file = PROJECT_ROOT / ".env"
        if env_file.exists():
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#') or '=' not in line:
                        continue
                    key, _, value = line.partition('=')
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    # Only load telegram-specific vars not in config.py
                    if key.startswith("TELEGRAM") and key not in os.environ:
                        os.environ[key] = value
        return
    
    # Fallback: load all vars if config.py not available
    env_file = PROJECT_ROOT / ".env"
    if not env_file.exists():
        return
    
    with open(env_file, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            key, _, value = line.partition('=')
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and value and key not in os.environ:
                os.environ[key] = value


load_env_file()


def load_json_file(path: Path) -> Any:
    """Load JSON file, return None on failure."""
    if path.exists():
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return None


def save_json_file(path: Path, data: Any) -> bool:
    """Save data to JSON file."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)
        return True
    except Exception:
        return False


def append_to_log(path: Path, entry: Dict) -> None:
    """Append entry to a JSON log file."""
    log = load_json_file(path) or []
    log.append(entry)
    if len(log) > 500:
        log = log[-500:]
    save_json_file(path, log)


def get_telegram_config() -> Tuple[str, str]:
    """Get Telegram bot token and chat ID from environment."""
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    
    if not bot_token or not chat_id:
        logger.error("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set")
        sys.exit(1)
    
    return bot_token, chat_id


def get_last_update_id() -> int:
    """Get last processed update ID."""
    if LAST_UPDATE_FILE.exists():
        try:
            return int(LAST_UPDATE_FILE.read_text().strip())
        except (ValueError, IOError):
            pass
    return 0


def save_last_update_id(update_id: int) -> None:
    """Save last processed update ID."""
    LAST_UPDATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    LAST_UPDATE_FILE.write_text(str(update_id))


DRAFT_STATE_FILE = LOGS_DIR / ".pending_draft_state.json"


def save_pending_draft(draft_data: Optional[Dict]) -> None:
    """Persist pending draft state to disk.
    
    Saves draft state to file so it survives gateway restarts.
    Call with None to clear pending draft.
    """
    DRAFT_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    if draft_data is None:
        if DRAFT_STATE_FILE.exists():
            DRAFT_STATE_FILE.unlink()
    else:
        draft_data["saved_at"] = datetime.now(timezone.utc).isoformat()
        with open(DRAFT_STATE_FILE, 'w') as f:
            json.dump(draft_data, f, indent=2)


def load_pending_draft() -> Optional[Dict]:
    """Load pending draft state from disk.
    
    Returns None if no draft is pending or draft is stale (>1 hour old).
    """
    if not DRAFT_STATE_FILE.exists():
        return None
    try:
        with open(DRAFT_STATE_FILE) as f:
            draft_data = json.load(f)
        
        saved_at_str = draft_data.get("saved_at")
        if saved_at_str:
            saved_at = datetime.fromisoformat(saved_at_str.replace("Z", "+00:00"))
            age = (datetime.now(timezone.utc) - saved_at).total_seconds()
            if age > 3600:
                DRAFT_STATE_FILE.unlink()
                return None
        
        return draft_data
    except (json.JSONDecodeError, IOError, ValueError):
        return None


@dataclass
class TelegramMessage:
    """Parsed Telegram message."""
    update_id: int
    message_id: int
    chat_id: str
    text: str
    timestamp: datetime
    from_user: str
    from_id: int
    document: Optional[Dict] = None
    photo: Optional[List[Dict]] = None
    caption: Optional[str] = None


@dataclass  
class GatewayResponse:
    """Response to send back to Telegram."""
    text: str
    success: bool = True
    log_entry: Optional[Dict] = None
    reply_markup: Optional[Dict] = None
    parse_mode: Optional[str] = None


class TelegramGateway:
    """Main Telegram gateway for Ira."""
    
    def __init__(self):
        self.bot_token, self.expected_chat_id = get_telegram_config()
        self._openai_client = None
        self._gmail_service = None
        self._last_request_time = 0
    
    def _rate_limit(self):
        """Enforce rate limiting between API calls."""
        elapsed = time.time() - self._last_request_time
        if elapsed < RATE_LIMIT_SECONDS:
            time.sleep(RATE_LIMIT_SECONDS - elapsed)
        self._last_request_time = time.time()
    
    def _api_request(
        self, 
        method: str, 
        endpoint: str, 
        max_retries: int = 3,
        timeout: int = 30,
        **kwargs
    ) -> Optional[Dict]:
        """
        Make a Telegram API request with automatic retry and rate limit handling.
        
        Args:
            method: HTTP method (GET/POST)
            endpoint: API endpoint (e.g., 'sendMessage')
            max_retries: Number of retry attempts
            timeout: Request timeout in seconds
            **kwargs: Additional arguments for requests (json, params, etc.)
            
        Returns:
            Response data dict on success, None on failure
        """
        self._rate_limit()
        url = f"{TELEGRAM_API_BASE.format(token=self.bot_token)}/{endpoint}"
        kwargs.setdefault("timeout", timeout)
        
        last_exception = None
        for attempt in range(max_retries + 1):
            try:
                if method.upper() == "GET":
                    response = requests.get(url, **kwargs)
                else:
                    response = requests.post(url, **kwargs)
                
                # Handle rate limiting (429)
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 5))
                    if attempt < max_retries:
                        logger.warning(f"Rate limited. Waiting {retry_after}s before retry...")
                        time.sleep(retry_after)
                        continue
                    else:
                        logger.error(f"Rate limited after {max_retries} retries")
                        return None
                
                # Handle server errors (5xx)
                if response.status_code >= 500:
                    if attempt < max_retries:
                        delay = 2 ** attempt
                        logger.warning(f"Server error {response.status_code}. Retrying in {delay}s...")
                        time.sleep(delay)
                        continue
                    else:
                        logger.error(f"Server error after {max_retries} retries")
                        return None
                
                data = response.json()
                if data.get("ok"):
                    return data
                else:
                    error_desc = data.get("description", "Unknown error")
                    logger.error(f"API error: {error_desc}")
                    return None
                    
            except requests.exceptions.Timeout as e:
                last_exception = e
                if attempt < max_retries:
                    delay = 2 ** attempt
                    logger.warning(f"Request timeout. Retrying in {delay}s...")
                    time.sleep(delay)
                else:
                    logger.error(f"Request timeout after {max_retries} retries")
                    
            except requests.exceptions.ConnectionError as e:
                last_exception = e
                if attempt < max_retries:
                    delay = 2 ** attempt
                    logger.warning(f"Connection error. Retrying in {delay}s...")
                    time.sleep(delay)
                else:
                    logger.error(f"Connection error after {max_retries} retries: {e}")
                    
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                return None
        
        return None
    
    def _get_openai_client(self):
        """Get or create OpenAI client."""
        if self._openai_client is None:
            try:
                from openai import OpenAI
                api_key = OPENAI_API_KEY or os.environ.get("OPENAI_API_KEY")
                if not api_key:
                    raise ValueError("OPENAI_API_KEY not set")
                self._openai_client = OpenAI(api_key=api_key)
            except ImportError:
                raise ImportError("openai package not installed")
        return self._openai_client
    
    def _update_brain_query_timestamp(self):
        """Update agent state with last brain query timestamp."""
        try:
            state_file = AGENT_DIR / "workspace" / "state.json"
            if state_file.exists():
                with open(state_file) as f:
                    state = json.load(f)
            else:
                state = {}
            
            state['brain_last_query'] = datetime.now().isoformat()
            
            state_file.parent.mkdir(parents=True, exist_ok=True)
            with open(state_file, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to update brain query timestamp: {e}")
    
    def _get_gmail_service(self):
        """Get or create Gmail service."""
        if self._gmail_service is None:
            try:
                from oauth_setup import get_gmail_service
                self._gmail_service = get_gmail_service()
            except Exception as e:
                raise RuntimeError(f"Gmail service unavailable: {e}")
        return self._gmail_service
    
    def send_message(self, text: str, parse_mode: Optional[str] = None, reply_markup: Optional[Dict] = None) -> Optional[int]:
        """Send message to Telegram chat with retry logic. Returns message_id on success."""
        if len(text) > 4000:
            text = text[:3950] + "\n\n... [truncated]"
        
        payload = {
            "chat_id": self.expected_chat_id,
            "text": text,
        }
        
        if parse_mode:
            payload["parse_mode"] = parse_mode
        
        if reply_markup:
            payload["reply_markup"] = reply_markup
        
        data = self._api_request("POST", "sendMessage", json=payload)
        if data:
            return data.get("result", {}).get("message_id")
        return None
    
    def send_typing_action(self) -> bool:
        """Show typing indicator to user with retry logic."""
        payload = {
            "chat_id": self.expected_chat_id,
            "action": "typing"
        }
        data = self._api_request("POST", "sendChatAction", max_retries=2, timeout=10, json=payload)
        return data is not None

    def edit_message(self, message_id: int, text: str, parse_mode: Optional[str] = None, reply_markup: Optional[Dict] = None) -> bool:
        """Edit an existing message with retry logic."""
        if len(text) > 4000:
            text = text[:3950] + "\n\n... [truncated]"

        payload = {
            "chat_id": self.expected_chat_id,
            "message_id": message_id,
            "text": text,
        }

        if parse_mode:
            payload["parse_mode"] = parse_mode

        if reply_markup:
            payload["reply_markup"] = reply_markup

        data = self._api_request("POST", "editMessageText", json=payload)
        return data is not None
    
    def answer_callback_query(self, callback_query_id: str, text: Optional[str] = None, show_alert: bool = False) -> bool:
        """Answer a callback query (required after button press) with retry logic."""
        payload = {"callback_query_id": callback_query_id}
        if text:
            payload["text"] = text
            payload["show_alert"] = show_alert
        data = self._api_request("POST", "answerCallbackQuery", max_retries=2, timeout=10, json=payload)
        return data is not None
    
    # =========================================================================
    # FILE DOWNLOAD & DOCUMENT INGEST
    # =========================================================================

    TELEGRAM_DOCS_DIR = PROJECT_ROOT / "data" / "imports" / "docs_from_telegram"
    SUPPORTED_DOC_EXTENSIONS = {
        ".pdf", ".xlsx", ".xls", ".docx", ".doc", ".csv", ".txt",
        ".json", ".md", ".pptx", ".ppt", ".png", ".jpg", ".jpeg",
        ".gif", ".webp", ".bmp", ".tiff",
    }
    IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".tiff"}

    def _download_telegram_file(self, file_id: str, dest_path: Path) -> bool:
        """Download a file from Telegram servers using getFile API."""
        file_info = self._api_request("GET", "getFile", params={"file_id": file_id})
        if not file_info:
            return False

        file_path = file_info.get("result", {}).get("file_path")
        if not file_path:
            return False

        download_url = f"https://api.telegram.org/file/bot{self.bot_token}/{file_path}"
        try:
            resp = requests.get(download_url, timeout=120, stream=True)
            resp.raise_for_status()
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            with open(dest_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
            logger.info(f"[DOWNLOAD] Saved {dest_path.name} ({dest_path.stat().st_size} bytes)")
            return True
        except Exception as e:
            logger.error(f"[DOWNLOAD] Failed to download file: {e}")
            return False

    def _extract_text_from_image(self, image_path: Path) -> Optional[str]:
        """Use GPT-4o vision to extract text/content from an image or screenshot."""
        try:
            import openai
            api_key = os.environ.get("OPENAI_API_KEY", "")
            if not api_key:
                try:
                    from config import OPENAI_API_KEY
                    api_key = OPENAI_API_KEY
                except ImportError:
                    pass
            if not api_key:
                logger.warning("[OCR] No OpenAI API key for image extraction")
                return None

            client = openai.OpenAI(api_key=api_key)
            with open(image_path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode("utf-8")

            ext = image_path.suffix.lower().lstrip(".")
            mime_map = {"jpg": "jpeg", "tiff": "tiff", "bmp": "bmp"}
            mime_type = f"image/{mime_map.get(ext, ext)}"

            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "Extract ALL text and information from this image. "
                                "If it's a screenshot of a document, email, chat, spreadsheet, or note, "
                                "transcribe the full content preserving structure. "
                                "If it's a diagram or chart, describe it in detail with all labels and values. "
                                "If it contains tables, format them clearly. "
                                "Return the extracted content as plain text."
                            ),
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:{mime_type};base64,{image_data}"},
                        },
                    ],
                }],
                max_tokens=4096,
            )
            extracted = response.choices[0].message.content
            logger.info(f"[OCR] Extracted {len(extracted)} chars from {image_path.name}")
            return extracted
        except Exception as e:
            logger.error(f"[OCR] Image extraction failed: {e}")
            return None

    def handle_document_upload(self, message: TelegramMessage) -> GatewayResponse:
        """Handle a document or photo uploaded via Telegram — download, save, and ingest."""
        self.TELEGRAM_DOCS_DIR.mkdir(parents=True, exist_ok=True)

        file_id = None
        original_name = None
        is_photo = False

        if message.document:
            file_id = message.document.get("file_id")
            original_name = message.document.get("file_name", "unnamed_document")
            file_size = message.document.get("file_size", 0)
            if file_size > 20 * 1024 * 1024:
                return GatewayResponse(
                    text="❌ File too large. Telegram bots can download files up to 20MB.",
                    success=False,
                )
        elif message.photo:
            best_photo = max(message.photo, key=lambda p: p.get("file_size", 0))
            file_id = best_photo.get("file_id")
            original_name = f"photo_{message.message_id}.jpg"
            is_photo = True

        if not file_id:
            return GatewayResponse(text="❌ Could not identify the uploaded file.", success=False)

        ext = Path(original_name).suffix.lower()
        if not ext:
            mime = (message.document or {}).get("mime_type", "")
            ext_map = {
                "application/pdf": ".pdf",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
                "application/vnd.ms-excel": ".xls",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
                "application/msword": ".doc",
                "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
                "text/plain": ".txt",
                "text/csv": ".csv",
                "text/markdown": ".md",
                "application/json": ".json",
                "image/png": ".png",
                "image/jpeg": ".jpg",
            }
            ext = ext_map.get(mime, ".bin")

        if ext not in self.SUPPORTED_DOC_EXTENSIONS:
            supported = ", ".join(sorted(self.SUPPORTED_DOC_EXTENSIONS))
            return GatewayResponse(
                text=f"❌ Unsupported file type: `{ext}`\n\nSupported: {supported}",
                success=False,
            )

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = re.sub(r'[^\w\-.]', '_', Path(original_name).stem)
        dest_filename = f"{timestamp}_{safe_name}{ext}"
        dest_path = self.TELEGRAM_DOCS_DIR / dest_filename

        if not self._download_telegram_file(file_id, dest_path):
            return GatewayResponse(text="❌ Failed to download file from Telegram.", success=False)

        # Check for duplicate: if an older copy with the same original name exists
        # and has identical content, remove the old one (keep the new timestamped version).
        import hashlib as _hl
        new_hash = _hl.sha256(dest_path.read_bytes()).hexdigest()
        for existing in self.TELEGRAM_DOCS_DIR.iterdir():
            if existing == dest_path or not existing.is_file():
                continue
            if existing.name.endswith(".extracted.txt") or existing.name == ".gitkeep":
                continue
            if existing.stat().st_size == dest_path.stat().st_size:
                if _hl.sha256(existing.read_bytes()).hexdigest() == new_hash:
                    logger.info(f"[DEDUP] Removing older duplicate: {existing.name}")
                    existing.unlink()
                    txt_companion = existing.with_suffix(".extracted.txt")
                    if txt_companion.exists():
                        txt_companion.unlink()

        is_image = ext in self.IMAGE_EXTENSIONS or is_photo
        extracted_text = None
        text_file_path = None

        if is_image:
            extracted_text = self._extract_text_from_image(dest_path)
            if extracted_text:
                text_file_path = dest_path.with_suffix(".extracted.txt")
                text_file_path.write_text(extracted_text, encoding="utf-8")

        ingest_result = self._ingest_uploaded_document(
            dest_path, original_name, message.caption, extracted_text, is_image
        )

        size_kb = dest_path.stat().st_size / 1024
        response_parts = [
            f"📄 **Document received: {original_name}**",
            f"📁 Saved to: `docs_from_telegram/{dest_filename}`",
            f"📏 Size: {size_kb:.1f} KB",
        ]

        if is_image and extracted_text:
            preview = extracted_text[:200] + "..." if len(extracted_text) > 200 else extracted_text
            response_parts.append(f"\n🔍 **Extracted text preview:**\n{preview}")

        if ingest_result:
            response_parts.append(f"\n{ingest_result}")

        if message.caption:
            response_parts.append(f"\n📝 Caption: _{message.caption}_")

        return GatewayResponse(
            text="\n".join(response_parts),
            log_entry={
                "type": "document_uploaded",
                "file_name": original_name,
                "saved_as": dest_filename,
                "size_bytes": dest_path.stat().st_size,
                "is_image": is_image,
                "had_extracted_text": bool(extracted_text),
                "ingested": bool(ingest_result),
            },
        )

    @staticmethod
    def _detect_knowledge_type(filename: str, caption: Optional[str]) -> str:
        """Infer the best knowledge_type from filename + caption for Mem0 routing."""
        text = f"{filename} {caption or ''}".lower()
        if any(w in text for w in ("quote", "quotation", "pricing", "price", "offer", "cost", "eur", "usd", "inr", "lakh")):
            return "pricing"
        if any(w in text for w in ("customer", "client", "company", "factory", "plant", "purchased", "order")):
            return "customer"
        if any(w in text for w in ("spec", "technical", "datasheet", "drawing", "dimension", "heater", "servo")):
            return "machine_spec"
        if any(w in text for w in ("process", "forming", "thermoform", "vacuum", "pressure")):
            return "process"
        if any(w in text for w in ("application", "automotive", "packaging", "aerospace", "medical")):
            return "application"
        return "general"

    @staticmethod
    def _extract_entities_from_caption(caption: Optional[str], filename: str) -> List[str]:
        """Extract machine models, company names, and key entities from caption + filename."""
        if not caption and not filename:
            return []
        text = f"{filename} {caption or ''}"
        entities = []

        # Machine models: PF1-X-1210, AM-1200, IMG-3020, FCS-*, ATF-*
        models = re.findall(
            r'(PF[12][-\s]?[A-Z]?[-\s]?\d[\d\-]*|AM[-\s]?\d[\w\-]*|IMG[-\s]?\d[\w\-]*|'
            r'FCS[-\s]?\w+|ATF[-\s]?\w+|UNO[-\s]?\w+|DUO[-\s]?\w+)',
            text, re.IGNORECASE,
        )
        entities.extend(m.upper().replace(" ", "-") for m in models)

        # Trade shows / events: K2025, K-2025, Plastindia, etc.
        events = re.findall(r'\b(K[-\s]?\d{4}|Plastindia\s*\d*|Chinaplas\s*\d*|NPE\s*\d*)\b', text, re.IGNORECASE)
        entities.extend(e.strip() for e in events)

        # Capitalized multi-word names (likely company names), excluding common words
        skip = {"This", "The", "For", "From", "With", "Please", "Quote", "EUR", "USD", "INR",
                "PDF", "Doc", "File", "Data", "Ingest", "Machine", "Model", "Series"}
        cap_phrases = re.findall(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b', text)
        entities.extend(p for p in cap_phrases if p.split()[0] not in skip)

        return list(dict.fromkeys(entities))

    def _ingest_uploaded_document(
        self,
        file_path: Path,
        original_name: str,
        caption: Optional[str],
        extracted_text: Optional[str],
        is_image: bool,
    ) -> Optional[str]:
        """Run the ingestion pipeline on an uploaded document. Returns status string."""
        results = []
        saved_filename = file_path.name
        knowledge_type = self._detect_knowledge_type(original_name, caption)
        entities = self._extract_entities_from_caption(caption, original_name)
        primary_entity = entities[0] if entities else ""

        # --- File Manifest: store the human-written description for NN research ---
        if caption:
            try:
                sys.path.insert(0, str(BRAIN_DIR))
                from nn_research import get_file_manifest
                manifest = get_file_manifest()
                manifest.add_file(
                    filename=saved_filename,
                    description=caption,
                    original_name=original_name,
                    file_path=str(file_path),
                )
                logger.info(f"[MANIFEST] Stored description for {saved_filename}: {caption[:80]}")
            except Exception as e:
                logger.warning(f"[MANIFEST] Could not store file description: {e}")

        # --- Path 1: KnowledgeIngestor (Qdrant + Mem0 + JSON) for text documents ---
        if not is_image or extracted_text:
            try:
                sys.path.insert(0, str(BRAIN_DIR))
                from knowledge_ingestor import KnowledgeIngestor, KnowledgeItem

                ingestor = KnowledgeIngestor()
                items_to_ingest = []

                if is_image and extracted_text:
                    items_to_ingest.append(KnowledgeItem(
                        text=extracted_text,
                        knowledge_type=knowledge_type,
                        source_file=original_name,
                        entity=primary_entity,
                        summary=caption or f"Extracted from image: {original_name}",
                        metadata={
                            "source": "telegram_upload",
                            "original_name": original_name,
                            "is_image": True,
                            "caption": caption,
                            "entities": entities,
                        },
                    ))
                else:
                    from document_extractor import DocumentExtractor
                    extractor = DocumentExtractor()
                    extraction = extractor.extract(str(file_path))

                    if not extraction.success:
                        results.append(f"⚠️ Text extraction failed: {extraction.error or 'unknown'}")
                    else:
                        text_content = extraction.text
                        if caption:
                            text_content = f"[Context: {caption}]\n\n{text_content}"

                        items_to_ingest.append(KnowledgeItem(
                            text=text_content,
                            knowledge_type=knowledge_type,
                            source_file=original_name,
                            entity=primary_entity,
                            summary=caption or f"Uploaded via Telegram: {original_name}",
                            metadata={
                                "source": "telegram_upload",
                                "original_name": original_name,
                                "pages": extraction.page_count,
                                "extractor": extraction.extractor_used,
                                "caption": caption,
                                "entities": entities,
                            },
                        ))

                # Store the caption itself as a standalone knowledge item so Ira
                # can retrieve it by semantic search independently of the document.
                if caption and len(caption) > 10:
                    items_to_ingest.append(KnowledgeItem(
                        text=(
                            f"File upload note for '{original_name}' "
                            f"(saved as {saved_filename}):\n{caption}"
                        ),
                        knowledge_type=knowledge_type,
                        source_file=original_name,
                        entity=primary_entity,
                        summary=f"Upload context: {caption}",
                        metadata={
                            "source": "telegram_upload_note",
                            "original_name": original_name,
                            "saved_filename": saved_filename,
                            "is_file_description": True,
                            "entities": entities,
                        },
                    ))

                ki_result = None
                if items_to_ingest:
                    ki_result = ingestor.ingest_batch(items_to_ingest)

                if ki_result and ki_result.success:
                    stores = []
                    if ki_result.qdrant_main or ki_result.qdrant_discovered:
                        stores.append("Qdrant")
                    if ki_result.mem0:
                        stores.append("Mem0")
                    if ki_result.json_backup:
                        stores.append("JSON")
                    if ki_result.neo4j:
                        stores.append("Neo4j")
                    store_str = ", ".join(stores) if stores else "stored"
                    skipped = f" ({ki_result.items_skipped} duplicates skipped)" if ki_result.items_skipped else ""
                    results.append(
                        f"✅ **Knowledge ingested:** {ki_result.items_ingested} items → {store_str}{skipped}"
                    )

                    # Create rich Neo4j relationships between extracted entities
                    if len(entities) > 1 and ki_result.neo4j:
                        try:
                            from neo4j_store import get_neo4j_store
                            neo4j = get_neo4j_store()
                            if neo4j.is_connected():
                                rel_map = {
                                    "pricing": "QUOTED_FOR",
                                    "customer": "CUSTOMER_OF",
                                    "machine_spec": "SPEC_FOR",
                                }
                                rel_type = rel_map.get(knowledge_type, "RELATED_TO")
                                for i, e1 in enumerate(entities[:8]):
                                    for e2 in entities[i+1:8]:
                                        neo4j.create_relationship(e1, e2, rel_type, strength=0.8)
                                results.append(f"🔗 **Graph:** {len(entities)} entities linked")
                        except Exception as e:
                            logger.debug(f"[NEO4J] Extra relationship creation: {e}")

                elif ki_result:
                    errors = ", ".join(ki_result.errors[:2]) if ki_result.errors else "unknown"
                    results.append(f"⚠️ Knowledge ingestion partial: {errors}")
            except ImportError as e:
                logger.warning(f"[INGEST] KnowledgeIngestor not available: {e}")
            except Exception as e:
                logger.error(f"[INGEST] Knowledge ingestion error: {e}")
                results.append(f"⚠️ Knowledge ingestion error: {str(e)[:80]}")

        # --- Path 2: DocumentIngestor (fact extraction → Mem0/PostgreSQL) ---
        if not is_image:
            try:
                sys.path.insert(0, str(AGENT_DIR / "src" / "memory"))
                from document_ingestor import DocumentIngestor

                fact_ingestor = DocumentIngestor(check_conflicts=True)
                fact_result = fact_ingestor.ingest(str(file_path), context=caption)

                if fact_result.facts_extracted > 0:
                    results.append(
                        f"🧠 **Facts extracted:** {fact_result.facts_extracted} facts, "
                        f"{fact_result.memories_stored} stored"
                    )
                    if fact_result.conflicts_found > 0:
                        results.append(
                            f"⚠️ {fact_result.conflicts_found} conflicts detected — use `/conflicts` to review"
                        )
            except ImportError as e:
                logger.warning(f"[INGEST] DocumentIngestor not available: {e}")
            except Exception as e:
                logger.error(f"[INGEST] Fact extraction error: {e}")

        if caption:
            results.append(f"📋 **Upload note stored** for NN research & retrieval (type: {knowledge_type})")

        return "\n".join(results) if results else "📥 File saved (ingestion modules not available)"

    def handle_docs_command(self) -> GatewayResponse:
        """Handle /docs - List documents uploaded via Telegram."""
        docs_dir = self.TELEGRAM_DOCS_DIR
        if not docs_dir.exists():
            return GatewayResponse(text="📂 No documents uploaded yet.\n\nSend me a file to get started!")

        files = sorted(docs_dir.iterdir(), key=lambda f: f.stat().st_mtime, reverse=True)
        files = [f for f in files if f.is_file() and not f.name.endswith(".extracted.txt")]

        if not files:
            return GatewayResponse(text="📂 No documents uploaded yet.\n\nSend me a file to get started!")

        total_size = sum(f.stat().st_size for f in files)
        total_mb = total_size / (1024 * 1024)

        lines = [f"📂 **Uploaded Documents** ({len(files)} files, {total_mb:.1f} MB total)\n"]

        for f in files[:20]:
            size_kb = f.stat().st_size / 1024
            mtime = datetime.fromtimestamp(f.stat().st_mtime).strftime("%b %d %H:%M")
            ext = f.suffix.lower()
            icon = "🖼️" if ext in self.IMAGE_EXTENSIONS else "📄"
            display_name = "_".join(f.stem.split("_")[2:]) + f.suffix if f.stem.count("_") >= 2 else f.name
            lines.append(f"{icon} `{display_name}` — {size_kb:.0f}KB — {mtime}")

        if len(files) > 20:
            lines.append(f"\n... and {len(files) - 20} more")

        lines.append(f"\n📁 Path: `data/imports/docs_from_telegram/`")
        return GatewayResponse(text="\n".join(lines))

    def handle_deep_ingest(self, args: str) -> GatewayResponse:
        """Handle /deep_ingest [filename] — Re-process an uploaded doc with deep research.

        Runs the deep research engine against the document to extract structured
        knowledge, then stores findings in Qdrant + Mem0.
        Without args, processes the most recently uploaded file.
        """
        docs_dir = self.TELEGRAM_DOCS_DIR
        if not docs_dir.exists():
            return GatewayResponse(text="📂 No uploaded documents to process.", success=False)

        files = sorted(
            [f for f in docs_dir.iterdir()
             if f.is_file() and not f.name.endswith(".extracted.txt") and f.name != ".gitkeep"],
            key=lambda f: f.stat().st_mtime, reverse=True,
        )
        if not files:
            return GatewayResponse(text="📂 No uploaded documents to process.", success=False)

        target = None
        if args.strip():
            query = args.strip().lower()
            for f in files:
                if query in f.name.lower() or query in f.stem.lower():
                    target = f
                    break
            if not target:
                return GatewayResponse(
                    text=f"❌ No uploaded file matching `{args.strip()}`.\nUse `/docs` to see available files.",
                    success=False,
                )
        else:
            target = files[0]

        self.send_typing_action()

        try:
            sys.path.insert(0, str(BRAIN_DIR))
            from document_extractor import DocumentExtractor
            from knowledge_ingestor import KnowledgeIngestor, KnowledgeItem

            extractor = DocumentExtractor()
            extraction = extractor.extract(str(target))
            if not extraction.success:
                return GatewayResponse(
                    text=f"❌ Could not extract text from `{target.name}`: {extraction.error}",
                    success=False,
                )

            # Get manifest description if available
            manifest_desc = ""
            try:
                from nn_research import get_file_manifest
                manifest_desc = get_file_manifest().get_all_descriptions(target.name)
            except Exception:
                pass

            # Use LLM to do a deep structured extraction
            import openai
            api_key = os.environ.get("OPENAI_API_KEY", "")
            if not api_key:
                try:
                    from config import OPENAI_API_KEY
                    api_key = OPENAI_API_KEY
                except ImportError:
                    pass

            client = openai.OpenAI(api_key=api_key)
            doc_text = extraction.text[:80000]

            context_line = f"\nUploader notes: {manifest_desc}" if manifest_desc else ""
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": (
                        "You are a knowledge extraction expert for Machinecraft Technologies, "
                        "a vacuum forming machine manufacturer. Extract ALL important knowledge "
                        "from this document into structured sections. Be thorough and precise."
                    )},
                    {"role": "user", "content": (
                        f"Document: {target.name}{context_line}\n\n"
                        f"Content:\n{doc_text}\n\n"
                        "Extract knowledge in these sections:\n"
                        "1. KEY FACTS — Specific data points (specs, prices, dates, quantities)\n"
                        "2. ENTITIES — Companies, people, machines mentioned with context\n"
                        "3. RELATIONSHIPS — Who bought what, who works with whom, deal status\n"
                        "4. TECHNICAL DETAILS — Specs, configurations, options\n"
                        "5. BUSINESS INTELLIGENCE — Pricing patterns, market signals, competitive info\n\n"
                        "For each item, write a clear standalone sentence that Ira can remember."
                    )},
                ],
                max_tokens=4096,
                temperature=0.2,
            )
            deep_knowledge = response.choices[0].message.content

            knowledge_type = self._detect_knowledge_type(target.name, manifest_desc)
            ingestor = KnowledgeIngestor()
            item = KnowledgeItem(
                text=deep_knowledge,
                knowledge_type=knowledge_type,
                source_file=target.name,
                summary=f"Deep extraction from {target.name}",
                entity=manifest_desc[:100] if manifest_desc else "",
                metadata={
                    "source": "deep_ingest",
                    "original_file": target.name,
                    "extraction_model": "gpt-4o",
                    "pages": extraction.page_count,
                },
            )
            result = ingestor.ingest_batch([item])

            preview = deep_knowledge[:500] + "..." if len(deep_knowledge) > 500 else deep_knowledge
            status = "✅" if result.success else "⚠️"
            return GatewayResponse(
                text=(
                    f"🔬 **Deep Ingest: {target.name}**\n\n"
                    f"{status} Ingested {result.items_ingested} items "
                    f"(type: {knowledge_type})\n\n"
                    f"**Extracted knowledge preview:**\n{preview}"
                ),
                log_entry={
                    "type": "deep_ingest",
                    "file": target.name,
                    "knowledge_type": knowledge_type,
                    "items": result.items_ingested,
                    "success": result.success,
                },
            )
        except Exception as e:
            logger.error(f"[DEEP_INGEST] Error: {e}")
            return GatewayResponse(text=f"❌ Deep ingest failed: {str(e)[:200]}", success=False)

    def set_my_commands(self) -> bool:
        """Configure bot menu commands."""
        url = f"{TELEGRAM_API_BASE.format(token=self.bot_token)}/setMyCommands"
        commands = [
            {"command": "start", "description": "Welcome & quick tour"},
            {"command": "menu", "description": "Main menu with quick actions"},
            {"command": "status", "description": "Brain score & system status"},
            {"command": "brief", "description": "Generate topic briefing"},
            {"command": "dashboard", "description": "Relationship overview"},
            {"command": "research", "description": "Deep research on a topic"},
            {"command": "docs", "description": "List uploaded documents"},
            {"command": "help", "description": "Show all commands"},
        ]
        try:
            response = requests.post(url, json={"commands": commands}, timeout=10)
            return response.json().get("ok", False)
        except Exception as e:
            logger.error(f"Error setting commands: {e}")
            return False
    
    # =========================================================================
    # INLINE KEYBOARD BUILDERS
    # =========================================================================
    
    def _build_decision_keyboard(self, options: List[str] = None) -> Dict:
        """Build inline keyboard for A/B/C decision replies."""
        return build_decision_keyboard(options)
    
    def _build_draft_keyboard(self, draft_id: str = "current") -> Dict:
        """Build inline keyboard for draft approval flow."""
        return build_draft_keyboard(draft_id)
    
    def _build_main_menu_keyboard(self) -> Dict:
        """Build main menu inline keyboard."""
        return build_main_menu_keyboard()
    
    def _build_error_keyboard(self, retry_action: str = "retry") -> Dict:
        """Build error recovery keyboard."""
        return build_error_keyboard(retry_action)
    
    def _make_error_response(self, error: Exception, context: str = "operation", include_keyboard: bool = True) -> GatewayResponse:
        """Create a user-friendly error response with recovery options."""
        error_type = type(error).__name__
        error_msg = str(error)[:100]
        
        # Categorize error and suggest action
        if "rate limit" in error_msg.lower() or "429" in error_msg:
            suggestion = "Wait 30 seconds and try again"
        elif "timeout" in error_msg.lower():
            suggestion = "The operation took too long. Try a simpler query"
        elif "not found" in error_msg.lower() or "404" in error_msg:
            suggestion = "The resource wasn't found. Check your input"
        elif "unauthorized" in error_msg.lower() or "401" in error_msg:
            suggestion = "Authentication issue. API keys may need refresh"
        else:
            suggestion = "Try again or rephrase your request"
        
        text = f"⚠️ *{context.title()} failed*\n\n"
        text += f"What happened: {error_type}\n"
        text += f"Details: {error_msg}\n\n"
        text += f"💡 {suggestion}"
        
        return GatewayResponse(
            text=text,
            success=False,
            parse_mode="Markdown",
            reply_markup=self._build_error_keyboard() if include_keyboard else None
        )
    
    def _build_onboarding_keyboard(self, step: str = "welcome") -> Dict:
        """Build onboarding flow keyboards."""
        return build_onboarding_keyboard(step)
    
    def fetch_updates(self) -> List[TelegramMessage]:
        """Fetch new messages and callback queries from Telegram with retry logic."""
        last_update_id = get_last_update_id()
        offset = last_update_id + 1 if last_update_id > 0 else 0
        
        params = {"timeout": 10}
        if offset > 0:
            params["offset"] = offset
        
        data = self._api_request("GET", "getUpdates", max_retries=3, timeout=30, params=params)
        
        if not data:
            return []
        
        messages = []
        now = datetime.now(timezone.utc)
        
        for update in data.get("result", []):
            # Handle callback queries (button presses)
            callback = update.get("callback_query")
            if callback:
                callback_chat_id = str(callback.get("message", {}).get("chat", {}).get("id", ""))
                if callback_chat_id == self.expected_chat_id:
                    self._handle_callback_query(callback)
                save_last_update_id(update["update_id"])
                continue
            
            msg = update.get("message", {})
            if not msg:
                continue

            has_text = bool(msg.get("text"))
            has_document = bool(msg.get("document"))
            has_photo = bool(msg.get("photo"))

            if not has_text and not has_document and not has_photo:
                save_last_update_id(update["update_id"])
                continue
            
            chat_id = str(msg.get("chat", {}).get("id", ""))
            if chat_id != self.expected_chat_id:
                continue
            
            msg_timestamp = datetime.fromtimestamp(
                msg.get("date", 0), tz=timezone.utc
            )
            age_seconds = (now - msg_timestamp).total_seconds()
            
            if age_seconds > MAX_MESSAGE_AGE_SECONDS:
                continue
            
            from_user = msg.get("from", {})
            
            text = msg.get("text", "").strip()
            caption = msg.get("caption", "").strip() or None

            if not text and caption:
                text = caption

            if not text:
                text = ""

            messages.append(TelegramMessage(
                update_id=update["update_id"],
                message_id=msg["message_id"],
                chat_id=chat_id,
                text=text,
                timestamp=msg_timestamp,
                from_user=from_user.get("username", from_user.get("first_name", "unknown")),
                from_id=from_user.get("id", 0),
                document=msg.get("document"),
                photo=msg.get("photo"),
                caption=caption,
            ))
        
        if messages:
            max_update_id = max(m.update_id for m in messages)
            save_last_update_id(max_update_id)
        elif data.get("result"):
            max_update_id = max(u["update_id"] for u in data["result"])
            save_last_update_id(max_update_id)
        
        return messages
    
    # =========================================================================
    # CALLBACK QUERY HANDLER (Button Presses)
    # =========================================================================
    
    def _handle_callback_query(self, callback: Dict) -> None:
        """Handle inline keyboard button presses."""
        callback_id = callback.get("id")
        data = callback.get("data", "")
        message = callback.get("message", {})
        message_id = message.get("message_id")
        from_user = callback.get("from", {})
        
        logger.info(f"[CALLBACK] data={data} from={from_user.get('username', 'unknown')}")
        
        # Always acknowledge the callback first
        self.answer_callback_query(callback_id)
        
        # Show typing for any action that takes time
        self.send_typing_action()
        
        try:
            # Decision callbacks (A/B/C)
            if data.startswith("decision_"):
                answer = data.replace("decision_", "").upper()
                response = self.handle_decision_reply(answer)
                if message_id:
                    self.edit_message(message_id, response.text)
                else:
                    self.send_message(response.text)
            
            # Draft approval callbacks
            elif data.startswith("draft_"):
                action = data.split("_")[1]  # preview, edit, approve, send, cancel
                draft_id = "_".join(data.split("_")[2:]) if len(data.split("_")) > 2 else "current"
                self._handle_draft_callback(action, draft_id, message_id)
            
            # Main menu callbacks
            elif data.startswith("menu_"):
                command = data.replace("menu_", "")
                self._handle_menu_callback(command, message_id)
            
            # Onboarding callbacks
            elif data.startswith("onboard_"):
                step = data.replace("onboard_", "")
                self._handle_onboard_callback(step, message_id)
            
            # Error recovery callbacks
            elif data.startswith("error_"):
                action = data.replace("error_", "")
                self._handle_error_callback(action, message_id)
            
            else:
                self.send_message(f"Unknown action: {data}")
        
        except Exception as e:
            logger.error(f"[CALLBACK] Error handling {data}: {e}")
            self.send_message(f"⚠️ Error processing action: {str(e)[:100]}")
    
    def _handle_draft_callback(self, action: str, draft_id: str, message_id: Optional[int]) -> None:
        """Handle draft approval button presses."""
        if action == "preview":
            response = self.handle_draft_command("PREVIEW")
        elif action == "edit":
            self.send_message("✏️ Reply with your edits or type CANCEL to abort.")
            return
        elif action == "approve":
            response = self.handle_draft_command("APPROVE")
        elif action == "send":
            response = self.handle_draft_command("SEND")
        elif action == "cancel":
            response = self.handle_draft_command("CANCEL")
        else:
            self.send_message(f"Unknown draft action: {action}")
            return
        
        if message_id and action in ["approve", "send", "cancel"]:
            # Update the original message to show result
            self.edit_message(message_id, response.text)
        else:
            self.send_message(response.text)
    
    def _handle_menu_callback(self, command: str, message_id: Optional[int]) -> None:
        """Handle main menu button presses."""
        command_map = {
            "status": "/status",
            "brief": "/brief",
            "research": "/research",
            "dashboard": "/dashboard",
            "priorities": "/priorities",
            "at_risk": "/at_risk",
            "help": "/help",
        }
        
        if command == "research":
            self.send_message("🔍 What would you like to research?\n\nJust type your question or use:\n`/research <topic>`")
            return
        elif command == "brief":
            self.send_message("📧 What topic for the briefing?\n\nJust type or use:\n`/brief <topic>`")
            return
        
        text_command = command_map.get(command, f"/{command}")
        # Process as a regular text command
        response = self.handle_text(text_command)
        self.send_message(response.text)
    
    def _handle_onboard_callback(self, step: str, message_id: Optional[int]) -> None:
        """Handle onboarding flow button presses."""
        if step == "tour":
            tour_text = """🚀 *Quick Tour of Ira*

I'm your AI assistant for MachineCraft. Here's what I can do:

*📊 Knowledge & Research*
• Answer questions about products, specs, pricing
• Research companies and contacts
• Search emails and documents

*📧 Communication*
• Draft and send emails
• Track conversation history
• Follow up on leads

*👥 Relationships*
• Monitor contact health
• Alert you to at-risk relationships
• Prioritize who needs attention

*Ready to explore?*"""
            keyboard = self._build_onboarding_keyboard("done")
            if message_id:
                self.edit_message(message_id, tour_text, parse_mode="Markdown", reply_markup=keyboard)
            else:
                self.send_message(tour_text, parse_mode="Markdown", reply_markup=keyboard)
        
        elif step == "skip":
            done_text = "✅ Setup complete! Just ask me anything or tap a button below."
            keyboard = self._build_onboarding_keyboard("done")
            if message_id:
                self.edit_message(message_id, done_text, reply_markup=keyboard)
            else:
                self.send_message(done_text, reply_markup=keyboard)
        
        elif step.startswith("role_"):
            role = step.replace("role_", "")
            self.send_message(f"✅ Got it, you're in {role}. I'll tailor my responses accordingly.\n\nReady to go! Ask me anything or use /menu.")
    
    def _handle_error_callback(self, action: str, message_id: Optional[int]) -> None:
        """Handle error recovery button presses."""
        if action == "retry":
            self.send_message("🔄 Please resend your last message to retry.")
        elif action == "details":
            self.send_message("📋 Check logs/telegram_gateway.log for detailed error information.")
        elif action == "dismiss":
            if message_id:
                self.edit_message(message_id, "❌ Dismissed")
            else:
                self.send_message("❌ Dismissed")
    
    def handle_decision_reply(self, answer: str) -> GatewayResponse:
        """Handle A/B/C decision reply."""
        pending = load_json_file(PENDING_DECISIONS_FILE) or []
        
        pending_items = [d for d in pending if d.get("status") == "pending"]
        pending_items.sort(key=lambda d: d.get("timestamp", ""), reverse=True)
        
        if not pending_items:
            return GatewayResponse(
                text=f"Received '{answer}' but no pending decisions.",
                success=False
            )
        
        decision = pending_items[0]
        question_id = decision.get("question_id")
        
        for d in pending:
            if d.get("question_id") == question_id:
                d["status"] = "resolved"
                d["answer"] = answer.upper()
                d["answered_at"] = datetime.now().isoformat()
                break
        
        save_json_file(PENDING_DECISIONS_FILE, pending)
        
        decision_log = load_json_file(DECISION_LOG_FILE) or []
        resolved_entry = {
            "question_id": question_id,
            "answer": answer.upper(),
            "status": "resolved",
            "answered_at": datetime.now().isoformat(),
            "question": decision.get("question", "")[:100]
        }
        decision_log.append(resolved_entry)
        save_json_file(DECISION_LOG_FILE, decision_log)
        
        return GatewayResponse(
            text=f"✓ Decision recorded: {answer}\nQuestion: {decision.get('question', '')[:80]}...",
            log_entry={
                "type": "decision",
                "question_id": question_id,
                "answer": answer
            }
        )
    
    def handle_multi_decision_reply(self, text: str) -> GatewayResponse:
        """
        Handle multi-line decision replies.
        
        Supports formats like:
        "PF1-C B
         ATF A
         PF1-X B"
        
        Maps each line to pending decisions by model name or decision_id.
        If ambiguous, asks clarifying question.
        """
        try:
            # Use session manager for parsing
            from telegram_session import get_session_manager
            sm = get_session_manager()
            parse_result = sm.parse_multi_decision(text)
        except ImportError:
            # Fallback to inline parsing
            parse_result = self._parse_multi_decision_inline(text)
        
        if not parse_result.is_valid:
            # No decisions could be parsed - check if ambiguous
            if parse_result.ambiguous:
                return self._format_ambiguous_decision_response(
                    parse_result.ambiguous, text
                )
            return GatewayResponse(
                text="❌ Could not parse any decisions from your reply.\n\n"
                     "**Expected format:**\n"
                     "```\n"
                     "PF1-C B\n"
                     "ATF A\n"
                     "```\n"
                     "Or simply: `A`, `B`, or `C` for a single pending decision.",
                success=False
            )
        
        # Process each parsed decision
        pending = load_json_file(PENDING_DECISIONS_FILE) or []
        decision_log = load_json_file(DECISION_LOG_FILE) or []
        resolved = []
        
        for question_id, answer in parse_result.decisions:
            # Find and update the pending decision
            for d in pending:
                if d.get("question_id") == question_id and d.get("status") == "pending":
                    d["status"] = "resolved"
                    d["answer"] = answer.upper()
                    d["answered_at"] = datetime.now().isoformat()
                    
                    # Add to log
                    decision_log.append({
                        "question_id": question_id,
                        "answer": answer.upper(),
                        "status": "resolved",
                        "answered_at": datetime.now().isoformat(),
                        "question": d.get("question", "")[:100]
                    })
                    
                    # Track for response
                    model = self._extract_model_from_question(d.get("question", ""))
                    resolved.append(f"• {model or question_id}: **{answer}**")
                    break
        
        save_json_file(PENDING_DECISIONS_FILE, pending)
        save_json_file(DECISION_LOG_FILE, decision_log)
        
        # Build response
        lines = [f"✓ **{len(resolved)} decision(s) recorded:**"]
        lines.extend(resolved)
        
        # Note any ambiguous items
        if parse_result.ambiguous:
            lines.append("")
            lines.append(f"⚠️ Could not match: {', '.join(parse_result.ambiguous)}")
            lines.append("Use `/status` to see remaining pending decisions.")
        
        # Check remaining pending
        remaining = [d for d in pending if d.get("status") == "pending"]
        if remaining:
            lines.append("")
            lines.append(f"📋 {len(remaining)} decision(s) still pending.")
        
        return GatewayResponse(
            text="\n".join(lines),
            log_entry={
                "type": "multi_decision",
                "resolved_count": len(resolved),
                "ambiguous_count": len(parse_result.ambiguous)
            }
        )
    
    def _parse_multi_decision_inline(self, text: str):
        """Inline fallback for multi-decision parsing."""
        from dataclasses import dataclass
        from typing import List, Tuple
        
        @dataclass
        class ParseResult:
            decisions: List[Tuple[str, str]]
            ambiguous: List[str]
            parsed_count: int
            is_valid: bool
        
        decisions = []
        ambiguous = []
        
        pending = load_json_file(PENDING_DECISIONS_FILE) or []
        pending_by_model = {}
        
        for d in pending:
            if d.get("status") == "pending":
                model = self._extract_model_from_question(d.get("question", ""))
                if model:
                    pending_by_model[model.upper()] = d.get("question_id")
        
        lines = text.strip().split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Parse "MODEL ANSWER" format
            match = re.match(r'^([A-Za-z0-9\-_]+)\s+([ABC])$', line, re.IGNORECASE)
            if match:
                label = match.group(1).upper()
                answer = match.group(2).upper()
                
                # Try exact match
                if label in pending_by_model:
                    decisions.append((pending_by_model[label], answer))
                else:
                    # Try partial match
                    matched = False
                    for model_key, q_id in pending_by_model.items():
                        if label in model_key or model_key in label:
                            decisions.append((q_id, answer))
                            matched = True
                            break
                    if not matched:
                        ambiguous.append(label)
        
        return ParseResult(
            decisions=decisions,
            ambiguous=ambiguous,
            parsed_count=len(decisions),
            is_valid=len(decisions) > 0
        )
    
    def _extract_model_from_question(self, question: str) -> str:
        """Extract model name from decision question."""
        match = re.search(
            r'\b(PF1[-\s]?[A-Z]?[-\s]?\d*|ATF[-\s]?\d*|PF1X[-\s]?\d*|IMG[-\s]?\d*|TOM[-\s]?\d*)\b',
            question, re.IGNORECASE
        )
        if match:
            return match.group(1).upper().replace(' ', '-').replace('--', '-')
        return ""
    
    def _format_ambiguous_decision_response(self, ambiguous: List[str], original_text: str) -> GatewayResponse:
        """Format a helpful response when decisions couldn't be matched."""
        pending = load_json_file(PENDING_DECISIONS_FILE) or []
        pending_items = [d for d in pending if d.get("status") == "pending"]
        
        lines = ["Let me help clarify. I received: " + ", ".join(ambiguous) + "\n"]
        
        if pending_items:
            lines.append("**Current pending decisions:**")
            for i, d in enumerate(pending_items[:5], 1):
                q_id = d.get("question_id", "?")
                question = d.get("question", "")[:60]
                model = self._extract_model_from_question(d.get("question", ""))
                
                if model:
                    lines.append(f"{i}. **{model}** (`{q_id}`)")
                else:
                    lines.append(f"{i}. `{q_id}`")
                lines.append(f"   {question}...")
            
            lines.append("")
            lines.append("**Reply format:**")
            lines.append("```")
            for d in pending_items[:3]:
                model = self._extract_model_from_question(d.get("question", ""))
                if model:
                    lines.append(f"{model} A")
            lines.append("```")
        else:
            lines.append("No pending decisions found.")
        
        return GatewayResponse(
            text="\n".join(lines),
            success=False,
            log_entry={"type": "ambiguous_decision", "unmatched": ambiguous}
        )
    
    def is_multi_decision_reply(self, text: str) -> bool:
        """Check if text looks like a multi-decision reply."""
        lines = text.strip().split('\n')
        
        # Must have at least one line with MODEL + A/B/C pattern
        pattern = re.compile(r'^[A-Za-z0-9\-_]+\s+[ABC]$', re.IGNORECASE)
        
        matching_lines = sum(1 for line in lines if pattern.match(line.strip()))
        return matching_lines >= 1
    
    def handle_preview_draft(self, draft_id: str) -> GatewayResponse:
        """Fetch and display Gmail draft."""
        try:
            service = self._get_gmail_service()
            draft = service.users().drafts().get(userId='me', id=draft_id).execute()
            
            message = draft.get("message", {})
            payload = message.get("payload", {})
            headers = payload.get("headers", [])
            
            subject = ""
            to = ""
            for header in headers:
                name = header.get("name", "").lower()
                if name == "subject":
                    subject = header.get("value", "")
                elif name == "to":
                    to = header.get("value", "")
            
            body = ""
            if payload.get("body", {}).get("data"):
                body = base64.urlsafe_b64decode(payload["body"]["data"]).decode('utf-8', errors='ignore')
            elif payload.get("parts"):
                for part in payload["parts"]:
                    if part.get("mimeType") == "text/plain" and part.get("body", {}).get("data"):
                        body = base64.urlsafe_b64decode(part["body"]["data"]).decode('utf-8', errors='ignore')
                        break
            
            preview = f"📄 DRAFT PREVIEW\n\n"
            preview += f"To: {to}\n"
            preview += f"Subject: {subject}\n"
            preview += f"─" * 30 + "\n\n"
            preview += body[:2000]
            if len(body) > 2000:
                preview += "\n\n... [truncated]"
            
            # Build action keyboard
            keyboard = {
                "inline_keyboard": [
                    [
                        {"text": "✅ Approve", "callback_data": f"draft_approve_{draft_id}"},
                        {"text": "📤 Send Now", "callback_data": f"draft_send_{draft_id}"}
                    ],
                    [{"text": "❌ Cancel", "callback_data": f"draft_cancel_{draft_id}"}]
                ]
            }
            
            return GatewayResponse(
                text=preview,
                log_entry={"type": "preview", "draft_id": draft_id},
                reply_markup=keyboard
            )
            
        except Exception as e:
            return self._make_error_response(e, "Draft preview")
    
    def handle_approve_draft(self, draft_id: str) -> GatewayResponse:
        """Approve draft and request SEND confirmation."""
        try:
            service = self._get_gmail_service()
            draft = service.users().drafts().get(userId='me', id=draft_id).execute()
            
            message = draft.get("message", {})
            payload = message.get("payload", {})
            headers = payload.get("headers", [])
            
            subject = ""
            to = ""
            for header in headers:
                name = header.get("name", "").lower()
                if name == "subject":
                    subject = header.get("value", "")
                elif name == "to":
                    to = header.get("value", "")
            
            body = ""
            if payload.get("body", {}).get("data"):
                body = base64.urlsafe_b64decode(payload["body"]["data"]).decode('utf-8', errors='ignore')
            elif payload.get("parts"):
                for part in payload["parts"]:
                    if part.get("mimeType") == "text/plain" and part.get("body", {}).get("data"):
                        body = base64.urlsafe_b64decode(part["body"]["data"]).decode('utf-8', errors='ignore')
                        break
            
            save_pending_draft({
                "draft_id": draft_id,
                "to": to,
                "subject": subject,
            })
            
            preview = f"📬 DRAFT APPROVED\n\n"
            preview += f"To: {to}\n"
            preview += f"Subject: {subject}\n"
            preview += f"─" * 30 + "\n\n"
            preview += body[:1500]
            if len(body) > 1500:
                preview += "\n\n... [truncated]"
            preview += f"\n\n⚠️ Choose an action below:"
            
            # Build send/cancel keyboard
            keyboard = {
                "inline_keyboard": [
                    [
                        {"text": "📤 Send Now", "callback_data": f"draft_send_{draft_id}"},
                        {"text": "❌ Cancel", "callback_data": f"draft_cancel_{draft_id}"}
                    ]
                ]
            }
            
            return GatewayResponse(
                text=preview,
                log_entry={"type": "approve", "draft_id": draft_id},
                reply_markup=keyboard
            )
            
        except Exception as e:
            return self._make_error_response(e, "Draft approval")
    
    def handle_send_draft(self) -> GatewayResponse:
        """Send the last approved draft (loaded from persistent storage)."""
        pending_draft = load_pending_draft()
        if not pending_draft:
            return GatewayResponse(
                text="❌ No approved draft pending. Use APPROVE <draft_id> first.",
                success=False
            )

        draft_id = pending_draft["draft_id"]

        try:
            service = self._get_gmail_service()
            result = service.users().drafts().send(userId='me', body={"id": draft_id}).execute()

            message_id = result.get("id", "unknown")
            to = pending_draft.get("to", "unknown")
            subject = pending_draft.get("subject", "unknown")

            save_pending_draft(None)

            return GatewayResponse(
                text=f"✅ EMAIL SENT\n\nTo: {to}\nSubject: {subject}\nMessage ID: {message_id}",
                log_entry={"type": "send", "draft_id": draft_id, "message_id": message_id}
            )

        except Exception as e:
            save_pending_draft(None)
            return self._make_error_response(e, "Email sending")
    
    def handle_cancel(self) -> GatewayResponse:
        """Cancel pending draft (loaded from persistent storage)."""
        pending_draft = load_pending_draft()
        if pending_draft:
            draft_id = pending_draft["draft_id"]
            save_pending_draft(None)
            return GatewayResponse(
                text=f"🚫 Cancelled draft {draft_id}",
                log_entry={"type": "cancel", "draft_id": draft_id}
            )
        else:
            return GatewayResponse(
                text="Nothing to cancel.",
                success=False
            )
    
    def handle_start(self) -> GatewayResponse:
        """Handle /start command - welcome and onboarding."""
        welcome_text = """👋 *Welcome to Ira!*

I'm your AI assistant for MachineCraft.

I can help you:
• Answer questions about products, specs & pricing
• Research companies and contacts
• Draft and send emails
• Track relationships and priorities

Let's get started!"""
        
        keyboard = self._build_onboarding_keyboard("welcome")
        self.send_message(welcome_text, parse_mode="Markdown", reply_markup=keyboard)
        return GatewayResponse(text="", success=True)
    
    def handle_menu(self) -> GatewayResponse:
        """Handle /menu command - show main menu with buttons."""
        menu_text = """📋 *Main Menu*

Tap a button below or just ask me anything in plain English."""
        
        keyboard = self._build_main_menu_keyboard()
        self.send_message(menu_text, parse_mode="Markdown", reply_markup=keyboard)
        return GatewayResponse(text="", success=True)
    
    def handle_help(self) -> GatewayResponse:
        """Show help message."""
        help_text = """🤖 **IRA - Your AI Sales Assistant**

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💬 **Just chat naturally!** Ask about machines, customers, pricing, or anything Machinecraft-related.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 **DECISION REPLIES**
  A, B, C → Resolve pending decision
  
  **Multi-line decisions:**
  ```
  PF1-C B
  ATF A
  PF1X B
  ```

DRAFT COMMANDS:
  PREVIEW <id> → View draft
  APPROVE <id> → Approve draft for sending
  SEND → Confirm and send approved draft
  CANCEL → Cancel pending draft

CAMPAIGN BATCH COMMANDS:
  PREVIEW BATCH <id> → Preview batch drafts
  APPROVE BATCH <id> → Approve batch
  SEND BATCH <id> → Send all batch drafts

CONTROL COMMANDS:
  /help → Show this message
  /status → Brain score, docs, chunks, conflicts
  /diag → Retrieval diagnostics (engine, doc_types)
  /next [N] → Send next N conflicts for review
  /apply → Apply resolved decisions
  /brief <topic> → Generate topic briefing
  /email summary → Preview brain summary email

QUOTE GENERATION:
  /quote <size> [variant] → Quick quote generation
    Examples:
      /quote 2000x1500 → PF1-C for 2000×1500mm
      /quote 2000x1500 servo → PF1-X servo variant
      /quote 3x2 m → 3000×2000mm (auto-converts)

FAILURE TRACKING:
  /fail last → Show last failure
  /fail stats → Show failure statistics
  /fail list [N] → List last N failures
  /fixplan last → Show fix plan for last failure

TAKEOUT EMAIL STATS:
  /takeout status → Basic email stats
  /takeout stats → Detailed stats with domains/events
  /takeout domains → Top 10 email domains
  /takeout events → Event type breakdown
  /takeout runs → Recent ingestion runs

RELATIONSHIP DASHBOARD:
  /dashboard → Overview of all relationship health
  /priorities → Top contacts needing attention
  /at_risk → Declining relationships
  /contact <name> → Detail about a specific contact

QUICK COMMANDS (with confirmation):
  restart → Restart agent
  pause → Pause campaign
  resume → Resume campaign

TEACH IRA (Natural Language):
  /teach <facts> → Teach Ira new facts in plain English
  Example: /teach FRIMO is no longer our active agent in Europe
  Example: /teach Dezet ordered PF1-X-1310 in 2025, Netherlands

BRAIN TRAINING MODE (Duolingo-style):
  /train start → Start continuous quiz (never-ending)
  /train next → Skip to next question
  /train answer A/B/C/D → Answer (or type naturally!)
  /train answer none → Flag that Ira doesn't know this
  /train score → Score breakdown by category
  /train reset → Clear all training history
  Wrong answers train Ira. "none" triggers NN research.

NN RESEARCH & METADATA:
  /confirm <id> → Confirm research result, learn it
  /reject <id> → Wrong answer, search next files
  /index → Show metadata index status
  /index build → Build/update LLM metadata for all import files

DEEP RESEARCH (Manus-Style):
  /research <query> → Full research mode (shows work)
  /think <query> → Force deep thinking
  /thinking → Show active research jobs
  /cancel_thinking → Cancel running analysis

  Research mode shows you:
  • What tools are being used
  • What's being found
  • How confidence builds
  
  Auto-triggered for complex questions.
  Add "quick" or "fast" to skip deep research.

EMAIL GENERATION (Manus-Style):
  /email <recipient> [company] [name] [purpose]
  
  Examples:
  /email john@bmw.de BMW John follow_up
  /email sales@toyota.com Toyota "" cold_outreach
  /email contact@supplier.com
  
  Purposes: follow_up, cold_outreach, quote_response,
            meeting_request, thank_you, introduction
  
  Shows research + drafting + self-critique process.

MEMORY (ChatGPT-Style):
  /memories → See what I remember about you
  "remember that..." → Explicitly tell me to remember something
  "forget #N" → Delete a specific memory
  "what do you know about me?" → Same as /memories
  
  I automatically learn from our conversations and use
  memories to personalize responses across all chats.

MEMORY ANALYTICS:
  /search_memory <topic> → Search what I know about a topic
  /memory_stats → Memory analytics dashboard
  /learn <fact> → Explicitly teach me something
  /export_memory → Backup all knowledge to file
  /decay_memory → Clean up old unused memories

DOCUMENT INGESTION:
  📎 Upload any file → Auto-download, save & train Ira
  /ingest <path> → Scan local document and store in memory
  /docs → List all uploaded documents
  Supports: PDF, XLSX, XLS, DOCX, DOC, PPTX, CSV, TXT, MD, JSON
  Images: PNG, JPG, GIF, WEBP (OCR via GPT-4o Vision)

CONFLICT RESOLUTION:
  /conflicts → Show pending memory conflicts
  /resolve <id> <1|2|merge:text> → Resolve a conflict
  Reply "1" → Keep existing fact
  Reply "2" → Use new fact
  Reply "merge: <text>" → Use custom merged version

PRICE CONFLICTS:
  /price_conflicts → Show pending price discrepancies
  /resolve_price <model> <price> → Set correct price
  Or reply: "PF1-C-3020: 85 lakh" (natural language)

RESPONSE FEEDBACK:
  /good → Rate last response as good (helps Ira learn)
  /bad [reason] → Rate last response as bad with optional reason
  /feedback → Show feedback summary
  /knowledge_quality → Show quality report for learned knowledge

PROACTIVE OUTREACH:
  /outreach → View queued outreach candidates
  /approve <name> [message] → Send outreach to contact
  /dismiss <name> → Remove from queue without sending
  /outreach_stats → View outreach statistics

PERSONALITY:
  /personality → View Ira's evolved personality traits
  /boost <trait> → Increase a trait (warmth, charm, humor, etc.)

FREE TEXT:
  Any other message is treated as a query.
  Ira will retrieve relevant knowledge and respond.
  Complex questions auto-trigger deep thinking.

CONVERSATIONAL FEATURES:
  • Short answers to Ira's questions (yes/no/A/B/C)
  • Multi-decision replies on multiple lines
  • Context-aware follow-up responses

SAFETY:
  - No auto-send for external emails
  - Only approved prices are shared
  - Max 20 emails/day, 5/hour"""
        
        return GatewayResponse(text=help_text)
    
    def handle_status(self) -> GatewayResponse:
        """Show Ira status including brain health."""
        lines = ["📊 IRA STATUS\n"]
        
        # Load agent state for brain health
        state_file = AGENT_DIR / "workspace" / "state.json"
        agent_state = load_json_file(state_file) or {}
        
        # Brain Health Section
        brain_status = agent_state.get('brain_status', 'unknown')
        brain_engine = agent_state.get('brain_engine', 'unknown')
        brain_message = agent_state.get('brain_message', '')
        brain_last_query = agent_state.get('brain_last_query')
        degraded_mode = agent_state.get('degraded_mode', False)
        
        # Status emoji mapping
        status_emoji = {
            'ok': '✅',
            'partial': '⚠️',
            'degraded': '❌',
            'unknown': '❓'
        }
        emoji = status_emoji.get(brain_status, '❓')
        
        lines.append(f"🧠 BRAIN RETRIEVAL")
        lines.append(f"   Status: {emoji} {brain_status.upper()}")
        lines.append(f"   Engine: {brain_engine}")
        if brain_message:
            lines.append(f"   Info: {brain_message[:60]}")
        if brain_last_query:
            lines.append(f"   Last Query: {brain_last_query[:19]}")
        if degraded_mode:
            lines.append(f"   ⚠️ DEGRADED MODE - QA may be limited")
        
        # Brain Score Section
        score_history = load_json_file(SCORE_HISTORY_FILE) or []
        if score_history:
            latest = score_history[-1]
            lines.append(f"\n📈 Brain Score: {latest.get('total', 0):.1f}/100")
            lines.append(f"   Coverage: {latest.get('coverage', 0):.1f}")
            lines.append(f"   Consistency: {latest.get('consistency', 0):.1f}")
            lines.append(f"   Confidence: {latest.get('confidence', 0):.1f}")
        else:
            lines.append("\n📈 Brain Score: Not computed")
        
        # Knowledge DB Section - PostgreSQL primary, SQLite fallback
        try:
            import psycopg2
            db_url = DATABASE_URL or os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL")
            if db_url:
                conn = psycopg2.connect(db_url)
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM ira_knowledge.documents WHERE status='active'")
                docs = cursor.fetchone()[0]
                cursor.execute("SELECT COUNT(*) FROM ira_knowledge.chunks")
                chunks = cursor.fetchone()[0]
                conn.close()
                lines.append(f"\n📚 Documents: {docs}")
                lines.append(f"📄 Chunks: {chunks}")
            else:
                raise Exception("No PostgreSQL URL configured")
        except Exception as pg_err:
            # SQLite fallback (deprecated)
            if KNOWLEDGE_DB.exists():
                try:
                    conn = sqlite3.connect(str(KNOWLEDGE_DB))
                    docs = conn.execute("SELECT COUNT(*) FROM documents WHERE status='active'").fetchone()[0]
                    chunks = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
                    conn.close()
                    lines.append(f"\n📚 Documents: {docs} (SQLite)")
                    lines.append(f"📄 Chunks: {chunks}")
                except Exception:
                    lines.append("\n📚 Knowledge DB: Error reading")
            else:
                lines.append("\n📚 Knowledge DB: Not found")
        
        # Conflicts and Decisions
        review_queue = load_json_file(REVIEW_QUEUE_FILE) or []
        pending_conflicts = len([r for r in review_queue if r.get("status") == "pending"])
        lines.append(f"\n⚠️ Pending conflicts: {pending_conflicts}")
        
        pending_decisions = load_json_file(PENDING_DECISIONS_FILE) or []
        awaiting = len([d for d in pending_decisions if d.get("status") == "pending"])
        lines.append(f"❓ Awaiting answers: {awaiting}")
        
        # Memory Stats
        if PERSISTENT_MEMORY_AVAILABLE:
            try:
                pm = get_persistent_memory()
                stats = pm.get_stats()
                user_mem = stats.get("user_memories", {})
                entity_mem = stats.get("entity_memories", {})
                
                lines.append(f"\n🧠 PERSISTENT MEMORY")
                lines.append(f"   User memories: {user_mem.get('total', 0)}")
                lines.append(f"   Users tracked: {user_mem.get('users_with_memories', 0)}")
                lines.append(f"   Entity memories: {entity_mem.get('total', 0)}")

                # Type breakdown
                by_type = user_mem.get('by_type', {})
                if by_type:
                    type_str = ", ".join([f"{t}:{c}" for t, c in by_type.items()])
                    lines.append(f"   Types: {type_str}")
                
                # Memory Trigger stats
                if MEMORY_TRIGGER_AVAILABLE:
                    trigger = get_memory_trigger()
                    tracked_users = len(trigger._message_count)
                    total_msgs = sum(trigger._message_count.values())
                    lines.append(f"   ⚡ Trigger: {tracked_users} users, {total_msgs} msgs evaluated")
            except Exception as e:
                lines.append(f"\n🧠 Memory: Error ({e})")
        
        # Agent uptime
        started_at = agent_state.get('started_at')
        if started_at:
            lines.append(f"\n🕐 Agent started: {started_at[:19]}")
        
        return GatewayResponse(text="\n".join(lines))
    
    def handle_diag(self) -> GatewayResponse:
        """Show retrieval diagnostics including IRA_MODE."""
        lines = ["🔍 IRA DIAGNOSTICS\n"]
        
        # IRA_MODE and stable config
        try:
            ira_mode = os.environ.get("IRA_MODE", "stable").upper()
            lines.append(f"**Mode:** `{ira_mode}`")
            
            from stable_config import get_config, is_stable_mode
            config = get_config()
            lines.append(f"  Qdrant only: {config.use_qdrant_only}")
            lines.append(f"  Truth-first: {config.use_truth_first}")
            lines.append(f"  Legacy fallback: {not config.disable_legacy_fallback}")
            lines.append("")
        except ImportError:
            lines.append(f"**Mode:** `{os.environ.get('IRA_MODE', 'unknown')}`")
            lines.append("")
        
        # Truth Core stats
        try:
            from truth_core import get_truth_core
            truth = get_truth_core()
            stats = truth.get_stats()
            lines.append("**Truth Core**")
            lines.append(f"  Models: {stats['total_models']}")
            lines.append(f"  Aliases: {stats['total_aliases']}")
            lines.append("")
        except ImportError:
            pass
        except Exception as e:
            lines.append(f"  ⚠️ Truth Core: {e}")
            lines.append("")
        
        try:
            sys.path.insert(0, str(BRAIN_DIR))
            from retrieval_diagnostics import get_diagnostics
            
            diag = get_diagnostics()
            stats = diag.get_stats()
            
            # Session stats
            session = stats.get("session", {})
            lines.append("**Session Stats**")
            lines.append(f"  Total queries: {session.get('total_queries', 0)}")
            qdrant_ratio = stats.get('qdrant_usage_ratio', 0)
            lines.append(f"  Qdrant: {session.get('qdrant_count', 0)} ({qdrant_ratio*100:.0f}%)")
            lines.append(f"  Fallback: {session.get('fallback_count', 0)}")
            lines.append(f"  Auto-reruns: {session.get('rerun_count', 0)}")
            lines.append("")
            
            # Last retrieval
            last = stats.get("last_retrieval")
            if last:
                lines.append("**Last Query**")
                lines.append(f"  Engine: `{last.get('engine', 'unknown')}`")
                lines.append(f"  Citations: {last.get('total_citations', 0)}")
                lines.append(f"  Reruns: {last.get('rerun_count', 0)}")
                lines.append(f"  Time: {last.get('execution_time_ms', 0):.0f}ms")
                
                # Doc type distribution
                doc_types = last.get('doc_type_counts', {})
                if doc_types:
                    lines.append(f"  Doc Types:")
                    for dt, count in sorted(doc_types.items(), key=lambda x: -x[1])[:5]:
                        lines.append(f"    • {dt}: {count}")
                lines.append("")
            
            # Engine distribution (recent)
            engine_dist = stats.get("engine_distribution", {})
            if engine_dist:
                lines.append("**Engine Distribution (recent)**")
                for engine, count in sorted(engine_dist.items(), key=lambda x: -x[1]):
                    lines.append(f"  • {engine}: {count}")
                lines.append("")
            
            # Aggregate doc type stats
            recent_dt = stats.get("recent_doc_types", {})
            if recent_dt:
                lines.append("**Doc Type Distribution (all recent)**")
                for dt, count in sorted(recent_dt.items(), key=lambda x: -x[1])[:7]:
                    lines.append(f"  • {dt}: {count}")
            
        except ImportError as e:
            lines.append(f"⚠️ Diagnostics module not available: {e}")
        except Exception as e:
            lines.append(f"❌ Error: {e}")
        
        return GatewayResponse(
            text="\n".join(lines),
            log_entry={"type": "diag"}
        )
    
    # =========================================================================
    # PERSISTENT MEMORY HANDLERS
    # =========================================================================
    
    def handle_memories_command(self, chat_id: str) -> GatewayResponse:
        """Handle /memories command - show what Ira remembers about the user."""
        lines = ["🧠 **WHAT I REMEMBER ABOUT YOU**\n"]
        user_identity_id = chat_id  # Default
        
        # Get identity if available
        try:
            from memory_service import get_memory_service
            memory = get_memory_service()
            identity = memory.get_identity(telegram_chat_id=chat_id)
            if identity:
                user_identity_id = identity.identity_id
        except Exception:
            pass
        
        # ===== MEM0 MEMORIES (Primary - Modern AI Memory) =====
        if MEM0_AVAILABLE:
            try:
                mem0_svc = _get_mem0()
                if mem0_svc:
                    mem0_memories = mem0_svc.get_all(user_id=user_identity_id)
                    
                    if mem0_memories:
                        lines.append("**✨ Mem0 AI Memory:**")
                        for i, mem in enumerate(mem0_memories[:15], 1):
                            lines.append(f"  {i}. {mem.memory}")
                        if len(mem0_memories) > 15:
                            lines.append(f"  ... and {len(mem0_memories) - 15} more")
                        lines.append("")
                    else:
                        lines.append("*No Mem0 memories yet - we'll learn as we chat!*\n")
                else:
                    lines.append("*Mem0 service not initialized*\n")
            except Exception as e:
                lines.append(f"*Mem0 unavailable: {e}*\n")
        
        # ===== LEGACY POSTGRES MEMORIES (Backup) =====
        if PERSISTENT_MEMORY_AVAILABLE:
            try:
                pm = get_persistent_memory()
                legacy_memories = pm.get_all_memories(identity_id=user_identity_id, limit=10)
                
                if legacy_memories:
                    lines.append("**📚 Legacy Memory (PostgreSQL):**")
                    for mem in legacy_memories:
                        lines.append(f"  • {mem.memory_text}")
                    lines.append("")
            except Exception:
                pass
        
        if len(lines) <= 1:
            lines.append("I don't have any memories yet. As we chat, I'll start remembering things about you!")
        
        return GatewayResponse(
            text="\n".join(lines),
            log_entry={"type": "memories_list", "identity_id": user_identity_id}
        )
    
    def _handle_remember_command(self, text: str, chat_id: str) -> Optional[GatewayResponse]:
        """Handle explicit 'remember that...' commands."""
        # Check if this looks like a remember command
        remember_patterns = ["remember that", "remember:", "note that", "keep in mind"]
        text_lower = text.lower().strip()
        
        if not any(p in text_lower for p in remember_patterns):
            return None
        
        try:
            from memory_service import get_memory_service
            memory = get_memory_service()
            
            # Get or create identity
            identity = memory.get_identity(telegram_chat_id=chat_id)
            if not identity:
                identity = memory.create_or_update_identity(telegram_chat_id=chat_id)
            
            if not identity:
                return GatewayResponse(
                    text="I couldn't create a memory identity for you. Please try again.",
                    success=False
                )
            
            pm = get_persistent_memory()
            success, response_msg = pm.handle_explicit_remember(
                identity_id=identity.identity_id,
                message=text,
                source_channel="telegram"
            )
            
            if response_msg:
                return GatewayResponse(
                    text=response_msg,
                    log_entry={"type": "remember_explicit", "success": success}
                )
            
        except Exception as e:
            logger.error(f"Remember command error: {e}")
        
        return None
    
    def _handle_forget_command(self, text: str, chat_id: str) -> Optional[GatewayResponse]:
        """Handle 'forget' commands."""
        text_lower = text.lower().strip()
        
        if not text_lower.startswith("forget"):
            return None
        
        try:
            from memory_service import get_memory_service
            memory = get_memory_service()
            
            identity = memory.get_identity(telegram_chat_id=chat_id)
            if not identity:
                return GatewayResponse(
                    text="I don't have any memories about you to forget.",
                    log_entry={"type": "forget_no_identity"}
                )
            
            pm = get_persistent_memory()
            success, response_msg = pm.handle_forget_command(
                identity_id=identity.identity_id,
                message=text
            )
            
            if response_msg:
                return GatewayResponse(
                    text=response_msg,
                    log_entry={"type": "forget", "success": success}
                )
            
        except Exception as e:
            logger.error(f"Forget command error: {e}")
        
        return None
    
    def handle_fail_command(self, text: str) -> GatewayResponse:
        """Handle /fail and /fixplan commands for failure logging."""
        try:
            from failure_logger import handle_fail_command as fail_handler
            response_text = fail_handler(text, channel="telegram")
            return GatewayResponse(
                text=response_text,
                log_entry={"type": "fail_command", "command": text}
            )
        except ImportError as e:
            return GatewayResponse(
                text=f"⚠️ Failure logger not available: {e}",
                success=False
            )
        except Exception as e:
            return GatewayResponse(
                text=f"❌ Error: {e}",
                success=False
            )
    
    def handle_takeout_command(self, text: str) -> GatewayResponse:
        """Handle /takeout commands for email ingestion stats."""
        try:
            from openclaw.agents.ira.src.takeout_ingest import handle_takeout_command as takeout_handler
            response_text = takeout_handler(text)
            return GatewayResponse(
                text=response_text,
                log_entry={"type": "takeout_command", "command": text}
            )
        except ImportError as e:
            return GatewayResponse(
                text=f"⚠️ Takeout ingest not available: {e}",
                success=False
            )
        except Exception as e:
            return GatewayResponse(
                text=f"❌ Error: {e}",
                success=False
            )
    
    # =========================================================================
    # MEMORY ANALYTICS COMMANDS
    # =========================================================================
    
    def handle_search_memory(self, query: str) -> GatewayResponse:
        """
        Handle /search_memory <query> - Search what IRA knows about a topic.
        
        Searches across:
        - Conversation history
        - Persistent memories
        - Learned corrections
        - Entity memories
        """
        try:
            sys.path.insert(0, str(AGENT_DIR / "src" / "memory"))
            from memory_analytics import search_memories, format_search_for_telegram
            
            results = search_memories(query, limit=15)
            response_text = format_search_for_telegram(query, results)
            
            return GatewayResponse(
                text=response_text,
                log_entry={"type": "search_memory", "query": query, "results": len(results)}
            )
        except ImportError as e:
            return GatewayResponse(
                text=f"⚠️ Memory analytics not available: {e}",
                success=False
            )
        except Exception as e:
            return GatewayResponse(
                text=f"❌ Search error: {e}",
                success=False
            )
    
    def handle_memory_stats(self) -> GatewayResponse:
        """Handle /memory_stats - Show memory analytics dashboard."""
        try:
            sys.path.insert(0, str(AGENT_DIR / "src" / "memory"))
            from memory_analytics import format_stats_for_telegram
            
            response_text = format_stats_for_telegram()
            
            return GatewayResponse(
                text=response_text,
                log_entry={"type": "memory_stats"}
            )
        except ImportError as e:
            return GatewayResponse(
                text=f"⚠️ Memory analytics not available: {e}",
                success=False
            )
        except Exception as e:
            return GatewayResponse(
                text=f"❌ Stats error: {e}",
                success=False
            )
    
    def handle_export_memory(self) -> GatewayResponse:
        """Handle /export_memory - Export all IRA knowledge to backup file."""
        try:
            sys.path.insert(0, str(AGENT_DIR / "src" / "memory"))
            from memory_analytics import export_all_knowledge
            from datetime import datetime
            
            # Create backup file path
            backup_dir = PROJECT_ROOT / "crm" / "backups"
            backup_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = backup_dir / f"ira_memory_backup_{timestamp}.json"
            
            summary = export_all_knowledge(str(backup_path))
            
            response_text = f"""✅ **Memory Backup Complete**

**Exported to:** `{backup_path.name}`

**Summary:**
• Conversation states: {summary.get('conversation', 0)}
• Persistent memories: {summary.get('persistent', 0)}
• Entity memories: {summary.get('entity', 0)}
• Learned corrections: {summary.get('learned', 0)}

File saved to: `crm/backups/`"""
            
            return GatewayResponse(
                text=response_text,
                log_entry={"type": "export_memory", "path": str(backup_path), "summary": summary}
            )
        except Exception as e:
            return GatewayResponse(
                text=f"❌ Export error: {e}",
                success=False
            )
    
    def handle_decay_memory(self) -> GatewayResponse:
        """Handle /decay_memory - Apply memory decay to old unused memories."""
        try:
            sys.path.insert(0, str(AGENT_DIR / "src" / "memory"))
            from memory_analytics import apply_memory_decay
            
            # First do a dry run
            dry_result = apply_memory_decay(days=90, dry_run=True)
            
            response_text = f"""🧹 **Memory Decay Preview**

**Would affect:**
• Decayed (confidence reduced): {dry_result.get('decayed', 0)}
• Deactivated (too old): {dry_result.get('deactivated', 0)}
• Preserved (in use): {dry_result.get('preserved', 0)}

Reply `CONFIRM DECAY` to apply these changes."""
            
            # Store pending decay for confirmation
            self._pending_decay = dry_result
            
            return GatewayResponse(
                text=response_text,
                log_entry={"type": "decay_preview", "preview": dry_result}
            )
        except Exception as e:
            return GatewayResponse(
                text=f"❌ Decay error: {e}",
                success=False
            )
    
    # =========================================================================
    # CONFLICT RESOLUTION HANDLERS
    # =========================================================================
    
    def handle_conflicts_command(self) -> GatewayResponse:
        """Handle /conflicts - Show all pending memory conflicts."""
        try:
            sys.path.insert(0, str(AGENT_DIR / "src" / "memory"))
            from conflict_clarifier import handle_conflicts_command
            
            response_text = handle_conflicts_command()
            
            return GatewayResponse(
                text=response_text,
                log_entry={"type": "conflicts_list"}
            )
        except ImportError as e:
            return GatewayResponse(
                text=f"⚠️ Conflict resolver not available: {e}",
                success=False
            )
        except Exception as e:
            return GatewayResponse(
                text=f"❌ Conflicts error: {e}",
                success=False
            )
    
    def handle_price_conflicts_command(self) -> GatewayResponse:
        """Handle /price_conflicts - Show pending price conflicts."""
        try:
            sys.path.insert(0, str(BRAIN_DIR))
            from pricing_learner import PricingLearner
            
            learner = PricingLearner(verbose=False)
            message = learner.format_conflicts_message()
            
            if not message:
                return GatewayResponse(
                    text="✅ No pending price conflicts.\n\nAll prices are consistent!",
                    success=True,
                )
            
            return GatewayResponse(
                text=message,
                success=True,
            )
        except ImportError as e:
            return GatewayResponse(
                text=f"❌ Pricing system not available: {e}",
                success=False,
            )
        except Exception as e:
            return GatewayResponse(
                text=f"❌ Error: {e}",
                success=False,
            )
    
    def _validate_machine_model(self, model: str) -> tuple[bool, str]:
        """Validate machine model format."""
        model = model.upper().strip()
        
        # Valid patterns: PF1-X-3020, ATF-1218, IMG-1350, AM-V-5060, etc.
        valid_patterns = [
            r'^PF[12]?-?[XCSPRA]?-?\d{4}$',
            r'^ATF-?\d{3,4}$',
            r'^IMG-?\d{3,4}$',
            r'^AM-?[MVP]-?\d{4}$',
            r'^FCS-?\d{4}$',
            r'^RT-?\d+[A-Z]?-?\d*$',
        ]
        
        import re
        for pattern in valid_patterns:
            if re.match(pattern, model, re.IGNORECASE):
                return True, model
        
        return False, f"Invalid model format: {model}"
    
    def handle_resolve_price_command(self, model: str, price_str: str) -> GatewayResponse:
        """Handle /resolve_price <model> <price> - Resolve a price conflict."""
        # Validate model format
        is_valid, result = self._validate_machine_model(model)
        if not is_valid:
            return GatewayResponse(
                text=f"❌ {result}\n\nExpected formats: PF1-C-3020, ATF-1218, IMG-1350",
                success=False,
            )
        model = result
        
        try:
            sys.path.insert(0, str(BRAIN_DIR))
            from pricing_learner import PricingLearner
            
            learner = PricingLearner(verbose=False)
            
            try:
                price = int(price_str.replace(",", ""))
            except ValueError:
                return GatewayResponse(
                    text=f"❌ Invalid price format: {price_str}",
                    success=False,
                )
            
            # Validate reasonable price range (₹1 lakh to ₹50 crore)
            MIN_PRICE = 100_000  # 1 lakh
            MAX_PRICE = 500_000_000  # 50 crore
            
            if price < MIN_PRICE:
                return GatewayResponse(
                    text=f"❌ Price ₹{price:,} seems too low. Did you mean ₹{price * 100_000:,} (in lakhs)?",
                    success=False,
                )
            
            if price > MAX_PRICE:
                return GatewayResponse(
                    text=f"❌ Price ₹{price:,} seems unreasonably high. Please verify.",
                    success=False,
                )
            
            model = model.upper()
            learner.resolve_conflict(model, price, "Resolved via Telegram")
            
            return GatewayResponse(
                text=f"✅ Price conflict resolved!\n\n**{model}**: ₹{price:,}\n\nI'll use this price for future quotes.",
                success=True,
            )
        except ImportError as e:
            return GatewayResponse(
                text=f"❌ Pricing system not available: {e}",
                success=False,
            )
        except Exception as e:
            return GatewayResponse(
                text=f"❌ Error resolving price: {e}",
                success=False,
            )
    
    def handle_resolve_command(self, args: str) -> GatewayResponse:
        """Handle /resolve <id> <1|2|merge:text> - Resolve a specific conflict."""
        try:
            sys.path.insert(0, str(AGENT_DIR / "src" / "memory"))
            from conflict_clarifier import handle_resolve_command
            
            response_text = handle_resolve_command(args)
            
            return GatewayResponse(
                text=response_text,
                log_entry={"type": "conflict_resolved", "args": args}
            )
        except ImportError as e:
            return GatewayResponse(
                text=f"⚠️ Conflict resolver not available: {e}",
                success=False
            )
        except Exception as e:
            return GatewayResponse(
                text=f"❌ Resolve error: {e}",
                success=False
            )
    
    def _validate_ingest_path(self, path: str) -> tuple[bool, str, Path]:
        """
        Validate that a path is safe for ingestion.
        
        Returns:
            (is_valid, error_message, resolved_path)
        """
        try:
            resolved = Path(path).expanduser().resolve()
        except Exception as e:
            return False, f"Invalid path: {e}", None
        
        # Check for path traversal attempts
        if ".." in path:
            return False, "Path traversal not allowed", None
        
        # Allow absolute paths only within project or home directories
        allowed_prefixes = [
            PROJECT_ROOT / "data" / "imports",
            PROJECT_ROOT / "data" / "exports",
            Path.home() / "Documents",
            Path.home() / "Downloads",
        ]
        
        is_allowed = any(
            str(resolved).startswith(str(prefix.resolve()))
            for prefix in allowed_prefixes
            if prefix.exists()
        )
        
        if not is_allowed:
            # Also allow relative paths that resolve to imports
            imports_dir = PROJECT_ROOT / "data" / "imports"
            if not str(resolved).startswith(str(imports_dir.resolve())):
                return False, f"Path must be within allowed directories (data/imports, Documents, Downloads)", None
        
        if not resolved.exists():
            return False, f"File not found: {resolved.name}", None
        
        if not resolved.is_file():
            return False, "Path must be a file, not a directory", None
        
        allowed_extensions = {'.pdf', '.xlsx', '.xls', '.docx', '.doc', '.csv', '.txt', '.json'}
        if resolved.suffix.lower() not in allowed_extensions:
            return False, f"Unsupported file type: {resolved.suffix}", None
        
        return True, "", resolved
    
    def handle_ingest_command(self, path: str) -> GatewayResponse:
        """Handle /ingest <path> - Ingest a document into memory."""
        # Validate path first
        is_valid, error_msg, resolved_path = self._validate_ingest_path(path)
        if not is_valid:
            return GatewayResponse(
                text=f"❌ {error_msg}",
                success=False
            )
        
        try:
            sys.path.insert(0, str(AGENT_DIR / "src" / "memory"))
            from document_ingestor import DocumentIngestor
            
            ingestor = DocumentIngestor(check_conflicts=True)
            result = ingestor.ingest(str(resolved_path))
            
            # Format response
            response_text = f"""📄 **Document Ingested: {Path(path).name}**

**Results:**
• Pages/Sheets: {result.pages_processed}
• Facts Extracted: {result.facts_extracted}
• Memories Stored: {result.memories_stored}
• Conflicts Found: {result.conflicts_found}
• Duration: {result.duration_seconds:.1f}s
"""
            
            if result.conflicts_found > 0:
                response_text += f"""
⚠️ **{result.conflicts_found} conflicts detected!**
Use `/conflicts` to review and resolve them."""
            
            if result.errors:
                response_text += f"\n\n⚠️ Errors: {', '.join(result.errors[:3])}"
            
            return GatewayResponse(
                text=response_text,
                log_entry={
                    "type": "document_ingested",
                    "path": path,
                    "facts": result.facts_extracted,
                    "stored": result.memories_stored,
                    "conflicts": result.conflicts_found
                }
            )
        except ImportError as e:
            return GatewayResponse(
                text=f"⚠️ Document ingestor not available: {e}",
                success=False
            )
        except Exception as e:
            return GatewayResponse(
                text=f"❌ Ingest error: {e}",
                success=False
            )
    
    def _handle_index_status(self) -> GatewayResponse:
        """Handle /index — show metadata index stats."""
        try:
            sys.path.insert(0, str(BRAIN_DIR))
            from imports_metadata_index import get_index_stats, get_index_progress
            
            progress = get_index_progress()
            if progress:
                return GatewayResponse(
                    text=(
                        f"\U0001f504 **Indexing in progress...**\n\n"
                        f"Progress: {progress['done']}/{progress['total']} ({progress['percent']}%)\n"
                        f"Current: {progress['current']}"
                    )
                )
            
            stats = get_index_stats()
            if stats.get("indexed", 0) == 0:
                return GatewayResponse(
                    text=(
                        "\U0001f4c1 **Metadata Index: Not built yet**\n\n"
                        f"Files on disk: {stats.get('total_on_disk', '?')}\n\n"
                        "Run `/index build` to scan all files and build the index.\n"
                        "This uses GPT-4o-mini to summarize each document (~$5 for 500 files)."
                    )
                )
            
            doc_types = stats.get("doc_types", {})
            type_lines = "\n".join(f"  \u2022 {k}: {v}" for k, v in sorted(doc_types.items(), key=lambda x: -x[1])[:8])
            
            return GatewayResponse(
                text=(
                    f"\U0001f4c1 **Metadata Index**\n\n"
                    f"Indexed: **{stats['indexed']}** / {stats.get('total_on_disk', '?')} files\n"
                    f"Unindexed: {stats.get('unindexed', 0)}\n"
                    f"Unique machines: {stats.get('unique_machines', 0)}\n"
                    f"Built: {stats.get('built_at', 'N/A')}\n\n"
                    f"**Document types:**\n{type_lines}\n\n"
                    f"Run `/index build` to update."
                ),
                log_entry={"type": "index_status"}
            )
        except ImportError as e:
            return GatewayResponse(text=f"\u26a0\ufe0f Metadata index module not available: {e}", success=False)
        except Exception as e:
            return GatewayResponse(text=f"\u274c Index error: {e}", success=False)

    def _handle_index_build(self) -> GatewayResponse:
        """Handle /index build — trigger metadata index build in background."""
        try:
            sys.path.insert(0, str(BRAIN_DIR))
            from imports_metadata_index import build_index, get_index_stats
            import threading
            
            stats = get_index_stats()
            total = stats.get("total_on_disk", 0)
            
            chat_id = self._current_chat_id or TELEGRAM_CHAT_ID if hasattr(self, '_current_chat_id') else ""
            
            def _run():
                try:
                    result = build_index(use_llm=True, force=False)
                    msg = (
                        f"\u2705 **Index build complete!**\n\n"
                        f"New: {result['new']}\n"
                        f"Skipped (unchanged): {result['skipped']}\n"
                        f"Errors: {result['errors']}\n"
                        f"Total indexed: {result['new'] + result['skipped']}"
                    )
                    self.send_message(msg)
                except Exception as e:
                    self.send_message(f"\u274c Index build failed: {e}")
            
            thread = threading.Thread(target=_run, daemon=True)
            thread.start()
            
            return GatewayResponse(
                text=(
                    f"\U0001f504 **Index build started!**\n\n"
                    f"Scanning {total} files in data/imports/...\n"
                    f"This will take ~15-30 minutes (LLM summarization).\n"
                    f"I'll notify you when it's done.\n\n"
                    f"Use `/index` to check progress."
                ),
                log_entry={"type": "index_build_started"}
            )
        except ImportError as e:
            return GatewayResponse(text=f"\u26a0\ufe0f Metadata index module not available: {e}", success=False)
        except Exception as e:
            return GatewayResponse(text=f"\u274c Index build error: {e}", success=False)

    def _handle_research_feedback(self, research_id: str, is_positive: bool) -> GatewayResponse:
        """Handle /confirm or /reject for NN research results."""
        try:
            sys.path.insert(0, str(BRAIN_DIR))
            from nn_research import handle_research_feedback
            result = handle_research_feedback(research_id, is_positive)
            return GatewayResponse(
                text=result,
                log_entry={"type": "research_feedback", "id": research_id, "positive": is_positive}
            )
        except ImportError as e:
            return GatewayResponse(text=f"\u26a0\ufe0f NN Research module not available: {e}", success=False)
        except Exception as e:
            return GatewayResponse(text=f"\u274c Feedback error: {e}", success=False)

    def handle_quote_command(self, params: str) -> GatewayResponse:
        """
        Handle /quote command - Generate a quick quote.
        
        Usage:
            /quote 2000x1500         → PF1-C quote for 2000x1500mm
            /quote 2000x1500 servo   → PF1-X servo variant
            /quote 3m x 2m           → Automatic size conversion
        """
        try:
            sys.path.insert(0, str(AGENT_DIR / "src" / "brain"))
            from quote_generator import generate_quote
            from quote_email_formatter import format_quote_telegram
        except ImportError as e:
            return GatewayResponse(
                text=f"⚠️ Quote generator not available: {e}",
                success=False
            )
        
        import re
        
        # Parse size from params
        size_match = re.search(r'(\d+\.?\d*)\s*[xX×]\s*(\d+\.?\d*)', params)
        if not size_match:
            return GatewayResponse(
                text="""❌ Could not parse size.

**Usage:** `/quote <width>x<height> [variant]`

**Examples:**
• `/quote 2000x1500` → PF1-C for 2000×1500mm
• `/quote 2000x1500 servo` → PF1-X servo variant
• `/quote 3x2 m` → 3000×2000mm (auto-converts)""",
                success=False
            )
        
        w, h = float(size_match.group(1)), float(size_match.group(2))
        
        # Auto-convert meters to mm
        if w < 100 and h < 100:
            w, h = int(w * 1000), int(h * 1000)
        else:
            w, h = int(w), int(h)
        
        # Check for variant - extract from remaining text after removing the size portion
        variant = "C"
        params_lower = params.lower()
        # Remove the size portion (e.g. "2000x1500") so "x" in dimensions doesn't trigger servo
        params_without_size = re.sub(r'\d+\.?\d*\s*[xX×]\s*\d+\.?\d*', '', params_lower).strip()
        if "servo" in params_without_size or "pf1-x" in params_without_size or "pf1x" in params_without_size:
            variant = "X"
        elif "pneumatic" in params_without_size or "pf1-c" in params_without_size or "pf1c" in params_without_size:
            variant = "C"
        
        # Check for materials
        materials = []
        material_list = ["hdpe", "abs", "pp", "ps", "pvc", "pmma", "pc", "pet"]
        for mat in material_list:
            if mat in params_lower:
                materials.append(mat.upper())
        
        try:
            quote = generate_quote(
                forming_size=(w, h),
                variant=variant,
                materials=materials or None,
            )
            
            quote_text = format_quote_telegram(quote, compact=False)
            
            return GatewayResponse(
                text=quote_text,
                log_entry={
                    "type": "quote_generated",
                    "quote_id": quote.quote_id,
                    "model": quote.recommended_model,
                    "size": f"{w}x{h}",
                    "total_inr": quote.total_inr,
                }
            )
        except Exception as e:
            return GatewayResponse(
                text=f"❌ Quote generation error: {e}",
                success=False
            )
    
    def _check_conflict_response(self, text: str) -> Optional[GatewayResponse]:
        """Check if text is a quick response to a pending conflict."""
        text_lower = text.strip().lower()
        
        # Only check if it looks like a conflict response
        if text_lower not in ["1", "2"] and not text_lower.startswith("merge:"):
            return None
        
        try:
            sys.path.insert(0, str(AGENT_DIR / "src" / "memory"))
            from conflict_clarifier import check_if_conflict_response
            
            response_text = check_if_conflict_response(text)
            
            if response_text:
                return GatewayResponse(
                    text=response_text,
                    log_entry={"type": "conflict_quick_resolve", "response": text}
                )
            
            return None
        except Exception:
            return None
    
    # =========================================================================
    # RELATIONSHIP DASHBOARD HANDLERS
    # =========================================================================
    
    def handle_dashboard_command(self) -> GatewayResponse:
        """Handle /dashboard - Show relationship health overview."""
        try:
            sys.path.insert(0, str(AGENT_DIR / "src" / "conversation"))
            from relationship_dashboard import generate_report
            
            report = generate_report("text")
            
            return GatewayResponse(
                text=report,
                log_entry={"type": "dashboard"}
            )
        except ImportError as e:
            return GatewayResponse(
                text=f"⚠️ Relationship dashboard not available: {e}",
                success=False
            )
        except Exception as e:
            return GatewayResponse(
                text=f"❌ Dashboard error: {e}",
                success=False
            )
    
    def handle_priorities_command(self) -> GatewayResponse:
        """Handle /priorities - Show top contacts needing attention."""
        try:
            sys.path.insert(0, str(AGENT_DIR / "src" / "conversation"))
            from relationship_dashboard import get_priorities
            
            priorities = get_priorities(5)
            
            if not priorities:
                return GatewayResponse(
                    text="✅ No urgent priorities. All relationships healthy!",
                    log_entry={"type": "priorities", "count": 0}
                )
            
            lines = ["🎯 **Top Priority Contacts**", ""]
            for i, p in enumerate(priorities, 1):
                name = p.get("name", p.get("contact_id", "Unknown"))
                warmth = p.get("warmth", "unknown")
                reasons = p.get("reasons", [])
                
                warmth_emoji = {"trusted": "🌟", "warm": "❤️", "familiar": "👋", "acquaintance": "🤝"}.get(warmth, "👤")
                
                lines.append(f"**{i}. {name}** {warmth_emoji}")
                for reason in reasons[:2]:
                    lines.append(f"   • {reason}")
                lines.append("")
            
            return GatewayResponse(
                text="\n".join(lines),
                log_entry={"type": "priorities", "count": len(priorities)}
            )
        except Exception as e:
            return GatewayResponse(
                text=f"❌ Error: {e}",
                success=False
            )
    
    def handle_at_risk_command(self) -> GatewayResponse:
        """Handle /at_risk - Show at-risk relationships."""
        try:
            sys.path.insert(0, str(AGENT_DIR / "src" / "conversation"))
            from relationship_dashboard import get_at_risk
            
            at_risk = get_at_risk()
            
            if not at_risk:
                return GatewayResponse(
                    text="✅ No relationships at risk. Great job!",
                    log_entry={"type": "at_risk", "count": 0}
                )
            
            lines = ["⚠️ **At-Risk Relationships**", ""]
            for r in at_risk:
                name = r.get("name", r.get("contact_id", "Unknown"))
                score = r.get("health_score", 0)
                trend = r.get("trend", "unknown")
                suggestions = r.get("suggestions", [])
                
                trend_emoji = {"declining": "📉", "stable": "➡️", "improving": "📈"}.get(trend, "❓")
                
                lines.append(f"**{name}** - Health: {score:.0f}/100 {trend_emoji}")
                if suggestions:
                    lines.append(f"   💡 {suggestions[0]}")
                lines.append("")
            
            return GatewayResponse(
                text="\n".join(lines),
                log_entry={"type": "at_risk", "count": len(at_risk)}
            )
        except Exception as e:
            return GatewayResponse(
                text=f"❌ Error: {e}",
                success=False
            )
    
    def handle_contact_detail_command(self, query: str) -> GatewayResponse:
        """Handle /contact <name> - Show detail about a contact."""
        try:
            conv_enhancer = get_conversational_enhancer()
            if not conv_enhancer:
                return GatewayResponse(
                    text="⚠️ Contact tracking not available.",
                    success=False
                )
            
            # Search for contact by name or ID
            query_lower = query.lower()
            matching_contact = None
            
            for contact_id, rel in conv_enhancer.relationship_memory.relationships.items():
                if query_lower in contact_id.lower() or query_lower in rel.name.lower():
                    matching_contact = contact_id
                    break
            
            if not matching_contact:
                return GatewayResponse(
                    text=f"❌ No contact found matching '{query}'",
                    success=False
                )
            
            # Get detail via dashboard
            sys.path.insert(0, str(AGENT_DIR / "src" / "conversation"))
            from relationship_dashboard import get_contact_detail
            
            detail = get_contact_detail(matching_contact)
            
            if not detail:
                return GatewayResponse(
                    text=f"❌ Could not retrieve details for '{query}'",
                    success=False
                )
            
            # Format response
            warmth_emoji = {"trusted": "🌟", "warm": "❤️", "familiar": "👋", "acquaintance": "🤝", "stranger": "👤"}.get(detail.get("warmth", ""), "")
            
            lines = [f"👤 **{detail.get('name', 'Unknown')}** {warmth_emoji}", ""]
            lines.append(f"**Warmth:** {detail.get('warmth', 'unknown').title()} ({detail.get('warmth_score', 0):.1f})")
            lines.append(f"**Interactions:** {detail.get('interaction_count', 0)} ({detail.get('positive_interactions', 0)} positive)")
            
            # Conversation health
            health = detail.get("conversation_health")
            if health:
                trend_emoji = {"declining": "📉", "stable": "➡️", "improving": "📈"}.get(health.get("trend", ""), "")
                lines.append(f"**Health:** {health.get('health_score', 50):.0f}/100 {trend_emoji}")
            
            # Style
            style = detail.get("style_profile")
            if style:
                traits = []
                if style.get("formality_score", 50) > 70:
                    traits.append("formal")
                elif style.get("formality_score", 50) < 30:
                    traits.append("casual")
                if style.get("detail_score", 50) > 70:
                    traits.append("detail-oriented")
                if traits:
                    lines.append(f"**Style:** {', '.join(traits)}")
            
            # Insights
            insights = detail.get("insights", [])
            if insights:
                lines.append("")
                lines.append("**Insights:**")
                for i in insights[:2]:
                    lines.append(f"  • {i.get('title', '')}")
            
            # Improvement suggestions
            suggestions = detail.get("improvement_suggestions", [])
            if suggestions:
                lines.append("")
                lines.append("**Suggestions:**")
                for s in suggestions[:2]:
                    lines.append(f"  💡 {s}")
            
            return GatewayResponse(
                text="\n".join(lines),
                log_entry={"type": "contact_detail", "contact": matching_contact}
            )
        except Exception as e:
            return GatewayResponse(
                text=f"❌ Error: {e}",
                success=False
            )
    
    def handle_good_command(self, chat_id: str) -> GatewayResponse:
        """Handle /good - Rate last response as good."""
        try:
            conv_enhancer = get_conversational_enhancer()
            if not conv_enhancer:
                return GatewayResponse(text="❌ Feedback system not available")
            
            # Record positive feedback for this contact
            contact_id = str(chat_id)
            
            # Get recent turn quality and mark it positive
            recent_turns = conv_enhancer.store.get_turn_history(contact_id, limit=1)
            if not recent_turns:
                return GatewayResponse(text="No recent interaction to rate.")
            
            turn = recent_turns[0]
            turn_id = turn.get("turn_id")
            
            # Update the turn quality with explicit positive feedback
            with conv_enhancer.store._get_conn() as conn:
                conn.execute("""
                    UPDATE turn_quality 
                    SET overall_score = MAX(overall_score, 85),
                        signals = COALESCE(signals, '') || ',explicit_positive_feedback'
                    WHERE turn_id = ?
                """, (turn_id,))
                
                # Also record this as a behavioral pattern
                conv_enhancer.store.record_pattern(
                    contact_id=contact_id,
                    pattern_type="feedback",
                    pattern_key="positive",
                    metadata={"turn_id": turn_id}
                )
            
            # Record quality feedback for consolidated knowledge used in the response
            knowledge_tracked = 0
            if QUALITY_TRACKING_AVAILABLE and hasattr(self, '_last_consolidated_ids'):
                knowledge_tracked = record_feedback_by_ids(self._last_consolidated_ids, was_helpful=True)
            
            extra_info = ""
            if knowledge_tracked > 0:
                extra_info = f"\n📊 Updated quality scores for {knowledge_tracked} learned knowledge items."
            
            return GatewayResponse(
                text=f"✅ Thanks! Noted that response worked well.{extra_info}",
                log_entry={"type": "feedback", "rating": "good", "turn_id": turn_id, "knowledge_tracked": knowledge_tracked}
            )
        except Exception as e:
            return GatewayResponse(text=f"❌ Error recording feedback: {e}", success=False)
    
    def handle_bad_command(self, chat_id: str, reason: str = "") -> GatewayResponse:
        """Handle /bad [reason] - Rate last response as bad."""
        try:
            conv_enhancer = get_conversational_enhancer()
            if not conv_enhancer:
                return GatewayResponse(text="❌ Feedback system not available")
            
            contact_id = str(chat_id)
            
            # Get recent turn quality
            recent_turns = conv_enhancer.store.get_turn_history(contact_id, limit=1)
            if not recent_turns:
                return GatewayResponse(text="No recent interaction to rate.")
            
            turn = recent_turns[0]
            turn_id = turn.get("turn_id")
            
            # Update the turn quality with explicit negative feedback
            signal = f"explicit_negative_feedback:{reason}" if reason else "explicit_negative_feedback"
            
            with conv_enhancer.store._get_conn() as conn:
                conn.execute("""
                    UPDATE turn_quality 
                    SET overall_score = MIN(overall_score, 30),
                        signals = COALESCE(signals, '') || ?
                    WHERE turn_id = ?
                """, (f",{signal}", turn_id))
                
                # Record the negative feedback pattern
                conv_enhancer.store.record_pattern(
                    contact_id=contact_id,
                    pattern_type="feedback",
                    pattern_key="negative",
                    metadata={"turn_id": turn_id, "reason": reason}
                )
            
            # Record negative quality feedback for consolidated knowledge
            knowledge_tracked = 0
            if QUALITY_TRACKING_AVAILABLE and hasattr(self, '_last_consolidated_ids'):
                knowledge_tracked = record_feedback_by_ids(self._last_consolidated_ids, was_helpful=False)
            
            response_text = "📝 Thanks for the feedback - I'll try to do better."
            if reason:
                response_text += f"\n\nReason noted: {reason}"
            if knowledge_tracked > 0:
                response_text += f"\n📊 Marked {knowledge_tracked} learned knowledge items as unhelpful."
            
            return GatewayResponse(
                text=response_text,
                log_entry={"type": "feedback", "rating": "bad", "reason": reason, "turn_id": turn_id, "knowledge_tracked": knowledge_tracked}
            )
        except Exception as e:
            return GatewayResponse(text=f"❌ Error recording feedback: {e}", success=False)
    
    def handle_feedback_command(self, chat_id: str) -> GatewayResponse:
        """Handle /feedback - Show feedback summary."""
        try:
            conv_enhancer = get_conversational_enhancer()
            if not conv_enhancer:
                return GatewayResponse(text="❌ Feedback system not available")
            
            contact_id = str(chat_id)
            
            with conv_enhancer.store._get_conn() as conn:
                # Count positive feedback
                pos = conn.execute("""
                    SELECT COUNT(*) as c FROM behavioral_patterns
                    WHERE contact_id = ? AND pattern_type = 'feedback' AND pattern_key = 'positive'
                """, (contact_id,)).fetchone()["c"]
                
                # Count negative feedback
                neg = conn.execute("""
                    SELECT COUNT(*) as c FROM behavioral_patterns
                    WHERE contact_id = ? AND pattern_type = 'feedback' AND pattern_key = 'negative'
                """, (contact_id,)).fetchone()["c"]
                
                # Get recent negative feedback reasons
                reasons = conn.execute("""
                    SELECT metadata FROM behavioral_patterns
                    WHERE contact_id = ? AND pattern_type = 'feedback' AND pattern_key = 'negative'
                    ORDER BY last_seen DESC LIMIT 3
                """, (contact_id,)).fetchall()
            
            total = pos + neg
            if total == 0:
                return GatewayResponse(text="No feedback recorded yet. Use /good or /bad after my responses.")
            
            lines = ["📊 **Feedback Summary**", ""]
            lines.append(f"✅ Good: {pos}")
            lines.append(f"❌ Bad: {neg}")
            
            if total > 0:
                satisfaction = (pos / total) * 100
                lines.append(f"📈 Satisfaction: {satisfaction:.0f}%")
            
            if reasons:
                import json
                lines.append("")
                lines.append("**Recent issues:**")
                for r in reasons:
                    try:
                        meta = json.loads(r["metadata"]) if r["metadata"] else {}
                        reason_text = meta.get("reason", "")
                        if reason_text:
                            lines.append(f"  • {reason_text}")
                    except (KeyError, TypeError):
                        pass
            
            return GatewayResponse(text="\n".join(lines))
        except Exception as e:
            return GatewayResponse(text=f"❌ Error: {e}", success=False)
    
    def handle_knowledge_quality_command(self) -> GatewayResponse:
        """Handle /knowledge_quality - Show quality report for consolidated knowledge."""
        try:
            if not QUALITY_TRACKING_AVAILABLE:
                return GatewayResponse(text="❌ Quality tracking not available")
            
            from src.memory.memory_consolidator import MemoryConsolidator
            consolidator = MemoryConsolidator(verbose=False)
            report = consolidator.get_quality_report()
            
            lines = ["📊 **Consolidated Knowledge Quality**", ""]
            
            # Overall stats
            lines.append(f"📚 Total tracked: {report.get('total_tracked', 0)}")
            lines.append(f"✅ Helpful: {report.get('helpful_count', 0)}")
            lines.append(f"❌ Not helpful: {report.get('not_helpful_count', 0)}")
            
            if report.get('overall_usefulness') is not None:
                usefulness = report['overall_usefulness'] * 100
                lines.append(f"📈 Overall usefulness: {usefulness:.0f}%")
            
            # Most useful
            most_useful = report.get('most_useful', [])
            if most_useful:
                lines.append("")
                lines.append("**🌟 Most useful:**")
                for item in most_useful[:3]:
                    content = item.get('content', '')[:50]
                    helpful = item.get('times_helpful', 0)
                    lines.append(f"  • _{content}..._ ({helpful}x helpful)")
            
            # Least useful
            least_useful = report.get('least_useful', [])
            if least_useful:
                lines.append("")
                lines.append("**⚠️ Least useful (consider removal):**")
                for item in least_useful[:3]:
                    content = item.get('content', '')[:50]
                    not_helpful = item.get('times_not_helpful', 0)
                    lines.append(f"  • _{content}..._ ({not_helpful}x not helpful)")
            
            # Never retrieved
            never_retrieved = report.get('never_retrieved', [])
            if never_retrieved:
                lines.append("")
                lines.append(f"**🔇 Never retrieved:** {len(never_retrieved)} items")
            
            return GatewayResponse(
                text="\n".join(lines),
                log_entry={"type": "knowledge_quality_view", "total": report.get('total_tracked', 0)}
            )
        except ImportError:
            return GatewayResponse(text="❌ Memory consolidator not available")
        except Exception as e:
            return GatewayResponse(text=f"❌ Error: {e}", success=False)
    
    def handle_outreach_command(self) -> GatewayResponse:
        """Handle /outreach - View queued outreach candidates."""
        try:
            from openclaw.agents.ira.src.conversation import get_outreach_queue
            queue = get_outreach_queue()
            
            if not queue:
                return GatewayResponse(text="📭 No outreach queued.\n\nIra will automatically detect contacts who might benefit from proactive outreach.")
            
            lines = ["📬 **Outreach Queue**", ""]
            
            for i, item in enumerate(queue[:10], 1):
                name = item.get("name", item.get("contact_id", "Unknown"))
                reasons = item.get("reasons", [])
                reason_text = reasons[0][:40] if reasons else "Check-in"
                priority = item.get("priority_score", 0)
                
                lines.append(f"{i}. **{name}** (priority: {priority:.1f})")
                lines.append(f"   📌 {reason_text}")
                lines.append(f"   💬 _{item.get('suggested_message', '')[:50]}..._")
                lines.append("")
            
            lines.append("Use `/approve <name>` to send or `/dismiss <name>` to remove.")
            
            return GatewayResponse(
                text="\n".join(lines),
                log_entry={"type": "outreach_view", "queue_size": len(queue)}
            )
        except Exception as e:
            return GatewayResponse(text=f"❌ Error: {e}", success=False)
    
    def handle_approve_outreach_command(self, args: str, chat_id: str) -> GatewayResponse:
        """Handle /approve <name> [custom message] - Send outreach."""
        try:
            from openclaw.agents.ira.src.conversation import get_outreach_queue, get_outreach_scheduler
            
            parts = args.strip().split(maxsplit=1)
            if not parts:
                return GatewayResponse(text="Usage: `/approve <name>` or `/approve <name> custom message`")
            
            search_name = parts[0].lower()
            custom_message = parts[1] if len(parts) > 1 else None
            
            # Find in queue
            queue = get_outreach_queue()
            matching = None
            for item in queue:
                name = item.get("name", "").lower()
                contact_id = item.get("contact_id", "").lower()
                if search_name in name or search_name in contact_id:
                    matching = item
                    break
            
            if not matching:
                return GatewayResponse(text=f"❌ No queued outreach for '{search_name}'.\n\nUse `/outreach` to see the queue.")
            
            # Set up send callback
            scheduler = get_outreach_scheduler()
            
            def send_via_telegram(channel: str, recipient: str, message: str) -> bool:
                if channel == "telegram":
                    try:
                        self.send_message(message, recipient)
                        return True
                    except Exception as e:
                        logger.error(f"[Outreach] Telegram send failed: {e}")
                        return False
                return False
            
            scheduler.send_callback = send_via_telegram
            
            # Send
            contact_id = matching.get("contact_id")
            success = scheduler.approve_and_send(contact_id, custom_message)
            
            if success:
                name = matching.get("name", contact_id)
                return GatewayResponse(
                    text=f"✅ Outreach sent to **{name}**!",
                    log_entry={"type": "outreach_sent", "contact": contact_id}
                )
            else:
                return GatewayResponse(text=f"❌ Failed to send outreach. Check if contact has a valid Telegram ID.")
        except Exception as e:
            return GatewayResponse(text=f"❌ Error: {e}", success=False)
    
    def handle_dismiss_outreach_command(self, name: str) -> GatewayResponse:
        """Handle /dismiss <name> - Remove from queue without sending."""
        try:
            from openclaw.agents.ira.src.conversation import get_outreach_queue, get_outreach_scheduler
            
            search_name = name.strip().lower()
            if not search_name:
                return GatewayResponse(text="Usage: `/dismiss <name>`")
            
            # Find in queue
            queue = get_outreach_queue()
            matching = None
            for item in queue:
                item_name = item.get("name", "").lower()
                contact_id = item.get("contact_id", "").lower()
                if search_name in item_name or search_name in contact_id:
                    matching = item
                    break
            
            if not matching:
                return GatewayResponse(text=f"❌ No queued outreach for '{name}'.")
            
            scheduler = get_outreach_scheduler()
            scheduler.dismiss(matching.get("contact_id"))
            
            return GatewayResponse(
                text=f"🗑️ Dismissed outreach for **{matching.get('name', name)}**.",
                log_entry={"type": "outreach_dismissed", "contact": matching.get("contact_id")}
            )
        except Exception as e:
            return GatewayResponse(text=f"❌ Error: {e}", success=False)
    
    def handle_outreach_stats_command(self) -> GatewayResponse:
        """Handle /outreach_stats - View outreach statistics."""
        try:
            from openclaw.agents.ira.src.conversation import get_outreach_scheduler
            scheduler = get_outreach_scheduler()
            stats = scheduler.get_stats()
            
            lines = ["📊 **Outreach Statistics**", ""]
            lines.append(f"**Status:** {'🟢 Running' if stats.get('running') else '⚪ Not started'}")
            lines.append(f"**Today:** {stats.get('daily_count', 0)}/{stats.get('daily_limit', 5)} sent")
            lines.append(f"**Queue:** {stats.get('queue_size', 0)} pending")
            
            if stats.get('last_check'):
                lines.append(f"**Last check:** {stats.get('last_check')[:16]}")
            
            lines.append("")
            lines.append("_Outreach respects rate limits and active hours._")
            
            return GatewayResponse(text="\n".join(lines))
        except Exception as e:
            return GatewayResponse(text=f"❌ Error: {e}", success=False)
    
    def handle_personality_command(self) -> GatewayResponse:
        """Handle /personality - View Ira's evolved personality traits."""
        try:
            conv_enhancer = get_conversational_enhancer()
            if not conv_enhancer:
                return GatewayResponse(text="❌ Conversational enhancer not available")
            
            summary = conv_enhancer.inner_voice.get_personality_summary()
            
            lines = ["🎭 **Ira's Personality Traits**", ""]
            lines.append("_These evolve based on what works in conversations._")
            lines.append("")
            
            trait_emojis = {
                "warmth": "❤️",
                "curiosity": "🔍",
                "enthusiasm": "🎉",
                "directness": "➡️",
                "empathy": "🤗",
                "humor": "😄",
                "charm": "💫",
            }
            
            for trait_name, data in summary.items():
                emoji = trait_emojis.get(trait_name, "•")
                value = data.get("value", 0.5)
                confidence = data.get("confidence", 0)
                positive = data.get("positive", 0)
                negative = data.get("negative", 0)
                
                # Visual bar
                filled = int(value * 10)
                bar = "█" * filled + "░" * (10 - filled)
                
                lines.append(f"{emoji} **{trait_name.title()}**: {bar} ({value:.0%})")
                if positive + negative > 0:
                    lines.append(f"   _+{positive}/-{negative} feedback, {confidence:.0%} confidence_")
            
            lines.append("")
            lines.append("_Use /good and /bad to help Ira learn._")
            lines.append("_Use /boost <trait> to manually adjust._")
            
            return GatewayResponse(text="\n".join(lines))
        except Exception as e:
            return GatewayResponse(text=f"❌ Error: {e}", success=False)
    
    def handle_boost_trait_command(self, trait_name: str) -> GatewayResponse:
        """Handle /boost <trait> - Manually increase a personality trait."""
        try:
            conv_enhancer = get_conversational_enhancer()
            if not conv_enhancer:
                return GatewayResponse(text="❌ Conversational enhancer not available")
            
            trait_name = trait_name.strip().lower()
            valid_traits = ["warmth", "curiosity", "enthusiasm", "directness", "empathy", "humor", "charm"]
            
            if trait_name not in valid_traits:
                return GatewayResponse(
                    text=f"❌ Unknown trait: {trait_name}\n\nValid traits: {', '.join(valid_traits)}"
                )
            
            trait = conv_enhancer.inner_voice.traits.get(trait_name)
            if not trait:
                return GatewayResponse(text=f"❌ Trait {trait_name} not found")
            
            old_value = trait.value
            trait.value = min(1.0, trait.value + 0.1)
            trait.positive_outcomes += 1  # Count as positive feedback
            
            # Save to SQLite
            conv_enhancer.inner_voice._save_state()
            
            trait_emojis = {
                "warmth": "❤️", "curiosity": "🔍", "enthusiasm": "🎉",
                "directness": "➡️", "empathy": "🤗", "humor": "😄", "charm": "💫"
            }
            emoji = trait_emojis.get(trait_name, "•")
            
            filled = int(trait.value * 10)
            bar = "█" * filled + "░" * (10 - filled)
            
            return GatewayResponse(
                text=f"{emoji} **{trait_name.title()}** boosted!\n\n{bar} {old_value:.0%} → {trait.value:.0%}",
                log_entry={"type": "trait_boost", "trait": trait_name, "new_value": trait.value}
            )
        except Exception as e:
            return GatewayResponse(text=f"❌ Error: {e}", success=False)
    
    def handle_learn_command(self, fact: str, chat_id: str) -> GatewayResponse:
        """
        Handle /learn <fact> - Explicitly teach IRA something new.
        
        Examples:
        - /learn PF1-C-1200-800 lead time is 12 weeks
        - /learn ABC Corp prefers email contact
        """
        try:
            sys.path.insert(0, str(BRAIN_DIR))
            from feedback_learner import teach_ira
            
            # Extract keywords from the fact
            import re
            keywords = []
            
            # Extract machine models
            models = re.findall(r'(PF1[-\s]?[A-Z][-\s]?\d+[-\s]?\d*|AM[-\s]?[MVP]\d*)', fact, re.IGNORECASE)
            keywords.extend([m.upper() for m in models])
            
            # Extract important words
            important = re.findall(r'\b(price|lead time|delivery|warranty|specification|contact|prefer)\b', fact.lower())
            keywords.extend(important)
            
            # Add any capitalized words (likely proper nouns)
            proper_nouns = re.findall(r'\b([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)?)\b', fact)
            keywords.extend([p for p in proper_nouns if p.lower() not in ['the', 'i', 'ira']])
            
            correction = teach_ira(
                correct_info=fact,
                context={"source": "telegram", "chat_id": chat_id},
                keywords=list(set(keywords))[:10],  # Dedupe and limit
                source=f"telegram:{chat_id}"
            )
            
            return GatewayResponse(
                text=f"""📚 **Learned!**

I've stored this knowledge:
> {fact}

**Keywords:** {', '.join(correction.keywords[:5]) if correction.keywords else 'N/A'}

I'll use this in future conversations!""",
                log_entry={"type": "learn", "fact": fact, "correction_id": correction.id}
            )
        except ImportError as e:
            return GatewayResponse(
                text=f"⚠️ Learning module not available: {e}",
                success=False
            )
        except Exception as e:
            return GatewayResponse(
                text=f"❌ Learning error: {e}",
                success=False
            )
    
    # =========================================================================
    # CONFLICT/DECISION COMMANDS
    # =========================================================================
    
    def handle_next(self, n: int = 1) -> GatewayResponse:
        """Send next N conflicts for review."""
        try:
            result = subprocess.run(
                [sys.executable, str(BRAIN_DIR / "truth_review.py"), "--ask-next", str(n)],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(PROJECT_ROOT)
            )
            
            output = result.stdout.strip()
            if result.returncode == 0:
                return GatewayResponse(
                    text=f"✓ Sent {n} conflict(s) for review.\n\n{output[:500]}",
                    log_entry={"type": "next", "count": n}
                )
            else:
                return GatewayResponse(
                    text=f"Error: {result.stderr or 'Unknown error'}",
                    success=False
                )
        except subprocess.TimeoutExpired:
            return GatewayResponse(text="❌ Command timed out", success=False)
        except Exception as e:
            return GatewayResponse(text=f"❌ Error: {e}", success=False)
    
    def handle_apply(self) -> GatewayResponse:
        """Apply resolved decisions."""
        try:
            result = subprocess.run(
                [sys.executable, str(BRAIN_DIR / "truth_review.py"), "--apply"],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(PROJECT_ROOT)
            )
            
            output = result.stdout.strip()
            if result.returncode == 0:
                return GatewayResponse(
                    text=f"✓ Applied decisions.\n\n{output[:500]}",
                    log_entry={"type": "apply"}
                )
            else:
                return GatewayResponse(
                    text=f"Error: {result.stderr or 'Unknown error'}",
                    success=False
                )
        except subprocess.TimeoutExpired:
            return GatewayResponse(text="❌ Command timed out", success=False)
        except Exception as e:
            return GatewayResponse(text=f"❌ Error: {e}", success=False)
    
    def handle_train(self, text: str) -> GatewayResponse:
        """
        Handle Brain Training Mode commands.
        
        Commands:
        - /train start: Load review_queue + KG cleanup queue
        - /train next [N]: Send next N questions
        - /train answer <id> <A|B|C>: Record decision
        - /train apply: Apply resolved decisions
        - /train status: Show progress
        """
        try:
            from brain_trainer import handle_train_command
            result = handle_train_command(text)
            return GatewayResponse(
                text=result,
                log_entry={"type": "train", "command": text}
            )
        except ImportError as e:
            return GatewayResponse(
                text=f"❌ Brain trainer module not available: {e}",
                success=False
            )
        except Exception as e:
            return GatewayResponse(
                text=f"❌ Training error: {e}",
                success=False
            )
    
    def handle_brief(self, topic: str) -> GatewayResponse:
        """Generate topic briefing using Qdrant + legacy SQLite."""
        context_parts = []

        # Primary: Qdrant retrieval (includes uploaded docs)
        try:
            qdrant_result = self.retrieve_knowledge(topic, limit=5)
            if qdrant_result and qdrant_result.get("citations"):
                for c in qdrant_result["citations"][:3]:
                    source = getattr(c, "source", "") or getattr(c, "citation", "") or "qdrant"
                    text = getattr(c, "text", str(c))[:500]
                    context_parts.append(f"[{source}]\n{text}")
        except Exception as e:
            logger.debug(f"Qdrant retrieval for brief failed: {e}")

        # Fallback: legacy SQLite FTS
        try:
            from query import search_chunks
            if KNOWLEDGE_DB.exists():
                results = search_chunks(KNOWLEDGE_DB, topic, k=5)
                for r in (results or [])[:3]:
                    context_parts.append(f"[{r.citation}]\n{r.text[:500]}")
        except (ImportError, Exception) as e:
            logger.debug(f"SQLite brief fallback: {e}")

        if not context_parts:
            return GatewayResponse(text=f"No knowledge found for: {topic}", success=False)

        try:
            context = "\n\n".join(context_parts)
            
            try:
                client = self._get_openai_client()
                
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are Ira, the Intelligent Revenue Assistant for Machinecraft. Generate a concise briefing (max 800 words) based on the provided knowledge. Be factual and cite sources when possible. Do not include any specific prices."},
                        {"role": "user", "content": f"Topic: {topic}\n\nRelevant Knowledge:\n{context}\n\nGenerate a briefing."}
                    ],
                    max_tokens=1000,
                    temperature=0.3
                )
                
                brief = response.choices[0].message.content.strip()
                
                return GatewayResponse(
                    text=f"📋 BRIEFING: {topic.upper()}\n\n{brief}",
                    log_entry={"type": "brief", "topic": topic}
                )
                
            except Exception as e:
                summary = f"📋 BRIEFING: {topic.upper()}\n\nSources:\n"
                for r in results[:3]:
                    summary += f"\n• {r.citation}\n  {r.text[:200]}...\n"
                
                return GatewayResponse(
                    text=summary,
                    log_entry={"type": "brief", "topic": topic, "ai_failed": True}
                )
                
        except Exception as e:
            return GatewayResponse(text=f"❌ Error: {e}", success=False)
    
    def handle_email_summary(self) -> GatewayResponse:
        """Preview brain summary email."""
        try:
            result = subprocess.run(
                [sys.executable, str(BRAIN_DIR / "send_brain_summary_email.py"), "--preview-only", "--to", "preview@internal"],
                capture_output=True,
                text=True,
                timeout=60,
                cwd=str(PROJECT_ROOT)
            )
            
            output = result.stdout.strip()
            
            preview_start = output.find("EMAIL PREVIEW")
            if preview_start > -1:
                preview = output[preview_start:preview_start+3500]
                return GatewayResponse(
                    text=f"📧 {preview}",
                    log_entry={"type": "email_preview"}
                )
            else:
                return GatewayResponse(
                    text=f"Email preview:\n{output[:2000]}",
                    log_entry={"type": "email_preview"}
                )
                
        except subprocess.TimeoutExpired:
            return GatewayResponse(text="❌ Email generation timed out", success=False)
        except Exception as e:
            return GatewayResponse(text=f"❌ Error: {e}", success=False)
    
    def get_approved_prices(self) -> Dict[str, Dict[str, float]]:
        """Get ONLY approved prices from pricebook."""
        pricebook = load_json_file(PRICEBOOK_FILE)
        if not pricebook:
            return {}
        
        approved = {}
        prices = pricebook.get("prices", [])
        
        if isinstance(prices, list):
            for entry in prices:
                if entry.get("approved") is True:
                    model = entry.get("model")
                    currency = entry.get("currency", "INR")
                    amount = entry.get("price") or entry.get("amount")
                    if model and amount:
                        if model not in approved:
                            approved[model] = {}
                        approved[model][currency] = amount
        
        elif isinstance(prices, dict):
            for canonical_id, currencies in prices.items():
                if not isinstance(currencies, dict):
                    continue
                for currency, data in currencies.items():
                    if not isinstance(data, dict):
                        continue
                    candidates = data.get("candidates", [])
                    for candidate in candidates:
                        if candidate.get("approved") is True:
                            if canonical_id not in approved:
                                approved[canonical_id] = {}
                            approved[canonical_id][currency] = candidate.get("amount")
                            break
        
        return approved
    
    def get_allowed_numbers(self, approved_prices: Dict) -> Set[float]:
        """Build set of numbers allowed in responses."""
        allowed = set(SAFE_NUMBERS)
        
        for model, currencies in approved_prices.items():
            for currency, amount in currencies.items():
                allowed.add(amount)
                if amount >= 100000:
                    allowed.add(amount / 100000)
                if amount >= 10000000:
                    allowed.add(amount / 10000000)
        
        return allowed
    
    def check_numeric_safety(self, text: str, allowed_numbers: Set[float]) -> Tuple[bool, List[Dict]]:
        """Check if all numbers in text are in allowed set."""
        violations = []
        
        patterns = [
            r'[₹$€]\s*([\d,]+(?:\.\d+)?)',
            r'([\d,]+(?:\.\d+)?)\s*(?:Cr|Crore|L|Lakh|Lac|K)\b',
            r'([\d,]+(?:\.\d+)?)\s*(?:INR|USD|EUR)\b',
            r'\b(\d{4,})\b',
        ]
        
        for pattern in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                try:
                    num_str = match.group(1).replace(',', '')
                    num = float(num_str)
                    
                    if num < 1000:
                        continue
                    
                    is_allowed = False
                    for allowed in allowed_numbers:
                        if abs(num - allowed) < 0.01:
                            is_allowed = True
                            break
                        if allowed >= 100000 and abs(num - allowed/100000) < 0.01:
                            is_allowed = True
                            break
                    
                    if not is_allowed:
                        context_start = max(0, match.start() - 20)
                        context_end = min(len(text), match.end() + 20)
                        violations.append({
                            "number": num,
                            "context": text[context_start:context_end]
                        })
                except (ValueError, IndexError):
                    continue
        
        return len(violations) == 0, violations
    
    def classify_complexity(self, text: str) -> str:
        """Classify message complexity for model routing."""
        text_lower = text.lower()
        
        for keyword in HIGH_COMPLEXITY_KEYWORDS:
            if keyword in text_lower:
                return "HIGH"
        
        for keyword in MEDIUM_COMPLEXITY_KEYWORDS:
            if keyword in text_lower:
                return "MEDIUM"
        
        return "LOW"
    
    def retrieve_knowledge(
        self, 
        query: str, 
        limit: int = 8, 
        source_group: str = "business",
        include_doc_types: List[str] = None,
        exclude_doc_types: List[str] = None
    ) -> Dict:
        """
        Retrieve relevant chunks using Qdrant unified retrieval.
        
        Source Groups:
        - business: data/imports, data/pdf_docs, leads, brochures, catalogs (DEFAULT)
        - governance: docs/tech_specs, policies, rules
        
        Doc Types:
        - thermoforming_portfolio, thermoforming_quote_offer, thermoforming_inquiry (include for portfolio)
        - cnc_router_quote (exclude for portfolio queries unless CNC mentioned)
        
        Returns dict with citations and metadata for confidence scoring.
        Also updates agent state with last query timestamp.
        """
        result = {
            'citations': [],
            'business_count': 0,
            'governance_count': 0,
            'engine': 'qdrant',
            'total': 0,
            'doc_type_counts': {}
        }
        
        # Use Qdrant retriever (canonical retrieval path)
        try:
            sys.path.insert(0, str(BRAIN_DIR))
            from qdrant_retriever import retrieve as qdrant_retrieve
            
            retrieval_result = qdrant_retrieve(
                query, 
                top_k=limit, 
                source_group=source_group,
                include_doc_types=include_doc_types,
                exclude_doc_types=exclude_doc_types
            )
            
            result['engine'] = 'qdrant'
            
            # Get doc_type_counts from retrieval result
            if hasattr(retrieval_result, 'doc_type_counts'):
                result['doc_type_counts'] = dict(retrieval_result.doc_type_counts)
            
            for c in retrieval_result.citations:
                sg = getattr(c, 'source_group', 'business')
                doc_type = getattr(c, 'doc_type', 'unknown')
                
                if sg in ['governance', 'technical']:
                    result['governance_count'] += 1
                else:
                    result['business_count'] += 1
                
                result['citations'].append({
                    'text': c.text,
                    'citation': c.filename,
                    'score': getattr(c, 'score', 0.8),
                    'source_group': sg,
                    'doc_type': doc_type
                })
            
            result['total'] = len(result['citations'])
            
            # Update agent state with last query timestamp
            self._update_brain_query_timestamp()
            
            return result
            
        except Exception as e:
            logger.error(f"Qdrant retrieval error: {e}")
            # Return empty result - no fallback to deprecated FTS5
            return result
    
    def _generate_llm_only_response(self, text: str, chat_id: str = None) -> GatewayResponse:
        """Generate response using LLM only when databases are unavailable."""
        try:
            client = self._get_openai_client()
            
            system_prompt = """You are Ira, the Intelligent Revenue Assistant for Machinecraft Technologies (India).
Machinecraft is a thermoforming machine manufacturer since 1976.

ABOUT MACHINECRAFT:
- Located in India, exports worldwide
- Specializes in thermoforming machines for various industries
- Main product lines: PF1 Series (single station), AM Series (twin sheet)

PF1 SERIES (Single Station Thermoforming):
- PF1-M: Medium size, servo or pneumatic drive, forming areas from 600x400mm to 1500x1000mm
- PF1-X: Large format for automotive, HDPE applications, forming areas up to 3500x2500mm
- Applications: Car mats, interior trim, refrigerator liners, bathtubs, automotive parts

KNOWN EUROPEAN CUSTOMERS (PF1 machines):
- Ridat (UK) - PF1-1015 (2021)
- Anatomic (Sweden) - PF1-810 (2022)
- Plastochim (France) - PF1-0808 (2022)
- Soehner (Germany) - PF1-1318 (2023)
- Thermic (Germany) - PF1-1616
- JoPlast (Denmark) - PF1-2015 (2024)
- Batelaan Kunststof (Netherlands)

EUROPEAN PROSPECTS interested in PF1:
- Imatex (Belgium), Stegoplast (Sweden), BD Plastindustri (Sweden)
- BT Plast Halden (Norway), World Panel (UK), Phase 3 Plastics (UK)
- Fritsch GmbH (Germany), Parat GmbH (Germany)

Be conversational, helpful, and specific. Answer like a knowledgeable sales assistant."""

            response = client.chat.completions.create(
                model="gpt-4o",  # Use better model for offline mode
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text}
                ],
                max_tokens=800,
                temperature=0.4
            )
            
            response_text = response.choices[0].message.content.strip()
            response_text += "\n\n⚠️ Database offline - using cached knowledge"
            
            self._save_conversation_turn(chat_id, text, response_text)
            
            return GatewayResponse(
                text=response_text,
                log_entry={"type": "llm_only_fallback", "reason": "database_offline"}
            )
            
        except Exception as e:
            return GatewayResponse(
                text=f"I'm having trouble right now. Please check if the databases are running.\n\nTry: `docker compose up -d`",
                success=False
            )
    
    def _get_last_bot_response(self, chat_id: str) -> str:
        """Get the last bot response for correction detection."""
        try:
            sys.path.insert(0, str(AGENT_DIR / "src" / "memory"))
            from memory_service import get_memory_service
            
            memory = get_memory_service()
            state = memory.load_state("telegram", chat_id)
            
            # Find last assistant message
            for msg in reversed(state.recent_messages):
                if hasattr(msg, 'role'):
                    role = msg.role
                elif isinstance(msg, dict):
                    role = msg.get('role', '')
                else:
                    continue
                    
                if role == "assistant":
                    if hasattr(msg, 'content'):
                        return msg.content
                    elif isinstance(msg, dict):
                        return msg.get('content', '')
            
            return ""
        except Exception as e:
            logger.error(f"Get last response error: {e}")
            return ""
    
    def _save_conversation_turn(self, chat_id: str, user_message: str, assistant_response: str):
        """Save conversation turn to unified memory for context continuity."""
        if not chat_id:
            return

        try:
            sys.path.insert(0, str(AGENT_DIR / "src" / "memory"))
            from memory_service import get_memory_service, MessageTurn

            memory = get_memory_service()
            state = memory.load_state("telegram", chat_id)
            
            # Add user message
            state.recent_messages.append(MessageTurn(
                role="user",
                content=user_message,
                channel="telegram"
            ))
            
            # Add assistant response
            state.recent_messages.append(MessageTurn(
                role="assistant",
                content=assistant_response[:1000],  # Truncate for storage
                channel="telegram"
            ))
            
            state.message_count += 1
            state.last_user_message = user_message
            
            # Keep only last N messages
            max_messages = 12
            if len(state.recent_messages) > max_messages:
                state.recent_messages = state.recent_messages[-max_messages:]
            
            memory.save_state(state)
            logger.debug(f"Saved conversation turn for chat {chat_id}, {len(state.recent_messages)} messages in context")
            
        except Exception as e:
            logger.error(f"Failed to save conversation turn: {e}")
    
    def handle_free_text(self, text: str, chat_id: str = None) -> GatewayResponse:
        """
        Handle free text query using UNIFIED generate_answer pipeline.
        
        All responses go through the unified generate_answer() which handles:
        - Deep retrieval for customer/business queries
        - Truth-first lookup for product queries
        - RAG retrieval for general queries
        
        Response path logged to Postgres: ira_memory.response_log
        """
        self._current_chat_id = chat_id
        request_start_time = time.time()
        
        # ===== START REQUEST TRACE =====
        trace_id = None
        if STRUCTURED_LOGGING_AVAILABLE:
            trace_id = start_trace(
                channel="telegram",
                user_id=chat_id or "unknown",
                message_preview=text[:50]
            )
            log_event("gateway", "request_started", {
                "message_length": len(text),
                "chat_id": chat_id[:8] if chat_id else ""
            })
        
        # ===== CHECK FOR CORRECTIONS (Learning Feedback Loop) =====
        # Detect if user is correcting IRA's previous response
        if FEEDBACK_LEARNER_AVAILABLE:
            try:
                # Get IRA's last response for context
                ira_previous = ""
                if hasattr(self, '_last_response'):
                    ira_previous = self._last_response
                
                correction = process_correction(
                    user_message=text,
                    ira_previous=ira_previous,
                    context={"chat_id": chat_id},
                    source=chat_id or "telegram",
                    channel="telegram"
                )
                if correction:
                    if STRUCTURED_LOGGING_AVAILABLE:
                        log_event("learning", "correction_detected", {
                            "correction_id": correction.id,
                            "type": correction.correction_type.value
                        })
            except Exception as learn_err:
                if STRUCTURED_LOGGING_AVAILABLE:
                    log_error("learning", learn_err, {"phase": "correction_detection"})
        
        # ===== FEEDBACK DETECTION (Positive / Negative) =====
        try:
            from openclaw.agents.ira.src.brain.feedback_handler import (
                detect_feedback, handle_positive_feedback, handle_negative_feedback
            )
            feedback_type, feedback_confidence = detect_feedback(text)
            if feedback_type and feedback_confidence > 0.5:
                _prev_response = getattr(self, '_last_response', '') or ''
                _gen_path = getattr(self, '_last_generation_path', '') or ''
                if feedback_type == "positive":
                    ack = handle_positive_feedback(text, _prev_response, _gen_path, chat_id or "")
                else:
                    ack = handle_negative_feedback(text, _prev_response, _gen_path, chat_id or "")
                logger.info(f"[FEEDBACK] {feedback_type} (confidence={feedback_confidence:.2f})")
                return GatewayResponse(text=ack, log_entry={
                    "type": f"feedback_{feedback_type}",
                    "confidence": feedback_confidence,
                })
        except ImportError as _fb_err:
            logger.debug(f"Feedback handler not available: {_fb_err}")
        except Exception as _fb_err:
            logger.warning(f"Feedback detection error (non-fatal): {_fb_err}")
        
        # ===== UNIFIED RESPONSE GENERATION =====
        try:
            sys.path.insert(0, str(BRAIN_DIR))
            from generate_answer import generate_answer, ContextPack, ResponseMode, ConfidenceLevel
            UNIFIED_AVAILABLE = True
        except ImportError as e:
            logger.warning(f"UNIFIED generate_answer not available: {e}")
            UNIFIED_AVAILABLE = False
        
        if UNIFIED_AVAILABLE:
            # ===== PHASE 1: WIRE THE MEMORY SERVICE =====
            # Get full conversation context from memory service
            try:
                from memory_service import get_memory_service
                memory = get_memory_service()
                full_context = memory.get_context_pack("telegram", chat_id or "", text)
            except ImportError as mem_err:
                logger.warning(f"Memory service not available: {mem_err}")
                full_context = None
            except Exception as mem_err:
                logger.error(f"Memory service error: {mem_err}")
                full_context = None
            
            # ===== PHASE 1.5: INTERNAL USER DETECTION =====
            # Derive is_internal from chat_id and identity email domain
            if full_context and not full_context.is_internal:
                _authorized_chat = os.environ.get("TELEGRAM_CHAT_ID", "")
                _is_internal = False
                if chat_id and _authorized_chat and str(chat_id) == str(_authorized_chat):
                    _is_internal = True
                if not _is_internal and full_context.identity:
                    _email = (full_context.identity.get("email") or "").lower()
                    if _email and any(_email.endswith(d) for d in ["machinecraft.org", "machinecraft.com", "machinecraft.in"]):
                        _is_internal = True
                if _is_internal:
                    full_context.is_internal = True
                    logger.debug(f"Internal user detected for chat {str(chat_id)[:8]}")
            
            # ===== PHASE 2: COREFERENCE RESOLUTION =====
            # Resolve pronouns like "it", "that machine" to specific entities
            actual_intent = text
            coreference_subs = []
            try:
                from coreference import CoreferenceResolver
                resolver = CoreferenceResolver()
                coref_context = {
                    "key_entities": full_context.key_entities if full_context else {},
                    "recent_messages": full_context.recent_messages if full_context else []
                }
                resolved = resolver.resolve(text, coref_context)
                if resolved.confidence > 0.7 and resolved.substitutions:
                    actual_intent = resolved.resolved
                    coreference_subs = resolved.substitutions
                    logger.debug(f"Coreference: '{text}' → '{actual_intent}'")
            except ImportError:
                pass  # Coreference module not available
            except Exception as coref_err:
                logger.warning(f"Coreference error (non-fatal): {coref_err}")
            
            # ===== PHASE 2.4: AUTO IDENTITY LINKING =====
            # Detect email addresses in user messages for cross-channel linking
            if full_context:
                try:
                    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
                    found_emails = re.findall(email_pattern, text)
                    
                    if found_emails:
                        from memory_service import get_memory_service
                        memory = get_memory_service()
                        
                        for email in found_emails:
                            email_lower = email.lower()
                            # Link this telegram chat to the email address
                            memory.link_identities(
                                channel1="telegram",
                                id1=chat_id or "",
                                channel2="email",
                                id2=email_lower,
                                confidence=0.9  # High confidence - user explicitly mentioned it
                            )
                            logger.info(f"Auto-linked: telegram:{chat_id[:8]}... ↔ email:{email_lower}")
                except ImportError:
                    pass
                except Exception as link_err:
                    logger.warning(f"Auto identity linking error (non-fatal): {link_err}")
            
            # ===== PHASE 2.4.5: CROSS-CHANNEL CONTEXT =====
            # Get recent email conversations with this contact to provide context
            cross_channel_context_str = ""
            cross_channel_data = None
            try:
                sys.path.insert(0, str(AGENT_DIR / "src" / "conversation"))
                from cross_channel_context import get_cross_channel_context
                
                cross_channel_data = get_cross_channel_context(
                    channel="telegram",
                    identifier=chat_id or "",
                    include_email=True,
                    include_telegram=False  # Don't include telegram - we already have that context
                )
                
                if cross_channel_data and cross_channel_data.email_threads:
                    cross_channel_context_str = cross_channel_data.to_context_string()
                    logger.info(f"Cross-channel: {len(cross_channel_data.email_threads)} email threads, "
                              f"topics: {cross_channel_data.topics_discussed[:3]}")
                    
                    if STRUCTURED_LOGGING_AVAILABLE:
                        log_event("cross_channel", "context_loaded", {
                            "email_threads": len(cross_channel_data.email_threads),
                            "topics": cross_channel_data.topics_discussed[:5],
                            "contact_name": cross_channel_data.contact_name or "",
                        })
            except ImportError as xc_err:
                logger.debug(f"Cross-channel context not available: {xc_err}")
            except Exception as xc_err:
                logger.warning(f"Cross-channel context error (non-fatal): {xc_err}")
            
            # ===== PHASE 2.5-2.6.6: UNIFIED BRAIN PROCESSING =====
            # Uses BrainOrchestrator to coordinate all cognitive functions:
            # - Memory Trigger (when to retrieve)
            # - Memory Retrieval (semantic memories)
            # - Episodic Retrieval (temporal context - PREVIOUSLY MISSING!)
            # - Procedural Matching (how-to guidance - PREVIOUSLY MISSING!)
            # - Memory Weaver (format for prompt)
            # - Memory Reasoning (inner monologue)
            # - Meta-cognition (knowledge state)
            # - Attention Filtering (working memory limits)
            # - Conflict Detection (queue for resolution)
            
            user_memories = []
            entity_memories = []
            user_identity_id = None
            memory_guidance = {}
            reasoning_context = ""
            metacognitive_guidance = ""
            episodic_context = ""
            procedure_guidance = ""
            brain_state = None
            
            # Get identity ID from context
            if full_context and full_context.identity:
                user_identity_id = full_context.identity.get("identity_id")
            
            # Early entity extraction so brain orchestrator and memory trigger
            # can use extracted_entities (was previously defined only after response)
            extracted_entities = {}
            try:
                from entity_extractor import EntityExtractor
                extractor = EntityExtractor()
                entities = extractor.extract(text)
                extracted_entities = entities.to_dict()
            except ImportError:
                pass
            except Exception:
                pass
            
            # Build RAG context for the generator (supplements brain retrieval)
            source_group = "business"
            policy_keywords = ['policy', 'rule', 'compliance', 'standard', 'regulation']
            if any(kw in text.lower() for kw in policy_keywords):
                source_group = "all"
            
            # Pre-fetch RAG retrieval for context
            retrieval = self.retrieve_knowledge(actual_intent, limit=10, source_group=source_group)
            knowledge_chunks = retrieval['citations']
            
            # Convert to ContextPack format with RAG chunks
            rag_chunks = []
            for c in knowledge_chunks[:8]:
                rag_chunks.append({
                    "text": c.get('text', '')[:500],
                    "filename": c.get('citation', 'unknown'),
                    "page": c.get('page'),
                    "source_group": c.get('source_group', 'business'),
                    "doc_type": c.get('doc_type', ''),
                    "score": c.get('score', 0.5)
                })
            
            # Use Brain Orchestrator if available (unified cognitive pipeline)
            if BRAIN_ORCHESTRATOR_AVAILABLE and user_identity_id:
                try:
                    brain = get_brain()
                    brain_state = brain.process(
                        message=text,
                        identity_id=user_identity_id,
                        context={
                            "mode": full_context.current_mode if full_context else "general",
                            "intent": actual_intent,
                            "entities": extracted_entities.get("companies", []) + extracted_entities.get("people", []),
                            "recent_messages": full_context.recent_messages if full_context else [],
                            "rag_chunks": rag_chunks,
                        },
                        channel="telegram"
                    )
                    
                    # Extract results from brain state
                    user_memories = brain_state.user_memories
                    entity_memories = brain_state.entity_memories
                    memory_guidance = brain_state.memory_guidance
                    reasoning_context = brain_state.reasoning_context
                    metacognitive_guidance = brain_state.metacognitive_guidance
                    episodic_context = brain_state.episodic_context
                    procedure_guidance = brain_state.procedure_guidance
                    
                    # Log brain processing results
                    total_ms = brain_state.timings.get("total", 0)
                    logger.debug(f"Brain processing: {brain_state.phase.value} ({total_ms:.0f}ms)")
                    if brain_state.episodes_retrieved:
                        logger.debug(f"Episodic: {brain_state.episodes_retrieved} episodes retrieved")
                    if brain_state.matched_procedure:
                        logger.debug(f"Procedure matched: {brain_state.matched_procedure.name}")
                    if brain_state.items_filtered:
                        logger.debug(f"Attention: filtered {brain_state.items_filtered} low-priority items")
                    if brain_state.errors:
                        for err in brain_state.errors:
                            logger.error(f"Brain error: {err}")
                            
                except Exception as brain_err:
                    logger.warning(f"Brain orchestrator error (falling back): {brain_err}")
                    import traceback
                    traceback.print_exc()
            
            # Fallback to individual modules if Brain Orchestrator not available/failed
            if not brain_state and PERSISTENT_MEMORY_AVAILABLE and user_identity_id:
                try:
                    pm = get_persistent_memory()
                    should_retrieve = True
                    retrieval_config = {"user_memory_limit": 5, "entity_memory_limit": 5, "min_relevance": 0.3}
                    
                    if MEMORY_TRIGGER_AVAILABLE:
                        trigger_context = {
                            "is_returning_user": user_identity_id is not None,
                            "has_identity": user_identity_id is not None,
                            "entities_mentioned": extracted_entities.get("companies", []) + extracted_entities.get("people", [])
                        }
                        should_retrieve, retrieval_config = should_retrieve_memory(text, chat_id, trigger_context)
                    
                    if should_retrieve:
                        user_memories = pm.retrieve_for_prompt(
                            identity_id=user_identity_id, query=actual_intent,
                            limit=retrieval_config.get("user_memory_limit", 5),
                            min_relevance=retrieval_config.get("min_relevance", 0.3)
                        )
                        entity_memories = pm.retrieve_entity_memories(query=actual_intent, limit=retrieval_config.get("entity_memory_limit", 5))
                        if user_memories:
                            logger.debug(f"Retrieved {len(user_memories)} user memories (fallback)")
                except Exception as pm_err:
                    logger.warning(f"Memory retrieval error (non-fatal): {pm_err}")
            
            # Fallback weaving if brain not used
            if not brain_state and MEMORY_WEAVER_AVAILABLE and (user_memories or entity_memories):
                try:
                    weaver = get_memory_weaver()
                    woven = weaver.weave(user_memories=user_memories, entity_memories=entity_memories,
                                         message=text, message_intent=actual_intent,
                                         mode=full_context.current_mode if full_context else None)
                    memory_guidance = weaver.format_for_prompt(woven)
                except Exception as weave_err:
                    logger.warning(f"Memory weaver error (non-fatal): {weave_err}")
            
            # Fallback reasoning if brain not used
            if not brain_state and MEMORY_REASONING_AVAILABLE and (user_memories or entity_memories):
                try:
                    trace = reason_with_memories(message=text, user_memories=user_memories, entity_memories=entity_memories,
                                                  context={"current_mode": full_context.current_mode if full_context else "general"})
                    if trace.inner_monologue:
                        reasoning_context = trace.to_prompt_context()
                except Exception as reason_err:
                    logger.warning(f"Memory reasoning error (non-fatal): {reason_err}")
            
            # ===== MEM0: SEMANTIC MEMORY RETRIEVAL =====
            # Get relevant memories from Mem0 (modern AI memory layer)
            mem0_context = ""
            if MEM0_AVAILABLE:
                try:
                    mem0_svc = _get_mem0()
                    if mem0_svc:
                        mem0_context = mem0_svc.get_relevant_context(
                            query=actual_intent,
                            user_id=user_identity_id or chat_id or "unknown",
                            limit=5,
                        )
                        if mem0_context:
                            logger.debug("Mem0: Retrieved relevant context for query")
                except Exception as mem0_err:
                    logger.warning(f"Mem0 retrieval error (non-fatal): {mem0_err}")
            
            # Fallback meta-cognition if brain not used
            if not brain_state and METACOGNITION_AVAILABLE:
                try:
                    knowledge_assessment = assess_knowledge(query=actual_intent, user_memories=user_memories,
                                                            entity_memories=entity_memories, rag_chunks=rag_chunks)
                    if knowledge_assessment.state != KnowledgeState.KNOW_VERIFIED:
                        from metacognition import get_metacognition
                        mc = get_metacognition()
                        metacognitive_guidance = mc.get_metacognitive_guidance(knowledge_assessment)
                except Exception as mc_err:
                    logger.warning(f"Meta-cognition error (non-fatal): {mc_err}")

            # ===== BUILD FULL CONTEXT PACK WITH CONVERSATION HISTORY =====
            if full_context:
                context_pack = {
                    # Conversation history (NEW - enables multi-turn)
                    "recent_messages": full_context.recent_messages,
                    "rolling_summary": full_context.rolling_summary,
                    "open_questions": full_context.open_questions,
                    "key_entities": full_context.key_entities,
                    
                    # RAG and KG facts
                    "rag_chunks": rag_chunks,
                    "kg_facts": full_context.kg_facts,
                    
                    # Identity and state
                    "identity": full_context.identity,
                    "is_internal": full_context.is_internal,
                    "thread_id": chat_id or "",
                    "current_mode": full_context.current_mode,
                    "current_stage": full_context.current_stage,
                    
                    # Persistent memories (ChatGPT-style)
                    "user_memories": [m.to_dict() for m in user_memories] if user_memories else [],
                    "entity_memories": [m.to_dict() for m in entity_memories] if entity_memories else [],
                    
                    # Memory Weaver guidance (structured prompt injection)
                    "memory_guidance": memory_guidance,
                    
                    # Memory Reasoning trace (inner monologue)
                    "reasoning_context": reasoning_context,
                    
                    # Meta-cognitive guidance (knowledge state assessment)
                    "metacognitive_guidance": metacognitive_guidance,
                    
                    # Episodic memory context (NEW - what happened before)
                    "episodic_context": episodic_context,
                    
                    # Procedural guidance (NEW - how to do things)
                    "procedure_guidance": procedure_guidance,
                    
                    # Mem0 context (modern AI memory - what I remember about you)
                    "mem0_context": mem0_context,
                    
                    # Brain state reference for feedback (if available)
                    "brain_state": brain_state,
                    
                    # Cross-channel context (email conversations with this contact)
                    "cross_channel_context": cross_channel_context_str,
                    "cross_channel_data": {
                        "email_threads": len(cross_channel_data.email_threads) if cross_channel_data else 0,
                        "topics": cross_channel_data.topics_discussed if cross_channel_data else [],
                        "contact_name": cross_channel_data.contact_name if cross_channel_data else None,
                        "contact_company": cross_channel_data.contact_company if cross_channel_data else None,
                    } if cross_channel_data else {},
                }
            else:
                # Fallback: minimal context without memory
                context_pack = {
                    "rag_chunks": rag_chunks,
                    "is_internal": True,
                    "thread_id": chat_id or "",
                    "user_memories": [],
                    "entity_memories": [],
                    "memory_guidance": {},
                    "reasoning_context": "",
                    "metacognitive_guidance": "",
                    "episodic_context": "",
                    "procedure_guidance": "",
                    "mem0_context": mem0_context,
                    "cross_channel_context": cross_channel_context_str,
                }
            
            # ===== PHASE 2.7: REPLIKA-INSPIRED CONVERSATIONAL ENHANCEMENT =====
            # Process through emotional intelligence + relationship memory + quality tracking
            conversational_enhancement = None
            conv_enhancer = get_conversational_enhancer()
            if conv_enhancer:
                try:
                    # Get user name from identity if available
                    user_name = ""
                    if full_context and full_context.identity:
                        user_name = full_context.identity.get("name", "")
                    
                    # Prepare memories for surfacing (combine user + entity memories)
                    memories_for_surfacing = []
                    if user_memories:
                        for m in user_memories:
                            memories_for_surfacing.append(m.to_dict() if hasattr(m, 'to_dict') else m)
                    if entity_memories:
                        for m in entity_memories:
                            memories_for_surfacing.append(m.to_dict() if hasattr(m, 'to_dict') else m)
                    
                    # Extract topics for pattern tracking
                    topics_detected = []
                    if full_context and full_context.key_entities:
                        for entity_type, entities in full_context.key_entities.items():
                            if isinstance(entities, list):
                                topics_detected.extend(entities[:3])
                            elif isinstance(entities, str):
                                topics_detected.append(entities)
                    
                    # Extract email from identity if available (for cross-channel linking)
                    user_email = None
                    if full_context and full_context.identity:
                        user_email = full_context.identity.get("email")
                    
                    # Process message through enhancer with extended data
                    conversational_enhancement = conv_enhancer.process_message(
                        contact_id=chat_id or "unknown",
                        message=text,
                        name=user_name,
                        channel="telegram",
                        additional_context={
                            "stage": full_context.current_stage if full_context else "new",
                            "mode": full_context.current_mode if full_context else "general",
                        },
                        memories=memories_for_surfacing,
                        topics=topics_detected,
                        telegram_id=str(chat_id) if chat_id else None,
                        email=user_email,
                    )
                    
                    # Add enhancement to context pack (extended with new fields)
                    context_pack["conversational_enhancement"] = {
                        "emotional_state": conversational_enhancement.emotional_reading.primary_state.value,
                        "emotional_intensity": conversational_enhancement.emotional_reading.intensity.value,
                        "warmth": conversational_enhancement.relationship_context.get("warmth", "stranger"),
                        "suggested_opener": conversational_enhancement.suggested_opener,
                        "prompt_additions": conversational_enhancement.prompt_additions,
                        "milestones": conversational_enhancement.milestones_to_celebrate,
                        # NEW: Extended enhancement fields
                        "memory_references": [m.to_dict() for m in conversational_enhancement.memory_references] if conversational_enhancement.memory_references else [],
                        "style_guidance": conversational_enhancement.style_profile.get_response_guidance() if conversational_enhancement.style_profile and conversational_enhancement.style_profile.messages_analyzed >= 3 else {},
                        "insights": [i.to_dict() for i in conversational_enhancement.insights[:2]] if conversational_enhancement.insights else [],
                        "conversation_health": conversational_enhancement.conversation_health.to_dict() if conversational_enhancement.conversation_health else None,
                    }
                    
                    # Enhanced logging
                    health_status = ""
                    if conversational_enhancement.conversation_health:
                        health_status = f", health={conversational_enhancement.conversation_health.health_score:.0f}"
                    
                    logger.debug(f"Conversational enhancement: "
                          f"emotion={conversational_enhancement.emotional_reading.primary_state.value}, "
                          f"warmth={conversational_enhancement.relationship_context.get('warmth', 'unknown')}"
                          f"{health_status}")
                    
                except Exception as conv_err:
                    logger.warning(f"Conversational enhancement error (non-fatal): {conv_err}")
            
            # =====================================================================
            # AGENTIC PIPELINE - Athena decides which tools to use
            # Uses LLM tool-calling loop: research, web search, memory, write, verify
            # Falls back to generate_answer if the agentic pipeline fails
            # =====================================================================
            _agent_used = False
            result = None
            try:
                import asyncio
                from openclaw.agents.ira.src.core.tool_orchestrator import process_with_tools

                # Build conversation history string for the agent
                _conv_history = ""
                if context_pack.get("recent_messages"):
                    for msg in context_pack["recent_messages"][-6:]:
                        role = msg.get("role", "user").upper()
                        content = msg.get("content", "")[:400]
                        _conv_history += f"{role}: {content}\n"

                _agent_context = {
                    "channel": "telegram",
                    "user_id": str(chat_id or "unknown"),
                    "is_internal": full_context.is_internal if full_context else False,
                    "conversation_history": _conv_history,
                    "mem0_context": mem0_context,
                    "identity": full_context.identity if full_context else None,
                    "_progress_callback": getattr(self, '_current_progress_callback', None),
                }

                _loop = asyncio.new_event_loop()
                try:
                    _agent_response = _loop.run_until_complete(
                        process_with_tools(
                            message=actual_intent,
                            channel="telegram",
                            user_id=str(chat_id or "unknown"),
                            context=_agent_context,
                        )
                    )
                finally:
                    _loop.close()

                if _agent_response and len(_agent_response.strip()) > 10:
                    _agent_used = True
                    result = type('AgentResult', (), {
                        'text': _agent_response,
                        'mode': type('M', (), {'value': 'agent'})(),
                        'confidence': type('C', (), {'value': 'HIGH'})(),
                        'generation_path': "agentic_tool_orchestrator",
                        'clarifying_questions': [],
                        'citations': [],
                        'debug_info': {"pipeline": "agentic"},
                        'consolidated_knowledge_ids': [],
                    })()
                    logger.info(f"[AGENT] Response via agentic pipeline")
            except Exception as _agent_err:
                logger.warning(f"Agentic pipeline error (falling back to generate_answer): {_agent_err}")
                import traceback
                traceback.print_exc()

            # Fallback: generate_answer (brain pipeline) if agent didn't produce a result
            if not _agent_used:
                result = generate_answer(
                    intent=actual_intent,
                    context_pack=context_pack,
                    channel="telegram",
                    thread_id=chat_id or "",
                    use_deep_retrieval=True
                )
            
            logger.info(f"[RESPONSE] mode={result.mode.value}, "
                  f"confidence={result.confidence.value}, path={result.generation_path}")
            
            # =====================================================================
            # ADAPTIVE RETRIEVAL - If confidence is LOW, try learning from documents
            # =====================================================================
            adaptive_answer = None
            adaptive_metadata = {}
            
            if result.confidence.value == "LOW":
                try:
                    from adaptive_retrieval import adaptive_retrieve
                    adaptive_answer, adaptive_metadata = adaptive_retrieve(actual_intent)
                    
                    if adaptive_answer and adaptive_metadata.get("confidence", 0) > 0.5:
                        logger.info(f"[ADAPTIVE] Found answer: {adaptive_metadata.get('status')} from {adaptive_metadata.get('source', 'memory')}")
                        
                        # Replace the low-confidence response with the learned fact
                        result.text = adaptive_answer
                        result.confidence = ConfidenceLevel.HIGH
                        result.generation_path = f"adaptive_retrieval:{adaptive_metadata.get('status')}"
                        
                        # Add source attribution
                        if adaptive_metadata.get("source"):
                            result.text += f"\n\n_(Source: {adaptive_metadata.get('source')})_"
                except ImportError as e:
                    logger.warning(f"[ADAPTIVE] Not available: {e}")
                except Exception as e:
                    logger.error(f"[ADAPTIVE] Error: {e}")
            
            # =====================================================================
            # NN RESEARCH FALLBACK - If still low confidence, trigger async research
            # =====================================================================
            nn_research_triggered = False
            if result.confidence.value == "LOW":
                try:
                    from nn_research import research_async
                    research_async(actual_intent, chat_id or "")
                    nn_research_triggered = True
                    logger.info("[NN_RESEARCH] Triggered async research for low-confidence query")
                except ImportError:
                    pass
                except Exception as e:
                    logger.debug(f"[NN_RESEARCH] Could not trigger: {e}")
            
            # Format response text
            response_text = result.text
            
            if nn_research_triggered:
                response_text += "\n\n_\U0001f50d I'm not fully confident in this answer, so I've started searching our documents for better data. I'll send you what I find shortly._"
            
            # Add clarifying question if available
            if result.clarifying_questions:
                response_text += f"\n\n**Question:** {result.clarifying_questions[0]}"
            
            # Price safety check - SKIP for internal users (founder/team can see all data)
            is_internal_user = full_context.is_internal if full_context else False
            safety_passed = True
            violations = []
            
            if not is_internal_user:
                approved_prices = self.get_approved_prices()
                allowed_numbers = self.get_allowed_numbers(approved_prices)
                safety_passed, violations = self.check_numeric_safety(response_text, allowed_numbers)
                
                if not safety_passed:
                    try:
                        from price_redactor import redact_prices
                        response_text = redact_prices(response_text, "[PRICE ON REQUEST]")
                    except ImportError:
                        response_text = re.sub(r'[₹$€]\s*[\d,]+(?:\.\d+)?', '[PRICE ON REQUEST]', response_text)
                    response_text += "\n\n⚠️ Some prices were redacted (not in approved list)."
            else:
                logger.info(f"[INTERNAL USER] Skipping price redaction for internal user")
            
            # Only show debug traces when explicitly enabled
            if SHOW_DEBUG:
                debug_trace = f"\n🔍 Debug: {result.generation_path} | mode:{result.mode.value} | conf:{result.confidence.value}"
                if coreference_subs:
                    debug_trace += f" | coref:{coreference_subs}"
                response_text += debug_trace
            
            # ===== UPDATE CONTEXT AFTER RESPONSE =====
            # extracted_entities was already populated before brain processing above
            
            # Update memory service with this conversation turn
            if full_context and memory:
                try:
                    memory.update_context_after_response(
                        channel="telegram",
                        identifier=chat_id or "",
                        user_message=text,
                        response_text=response_text,
                        mode=result.mode.value,
                        intent=actual_intent,
                        questions_asked=result.clarifying_questions or [],
                        entities_extracted=extracted_entities
                    )
                except Exception as update_err:
                    logger.warning(f"Context update error (non-fatal): {update_err}")
            
            # ===== EXTRACT PERSISTENT MEMORIES =====
            # Extract memorable facts from this conversation for future use
            if PERSISTENT_MEMORY_AVAILABLE and user_identity_id:
                try:
                    pm = get_persistent_memory()
                    created_memories = pm.extract_and_store(
                        identity_id=user_identity_id,
                        user_message=text,
                        assistant_response=response_text,
                        source_channel="telegram",
                        source_conversation_id=chat_id
                    )
                    total = sum(len(v) for v in created_memories.values())
                    if total > 0:
                        logger.debug(f"Extracted {total} new memories (user:{len(created_memories.get('user', []))}, entity:{len(created_memories.get('entity', []))}, correction:{len(created_memories.get('correction', []))})")
                except Exception as pm_err:
                    logger.warning(f"Persistent memory extraction error (non-fatal): {pm_err}")
            
            # ===== MEMORY CONTROLLER: INTELLIGENT MEMORY STORAGE =====
            # Use Memory Controller for intelligent routing, dedup, and conflict detection
            if MEMORY_CONTROLLER_AVAILABLE:
                try:
                    mem_result = remember_conversation(
                        user_message=text,
                        assistant_response=response_text,
                        user_id=user_identity_id or chat_id or "unknown",
                        channel="telegram",
                    )
                    
                    mem_count = len(mem_result.added) + len(mem_result.updated)
                    if mem_count > 0:
                        logger.debug(f"MemController: +{len(mem_result.added)} added, ~{len(mem_result.updated)} updated")
                    if mem_result.ignored > 0:
                        logger.debug(f"MemController: {mem_result.ignored} ignored (noise)")
                    if mem_result.conflicts > 0:
                        logger.debug(f"MemController: {mem_result.conflicts} conflicts queued")
                except Exception as mem_err:
                    logger.warning(f"MemController error (non-fatal): {mem_err}")
                    # Fallback to direct Mem0 if controller fails
                    if MEM0_AVAILABLE:
                        try:
                            mem0_svc = _get_mem0()
                            if mem0_svc:
                                mem0_svc.remember_from_message(
                                    user_message=text,
                                    assistant_response=response_text,
                                    user_id=user_identity_id or chat_id or "unknown",
                                    channel="telegram",
                                )
                        except Exception:
                            pass
            elif MEM0_AVAILABLE:
                # Fallback: Direct Mem0 if controller not available
                try:
                    mem0_svc = _get_mem0()
                    if mem0_svc:
                        mem0_result = mem0_svc.remember_from_message(
                            user_message=text,
                            assistant_response=response_text,
                            user_id=user_identity_id or chat_id or "unknown",
                            channel="telegram",
                        )
                        mem0_count = len(mem0_result.added) + len(mem0_result.updated)
                        if mem0_count > 0:
                            logger.debug(f"Mem0: +{len(mem0_result.added)} added, ~{len(mem0_result.updated)} updated")
                except Exception as mem0_err:
                    logger.warning(f"Mem0 error (non-fatal): {mem0_err}")
            
            # ===== PROACTIVE SUGGESTIONS =====
            # Generate proactive suggestions based on memories (for logging/future use)
            if PERSISTENT_MEMORY_AVAILABLE and user_identity_id and user_memories:
                try:
                    pm = get_persistent_memory()
                    suggestion = pm.get_proactive_suggestion(
                        identity_id=user_identity_id,
                        current_context=f"Conversation mode: {result.mode.value}",
                        recent_message=text[:500]
                    )
                    if suggestion:
                        suggestion_text = suggestion.get("suggestion", "")
                        suggestion_reason = suggestion.get("reason", "")
                        logger.debug(f"Proactive suggestion: {suggestion_text[:60]}...")
                        # Store for potential use in follow-up
                        self._last_proactive_suggestion = {
                            "suggestion": suggestion_text,
                            "reason": suggestion_reason,
                            "chat_id": chat_id,
                            "timestamp": datetime.now().isoformat()
                        }
                except Exception as ps_err:
                    logger.warning(f"Proactive suggestion error (non-fatal): {ps_err}")
            
            # ===== RECORD EPISODIC MEMORY =====
            # Record this conversation as an episode with temporal context
            if EPISODIC_MEMORY_AVAILABLE and user_identity_id:
                try:
                    em = get_episodic_memory()
                    
                    # Determine episode type based on mode/intent
                    ep_type = EpisodeType.CONVERSATION
                    if "quote" in actual_intent.lower() or "price" in actual_intent.lower():
                        ep_type = EpisodeType.INQUIRY
                    elif "problem" in actual_intent.lower() or "issue" in actual_intent.lower():
                        ep_type = EpisodeType.COMPLAINT
                    elif "follow" in actual_intent.lower():
                        ep_type = EpisodeType.FOLLOWUP
                    
                    # Map emotional state to valence
                    emotional_valence = EmotionalValence.NEUTRAL
                    if conversational_enhancement:
                        es = conversational_enhancement.emotional_state
                        if es in ["positive", "grateful"]:
                            emotional_valence = EmotionalValence.POSITIVE
                        elif es in ["frustrated", "stressed"]:
                            emotional_valence = EmotionalValence.NEGATIVE
                    
                    # Create summary
                    summary = f"User asked: {actual_intent[:100]}. "
                    if result.mode.value == "answer":
                        summary += f"Provided {result.confidence.value.lower()} confidence answer."
                    elif result.mode.value == "clarify":
                        summary += "Asked clarifying questions."
                    
                    # Record episode
                    episode = em.record_episode(
                        identity_id=user_identity_id,
                        channel="telegram",
                        summary=summary,
                        episode_type=ep_type,
                        key_topics=list(extracted_entities.get("topics", []))[:5] if extracted_entities else [],
                        entities_mentioned=list(extracted_entities.get("companies", []) + extracted_entities.get("products", []))[:5] if extracted_entities else [],
                        outcome=result.mode.value,
                        emotional_valence=emotional_valence,
                        user_emotional_state=conversational_enhancement.emotional_state if conversational_enhancement else "",
                        importance=0.6 if ep_type != EpisodeType.CONVERSATION else 0.4,
                    )
                    logger.debug(f"Recorded episode: {episode.id[:8]}... ({ep_type.value})")
                except Exception as ep_err:
                    logger.warning(f"Episodic memory error (non-fatal): {ep_err}")
            
            # ===== UPDATE CONVERSATIONAL ENHANCER STATE =====
            # Update relationship memory, emotional tracking, and conversation quality
            if conv_enhancer and conversational_enhancement:
                try:
                    # Determine if interaction was positive based on response confidence
                    was_positive = result.confidence.value in ["HIGH", "MEDIUM"]
                    
                    # Track which memories were surfaced (if any references made it to response)
                    memories_surfaced = []
                    if conversational_enhancement.memory_references:
                        for mem_ref in conversational_enhancement.memory_references:
                            if mem_ref.surfacing_text and mem_ref.surfacing_text.lower() in response_text.lower():
                                memories_surfaced.append(mem_ref.memory_id)
                    
                    # Score conversation quality and update all state
                    turn_quality = conv_enhancer.post_response_update(
                        contact_id=chat_id or "unknown",
                        message=text,
                        response=response_text,
                        was_positive=was_positive,
                        memories_surfaced=memories_surfaced,
                        response_time_ms=int(request_duration_ms) if 'request_duration_ms' in dir() else 0,
                        had_citations=bool(result.citations),
                    )
                    
                    # Log quality score
                    if turn_quality:
                        logger.debug(f"Turn quality: score={turn_quality.overall_score:.0f}, "
                              f"signals={len(turn_quality.signals)}")
                    
                except Exception as conv_update_err:
                    logger.warning(f"Conversational enhancer update error (non-fatal): {conv_update_err}")
            
            # Legacy save disabled -- update_context_after_response already saves the turn.
            # Duplicate saves were filling the 12-message window in 3 turns instead of 6.
            # self._save_conversation_turn(chat_id, text, response_text)
            
            # Store last response and generation path for feedback learning
            self._last_response = response_text
            self._last_generation_path = getattr(result, 'generation_path', '') or ''
            
            # Store consolidated knowledge IDs for quality tracking
            self._last_consolidated_ids = getattr(result, 'consolidated_knowledge_ids', []) or []
            
            # ===== SELF-HEALING: Record low-confidence gaps + auto-discover =====
            _conf_value = getattr(result.confidence, 'value', str(result.confidence))
            if _conf_value == "LOW":
                try:
                    from openclaw.agents.ira.src.memory.dream_neuroscience import KnowledgeGapDetector
                    gap_detector = KnowledgeGapDetector()
                    _topics = []
                    if extracted_entities:
                        _topics = (
                            extracted_entities.get("companies", []) +
                            extracted_entities.get("products", []) +
                            extracted_entities.get("topics", [])
                        )[:5]
                    if not _topics:
                        _topics = [actual_intent[:50]]
                    gap_detector.record_low_confidence_response(
                        query=actual_intent,
                        response=response_text[:200],
                        confidence=0.3,
                        topics=_topics,
                    )
                    logger.info(f"[SELF-HEALING] Recorded knowledge gap for: {actual_intent[:50]}")
                    
                    # Try auto-discovery in background
                    import threading
                    def _auto_discover():
                        try:
                            from openclaw.agents.ira.src.brain.knowledge_discovery import discover_on_the_fly
                            discovered = discover_on_the_fly(actual_intent, context={"search_results": rag_chunks})
                            if discovered:
                                logger.info(f"[SELF-HEALING] Auto-discovered knowledge: {discovered[:80]}")
                        except Exception as _de:
                            logger.debug(f"[SELF-HEALING] Auto-discovery failed: {_de}")
                    threading.Thread(target=_auto_discover, daemon=True).start()
                except Exception as _gap_err:
                    logger.debug(f"[SELF-HEALING] Gap recording failed: {_gap_err}")
            
            # ===== APPLY LEARNED CORRECTIONS =====
            # Enhance response with previously learned knowledge
            if FEEDBACK_LEARNER_AVAILABLE:
                try:
                    enhanced = enhance_response_with_learning(text, response_text)
                    if enhanced != response_text:
                        response_text = enhanced
                        if STRUCTURED_LOGGING_AVAILABLE:
                            log_event("learning", "corrections_applied")
                except Exception as learn_err:
                    if STRUCTURED_LOGGING_AVAILABLE:
                        log_error("learning", learn_err, {"phase": "response_enhancement"})
            
            # ===== END REQUEST TRACE =====
            request_duration_ms = (time.time() - request_start_time) * 1000
            if STRUCTURED_LOGGING_AVAILABLE:
                log_event("gateway", "response_generated", {
                    "mode": result.mode.value,
                    "confidence": result.confidence.value,
                    "path": result.generation_path,
                    "response_length": len(response_text)
                }, duration_ms=request_duration_ms)
                
                log_request(
                    channel="telegram",
                    user_id=chat_id or "",
                    message=text,
                    response=response_text,
                    duration_ms=request_duration_ms,
                    mode=result.mode.value,
                    confidence=result.confidence.value
                )
                
                end_trace(success=True, mode=result.mode.value)
            
            # ===== CHAT LOG: Log for dream learning =====
            try:
                from openclaw.agents.ira.src.conversation.chat_log import log_interaction
                log_interaction("telegram", chat_id, "user", text)
                log_interaction("telegram", chat_id, "assistant", response_text, metadata={
                    "mode": result.mode.value,
                    "confidence": result.confidence.value,
                    "duration_ms": round(request_duration_ms, 2),
                })
            except Exception as chat_log_err:
                logger.debug(f"Chat log error (non-fatal): {chat_log_err}")
            
            # ===== REFLECTION: Sophia learns from this interaction =====
            try:
                import asyncio
                from openclaw.agents.ira.src.agents.reflector.agent import reflect
                interaction_data = {
                    "user_message": text,
                    "response": response_text,
                    "intent": actual_intent,
                    "mode": result.mode.value,
                    "confidence": result.confidence.value,
                    "channel": "telegram",
                }
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.ensure_future(reflect(interaction_data))
                else:
                    loop.run_until_complete(reflect(interaction_data))
            except Exception as reflect_err:
                logger.debug(f"Reflection error (non-fatal): {reflect_err}")
            
            return GatewayResponse(
                text=response_text,
                log_entry={
                    "type": "unified_query",
                    "mode": result.mode.value,
                    "confidence": result.confidence.value,
                    "generation_path": result.generation_path,
                    "safety_passed": safety_passed,
                    "business_count": retrieval['business_count'],
                    "governance_count": retrieval['governance_count'],
                    "engine": retrieval['engine'],
                    "coreference_applied": len(coreference_subs) > 0,
                    "memory_wired": full_context is not None,
                    "duration_ms": round(request_duration_ms, 2),
                    "trace_id": trace_id
                }
            )
        
        # ===== FALLBACK: LLM-only response (database offline) =====
        logger.warning("Unified generator not available, using LLM fallback")
        return self._generate_llm_only_response(text, chat_id)
    
    def _handle_free_text_legacy(self, text: str, chat_id: str = None) -> GatewayResponse:
        """Legacy free text handler (deprecated - kept for rollback)."""
        # Legacy retrieval
        source_group = "business"
        retrieval = self.retrieve_knowledge(text, limit=10, source_group=source_group)
        knowledge_chunks = retrieval['citations']
        
        catalog = load_json_file(CATALOG_FILE) or {}
        approved_prices = self.get_approved_prices()
        
        business_chunks = [c for c in knowledge_chunks if c.get('source_group', 'business') != 'governance']
        use_chunks = business_chunks[:5] if business_chunks else knowledge_chunks[:5]
        
        knowledge_context = ""
        if use_chunks:
            knowledge_context = "RELEVANT KNOWLEDGE:\n"
            for chunk in use_chunks:
                knowledge_context += f"\n[{chunk.get('citation', 'unknown')}]\n{chunk.get('text', '')[:500]}\n"
        
        complexity = self.classify_complexity(text)
        model = MODEL_MAP[complexity]
        
        system_prompt = f"""You are Ira, the Intelligent Revenue Assistant for Machinecraft Technologies.
{knowledge_context}

Be helpful, professional, and concise. Do not make up specifications.
Respond concisely (max 500 words for Telegram)."""

        try:
            client = self._get_openai_client()
            
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text}
                ],
                max_tokens=800,
                temperature=0.7
            )
            
            response_text = response.choices[0].message.content.strip()
            
            if SHOW_DEBUG:
                response_text += f"\n\n⚠️ Debug: LEGACY_PATH | engine:{retrieval['engine']}"
            
            self._save_conversation_turn(chat_id, text, response_text)
            
            return GatewayResponse(
                text=response_text,
                log_entry={
                    "type": "legacy_query",
                    "generation_path": "LEGACY_FALLBACK",
                    "engine": retrieval['engine']
                }
            )
            
        except Exception as e:
            return self._generate_llm_only_response(text, chat_id)
    
    def handle_preview_batch(self, batch_id: int) -> GatewayResponse:
        """Preview campaign batch drafts."""
        try:
            sys.path.insert(0, str(AGENT_DIR / "src" / "campaign_engine"))
            from draft_batch import CampaignDrafter
            
            drafter = CampaignDrafter()
            preview = drafter.get_batch_preview(batch_id)
            
            return GatewayResponse(
                text=preview[:4000],
                log_entry={"type": "preview_batch", "batch_id": batch_id}
            )
        except Exception as e:
            return GatewayResponse(
                text=f"❌ Error previewing batch: {e}",
                success=False
            )
    
    def handle_approve_batch(self, batch_id: int) -> GatewayResponse:
        """Approve campaign batch for sending."""
        try:
            from db import get_crm_db
            db = get_crm_db()
            
            batch = db.get_campaign_batch(batch_id)
            if not batch:
                return GatewayResponse(
                    text=f"❌ Batch {batch_id} not found",
                    success=False
                )
            
            if batch.get('emails_drafted', 0) == 0:
                return GatewayResponse(
                    text=f"❌ Batch {batch_id} has no drafts",
                    success=False
                )
            
            self._pending_batch = {
                "batch_id": batch_id,
                "name": batch.get('name'),
                "emails_drafted": batch.get('emails_drafted', 0),
                "approved_at": datetime.now().isoformat()
            }
            
            return GatewayResponse(
                text=f"""📬 BATCH {batch_id} APPROVED

Name: {batch.get('name')}
Drafts: {batch.get('emails_drafted', 0)}

⚠️ Type 'SEND BATCH {batch_id}' to send all drafts.
Type CANCEL to abort.""",
                log_entry={"type": "approve_batch", "batch_id": batch_id}
            )
        except Exception as e:
            return GatewayResponse(
                text=f"❌ Error approving batch: {e}",
                success=False
            )
    
    def handle_send_batch(self, batch_id: int) -> GatewayResponse:
        """Send all drafts in approved batch."""
        if not hasattr(self, '_pending_batch') or not self._pending_batch:
            return GatewayResponse(
                text=f"❌ No approved batch pending. Use 'APPROVE BATCH {batch_id}' first.",
                success=False
            )
        
        if self._pending_batch.get('batch_id') != batch_id:
            return GatewayResponse(
                text=f"❌ Batch {batch_id} not approved. Approved batch is {self._pending_batch.get('batch_id')}.",
                success=False
            )
        
        try:
            service = self._get_gmail_service()
            from db import get_crm_db
            db = get_crm_db()
            
            cursor = db.conn.execute("""
                SELECT gmail_draft_id FROM sdr_emails_sent
                WHERE campaign_batch_id = ? AND gmail_draft_id IS NOT NULL
            """, (batch_id,))
            
            draft_ids = [row['gmail_draft_id'] for row in cursor.fetchall()]
            
            sent_count = 0
            failed_count = 0
            
            for draft_id in draft_ids:
                can_send, _ = db.check_rate_limit()
                if not can_send:
                    failed_count += len(draft_ids) - sent_count - failed_count
                    break
                
                try:
                    service.users().drafts().send(userId='me', body={"id": draft_id}).execute()
                    sent_count += 1
                except Exception as e:
                    failed_count += 1
            
            db.update_campaign_batch(
                batch_id,
                emails_sent=sent_count,
                status='completed' if failed_count == 0 else 'partial'
            )
            
            self._pending_batch = None
            
            return GatewayResponse(
                text=f"""✅ BATCH {batch_id} SENT

Sent: {sent_count}
Failed: {failed_count}
Total: {len(draft_ids)}""",
                log_entry={"type": "send_batch", "batch_id": batch_id, "sent": sent_count, "failed": failed_count}
            )
        except Exception as e:
            self._pending_batch = None
            return GatewayResponse(
                text=f"❌ Error sending batch: {e}",
                success=False
            )
    
    def route_message(self, message: TelegramMessage) -> GatewayResponse:
        """Route message to appropriate handler."""
        text = message.text.strip()
        text_upper = text.upper()
        
        # =====================================================================
        # CONVERSATIONAL HANDLER - Check for context-aware processing first
        # =====================================================================
        try:
            from conversational_handler import process_message_with_context, format_error_with_context
            
            conv_result = process_message_with_context(message.chat_id, text)
            if conv_result is not None:
                # Conversational handler handled the message
                return GatewayResponse(
                    text=conv_result.text,
                    success=conv_result.success,
                    log_entry=conv_result.log_entry
                )
        except ImportError as e:
            logger.warning(f"Conversational handler not available: {e}")
        except Exception as e:
            logger.error(f"Conversational handler error: {e}")
        
        # =====================================================================
        # CORRECTION LEARNING - Detect and learn from user corrections
        # =====================================================================
        try:
            sys.path.insert(0, str(BRAIN_DIR))
            from correction_learner import detect_and_learn, get_learner
            
            # Get previous bot response for context
            previous_response = self._get_last_bot_response(message.chat_id)
            
            # Detect if user is making a correction
            correction = detect_and_learn(
                user_message=text,
                previous_bot_response=previous_response,
                context={"query": text, "chat_id": message.chat_id}
            )
            
            if correction:
                logger.info(f"Learned correction: {correction.correction_type} - {correction.entity}")
                
                # Acknowledge the correction
                if correction.correction_type == "competitor":
                    return GatewayResponse(
                        text=f"Got it! I've noted that **{correction.entity}** is a competitor, not a prospect. I won't suggest them again.",
                        log_entry={"type": "correction_learned", "correction": correction.to_dict()}
                    )
                elif correction.correction_type == "customer":
                    return GatewayResponse(
                        text=f"Thanks for the correction! I've noted that **{correction.entity}** is already our customer. I'll exclude them from prospect lists.",
                        log_entry={"type": "correction_learned", "correction": correction.to_dict()}
                    )
                elif correction.correction_type == "fact":
                    # For fact corrections, acknowledge and continue
                    logger.info(f"Fact correction stored: {correction.corrected[:50]}")
        except ImportError as e:
            logger.warning(f"Correction learner not available: {e}")
        except Exception as e:
            logger.error(f"Correction learning error: {e}")
        
        # =====================================================================
        # COMMAND ALIASES - Natural language to command mapping
        # =====================================================================
        try:
            from stable_config import resolve_alias
            alias_command = resolve_alias(text)
            if alias_command:
                # Handle approval aliases specially
                if alias_command == "SEND_LAST_DRAFT":
                    return self.handle_send_draft()
                elif alias_command == "APPROVE_LAST":
                    # Check for pending items
                    pending = load_json_file(PENDING_DECISIONS_FILE) or []
                    if pending:
                        return GatewayResponse(
                            text="✓ Understood. Which item would you like to approve?",
                            log_entry={"type": "approval_clarification"}
                        )
                    return self.handle_send_draft()
                elif alias_command.startswith("/"):
                    # Route to command handler
                    text = alias_command
                    # Continue to standard routing with new text
        except ImportError:
            pass
        except Exception as e:
            logger.error(f"Alias resolution error: {e}")
        
        # =====================================================================
        # STANDARD ROUTING
        # =====================================================================
        
        # Multi-decision reply (e.g., "PF1-C B\nATF A\nPF1-X B")
        if self.is_multi_decision_reply(text):
            return self.handle_multi_decision_reply(text)
        
        # Single decision reply (A, B, or C alone)
        if text_upper in VALID_DECISION_ANSWERS:
            return self.handle_decision_reply(text_upper)
        
        preview_match = re.match(r'^PREVIEW\s+(\S+)$', text, re.IGNORECASE)
        if preview_match:
            return self.handle_preview_draft(preview_match.group(1))
        
        approve_match = re.match(r'^APPROVE\s+(\S+)$', text, re.IGNORECASE)
        if approve_match:
            return self.handle_approve_draft(approve_match.group(1))
        
        if text_upper == "SEND":
            return self.handle_send_draft()
        
        if text_upper == "CANCEL":
            return self.handle_cancel()
        
        if text.lower() == "/start":
            return self.handle_start()
        
        if text.lower() == "/menu":
            return self.handle_menu()
        
        if text.lower() == "/help":
            return self.handle_help()
        
        if text.lower() == "/status":
            return self.handle_status()
        
        if text.lower() == "/diag":
            return self.handle_diag()
        
        # =====================================================================
        # PERSISTENT MEMORY COMMANDS
        # =====================================================================
        
        if text.lower() == "/memories":
            return self.handle_memories_command(message.chat_id)
        
        # Natural language memory queries
        memory_query_patterns = [
            "what do you know about me",
            "what do you remember about me",
            "what have you learned about me",
            "show me my memories",
            "list my memories",
        ]
        if any(p in text.lower() for p in memory_query_patterns):
            return self.handle_memories_command(message.chat_id)
        
        # Handle "remember that..." explicit commands
        if PERSISTENT_MEMORY_AVAILABLE:
            remember_result = self._handle_remember_command(text, message.chat_id)
            if remember_result:
                return remember_result
            
            forget_result = self._handle_forget_command(text, message.chat_id)
            if forget_result:
                return forget_result
        
        # =====================================================================
        # MEMORY ANALYTICS COMMANDS
        # =====================================================================
        
        # /search_memory <query> - Search what IRA knows
        search_match = re.match(r'^/search_memory\s+(.+)$', text, re.IGNORECASE)
        if search_match:
            return self.handle_search_memory(search_match.group(1).strip())
        
        # /memory_stats - Show memory analytics
        if text.lower() in ["/memory_stats", "/mem_stats", "/brain_stats"]:
            return self.handle_memory_stats()
        
        # /export_memory - Export all knowledge to file
        if text.lower() == "/export_memory":
            return self.handle_export_memory()
        
        # /decay_memory - Apply memory decay (admin only)
        if text.lower() == "/decay_memory":
            return self.handle_decay_memory()
        
        # =====================================================================
        # CONFLICT RESOLUTION COMMANDS
        # =====================================================================
        
        # /conflicts - Show pending memory conflicts
        if text.lower() == "/conflicts":
            return self.handle_conflicts_command()
        
        # /resolve <id> <1|2|merge:text> - Resolve a specific conflict
        resolve_match = re.match(r'^/resolve\s+(.+)$', text, re.IGNORECASE)
        if resolve_match:
            return self.handle_resolve_command(resolve_match.group(1).strip())
        
        # /ingest <path> - Ingest a document into memory
        ingest_match = re.match(r'^/ingest\s+(.+)$', text, re.IGNORECASE)
        if ingest_match:
            return self.handle_ingest_command(ingest_match.group(1).strip())

        # /docs - List documents uploaded via Telegram
        if text_upper in ("/DOCS", "/DOCUMENTS", "/UPLOADS"):
            return self.handle_docs_command()

        # /deep_ingest [filename] - Deep re-process an uploaded document
        deep_ingest_match = re.match(r'^/deep_ingest\s*(.*)', text, re.IGNORECASE)
        if deep_ingest_match:
            return self.handle_deep_ingest(deep_ingest_match.group(1))

        # =====================================================================
        # METADATA INDEX COMMANDS
        # =====================================================================
        
        if text.lower() in ["/index", "/index status", "/index_status"]:
            return self._handle_index_status()
        
        if text.lower() in ["/index build", "/index_build", "/reindex"]:
            return self._handle_index_build()
        
        # =====================================================================
        # NN RESEARCH FEEDBACK COMMANDS
        # =====================================================================
        
        confirm_match = re.match(r'^/confirm\s+(\S+)', text, re.IGNORECASE)
        if confirm_match:
            return self._handle_research_feedback(confirm_match.group(1), True)
        
        reject_match = re.match(r'^/reject\s+(\S+)', text, re.IGNORECASE)
        if reject_match:
            return self._handle_research_feedback(reject_match.group(1), False)
        
        # =====================================================================
        # QUOTE GENERATION COMMANDS
        # =====================================================================
        
        # /quote <size> [variant] - Generate a quick quote
        quote_match = re.match(r'^/quote\s+(.+)$', text, re.IGNORECASE)
        if quote_match:
            return self.handle_quote_command(quote_match.group(1).strip())
        
        # Quick conflict responses: "1", "2", "merge: text"
        conflict_response = self._check_conflict_response(text)
        if conflict_response:
            return conflict_response
        
        # =====================================================================
        # HEALTH DIAGNOSTIC COMMAND
        # =====================================================================
        
        if text.lower() in ['/health', '/diagnostic', '/status_full']:
            return self._handle_health_command()
        
        # =====================================================================
        # PRICE CONFLICT COMMANDS
        # =====================================================================
        
        # /price_conflicts - Show pending price conflicts
        if text.lower() in ["/price_conflicts", "/priceconflicts", "/prices"]:
            return self.handle_price_conflicts_command()
        
        # /resolve_price <model> <price> - Resolve a price conflict
        resolve_price_match = re.match(r'^/resolve_price\s+(\S+)\s+(\d[\d,]*)', text, re.IGNORECASE)
        if resolve_price_match:
            model = resolve_price_match.group(1)
            price_str = resolve_price_match.group(2).replace(",", "")
            return self.handle_resolve_price_command(model, price_str)
        
        # Natural language: "PF1-C-3020: 85 lakh" or "PF1-C-3020 price is 8500000"
        price_resolve_match = re.match(r'^(PF1-[A-Z]-\d{4})[\s:]+(\d+)\s*(?:lakh|lac)?', text, re.IGNORECASE)
        if price_resolve_match:
            model = price_resolve_match.group(1).upper()
            price_str = price_resolve_match.group(2)
            # Convert lakh to actual number if needed
            price = int(price_str)
            if price < 1000:  # Likely in lakhs
                price = price * 100000
            return self.handle_resolve_price_command(model, str(price))
        
        # =====================================================================
        # RELATIONSHIP DASHBOARD COMMANDS
        # =====================================================================
        
        # /dashboard - Show relationship health overview
        if text.lower() == "/dashboard":
            return self.handle_dashboard_command()
        
        # /priorities - Show top contacts needing attention
        if text.lower() == "/priorities":
            return self.handle_priorities_command()
        
        # /at_risk - Show at-risk relationships
        if text.lower() in ["/at_risk", "/atrisk"]:
            return self.handle_at_risk_command()
        
        # /contact <name> - Show detail about a contact
        contact_match = re.match(r'^/contact\s+(.+)$', text, re.IGNORECASE)
        if contact_match:
            return self.handle_contact_detail_command(contact_match.group(1).strip())
        
        # Response feedback commands
        if text.lower() == "/good":
            return self.handle_good_command(message.chat_id)
        
        bad_match = re.match(r'^/bad(?:\s+(.*))?$', text, re.IGNORECASE)
        if bad_match:
            reason = bad_match.group(1) or ""
            return self.handle_bad_command(message.chat_id, reason.strip())
        
        if text.lower() == "/feedback":
            return self.handle_feedback_command(message.chat_id)
        
        if text.lower() in ["/knowledge_quality", "/kq"]:
            return self.handle_knowledge_quality_command()
        
        # Proactive outreach commands
        if text.lower() == "/outreach":
            return self.handle_outreach_command()
        
        approve_match = re.match(r'^/approve\s+(.+)$', text, re.IGNORECASE)
        if approve_match:
            return self.handle_approve_outreach_command(approve_match.group(1), message.chat_id)
        
        dismiss_match = re.match(r'^/dismiss\s+(.+)$', text, re.IGNORECASE)
        if dismiss_match:
            return self.handle_dismiss_outreach_command(dismiss_match.group(1))
        
        if text.lower() in ["/outreach_stats", "/outreach stats"]:
            return self.handle_outreach_stats_command()
        
        if text.lower() == "/personality":
            return self.handle_personality_command()
        
        boost_match = re.match(r'^/boost\s+(.+)$', text, re.IGNORECASE)
        if boost_match:
            return self.handle_boost_trait_command(boost_match.group(1))
        
        # /learn <fact> - Explicitly teach IRA something
        learn_match = re.match(r'^/learn\s+(.+)$', text, re.IGNORECASE)
        if learn_match:
            return self.handle_learn_command(learn_match.group(1).strip(), message.chat_id)
        
        # Failure logger commands: /fail, /fail last, /fail stats, /fixplan
        fail_match = re.match(r'^/(fail|fixplan)(?:\s+(.*))?$', text, re.IGNORECASE)
        if fail_match:
            return self.handle_fail_command(text)
        
        # Takeout email stats: /takeout status, /takeout stats, /takeout domains, etc.
        takeout_match = re.match(r'^/takeout(?:\s+(.*))?$', text, re.IGNORECASE)
        if takeout_match:
            return self.handle_takeout_command(text)
        
        next_match = re.match(r'^/next(?:\s+(\d+))?$', text, re.IGNORECASE)
        if next_match:
            n = int(next_match.group(1)) if next_match.group(1) else 1
            return self.handle_next(min(n, 10))
        
        if text.lower() == "/apply":
            return self.handle_apply()
        
        brief_match = re.match(r'^/brief\s+(.+)$', text, re.IGNORECASE)
        if brief_match:
            return self.handle_brief(brief_match.group(1).strip())
        
        if text.lower() == "/email summary":
            return self.handle_email_summary()
        
        # Batch campaign commands
        preview_batch_match = re.match(r'^PREVIEW\s+BATCH\s+(\d+)$', text, re.IGNORECASE)
        if preview_batch_match:
            return self.handle_preview_batch(int(preview_batch_match.group(1)))
        
        approve_batch_match = re.match(r'^APPROVE\s+BATCH\s+(\d+)$', text, re.IGNORECASE)
        if approve_batch_match:
            return self.handle_approve_batch(int(approve_batch_match.group(1)))
        
        send_batch_match = re.match(r'^SEND\s+BATCH\s+(\d+)$', text, re.IGNORECASE)
        if send_batch_match:
            return self.handle_send_batch(int(send_batch_match.group(1)))
        
        # Natural language teaching: /teach <facts>
        teach_match = re.match(r'^/teach\s+(.+)$', text, re.IGNORECASE | re.DOTALL)
        if teach_match:
            return self._handle_teach(teach_match.group(1).strip(), message.chat_id)
        
        # Brain Training Mode commands
        train_match = re.match(r'^/train(?:\s+(.*))?$', text, re.IGNORECASE)
        if train_match:
            return self.handle_train(text)
        
        # =====================================================================
        # DEEP DIVE - Conversational multi-topic research
        # =====================================================================
        
        deepdive_match = re.match(r'^/deepdive\s+(.+)$', text, re.IGNORECASE)
        if deepdive_match:
            return self._handle_deepdive_start(deepdive_match.group(1).strip(), message.chat_id)
        
        if text.lower() in ['/deepdive', '/deepdive_cancel', '/cancel_deepdive']:
            return self._handle_deepdive_cancel(message.chat_id)
        
        # Check if there's an active deep dive conversation
        try:
            from openclaw.agents.ira.src.brain.deep_dive import get_session
            active_dd = get_session(message.chat_id)
            if active_dd and active_dd.phase == "conversation":
                return self._handle_deepdive_reply(text, message.chat_id)
        except ImportError:
            pass
        
        # =====================================================================
        # DEEP THINKING COMMANDS
        # =====================================================================
        
        # /research or /deep <query> - Manus-style deep research mode
        research_match = re.match(r'^/(?:research|deep)\s+(.+)$', text, re.IGNORECASE)
        if research_match:
            return self.handle_research_command(research_match.group(1).strip(), message.chat_id)
        
        # /think <query> - Force deep thinking
        think_match = re.match(r'^/think\s+(.+)$', text, re.IGNORECASE)
        if think_match:
            return self.handle_think_command(think_match.group(1).strip(), message.chat_id)
        
        # /thinking or /research status - Show usage help
        if text.lower() in ['/thinking', '/think', '/research']:
            return GatewayResponse(
                text="🔍 *Research Commands*\n\n"
                     "`/research <query>` — Deep research on a topic\n"
                     "`/deepdive <topic>` — Conversational multi-topic research\n\n"
                     "Example: `/research PlastIndia 2025 leads`\n"
                     "Example: `/deepdive European market strategy 2026`",
                parse_mode="Markdown",
            )
        
        # /cancel_thinking - Cancel active thinking jobs
        if text.lower() == '/cancel_thinking':
            return self.handle_cancel_thinking(message.chat_id)
        
        # =====================================================================
        # EMAIL GENERATION COMMAND
        # =====================================================================
        
        # /email <recipient> [company] [name] [purpose]
        email_match = re.match(r'^/email\s+(.+)$', text, re.IGNORECASE)
        if email_match:
            return self.handle_email_command(email_match.group(1).strip(), message.chat_id)
        
        # =====================================================================
        # PLASTINDIA LEAD EMAIL DRAFTING
        # =====================================================================
        
        # /leads or "list leads" - Show Plastindia leads
        if text.lower() in ['/leads', '/plastindia', 'list leads', 'show leads']:
            return self.handle_leads_list()
        
        # /leads A or "list category A leads" - Show specific category
        leads_cat_match = re.match(r'^(?:/leads|list\s+leads?|show\s+leads?)\s+([A-F])$', text, re.IGNORECASE)
        if leads_cat_match:
            return self.handle_leads_list(leads_cat_match.group(1).upper())
        
        # "Draft email for [company]" or "/draft [company]"
        draft_lead_match = re.match(
            r'^(?:draft\s+(?:email\s+)?(?:for\s+)?|/draft\s+)(.+)$', 
            text, re.IGNORECASE
        )
        if draft_lead_match:
            return self.handle_lead_draft(draft_lead_match.group(1).strip())
        
        # =====================================================================
        # DEEP THINKING AUTO-DETECTION
        # Check if this query should use deep thinking (complex questions)
        # =====================================================================
        deep_result = self._try_deep_thinking(text, message.chat_id)
        if deep_result is not None:
            return deep_result
        
        # Natural language training detection
        nl_result = self.check_natural_language_training(text)
        if nl_result:
            return nl_result
        
        return self.handle_free_text(text, chat_id=message.chat_id)
    
    def check_natural_language_training(self, text: str) -> Optional[GatewayResponse]:
        """
        Check if text contains natural language training input.
        
        Handles:
        - "PF1-A is same as PF1-C" → creates alias question
        - "customer names are wrong" → starts cleanup workflow
        """
        try:
            from brain_trainer import handle_natural_language_training
            matched, response = handle_natural_language_training(text)
            if matched:
                return GatewayResponse(
                    text=response,
                    log_entry={"type": "train_nl", "input": text[:100]}
                )
        except ImportError:
            pass
        except Exception as e:
            logger.error(f"NL training error: {e}")
        
        return None
    
    # =========================================================================
    # HEALTH DIAGNOSTIC
    # =========================================================================
    
    def _handle_health_command(self) -> GatewayResponse:
        """Comprehensive self-diagnostic: services, memory, knowledge, agent scores, gaps."""
        lines = ["🏥 *Ira Health Diagnostic*\n"]
        
        # 1. Service status
        lines.append("*Services:*")
        services = {
            "Qdrant": lambda: __import__('requests').get(os.environ.get('QDRANT_URL', 'http://localhost:6333')).status_code == 200,
            "Mem0": lambda: bool(__import__('openclaw.agents.ira.src.memory.mem0_memory', fromlist=['get_mem0_service']).get_mem0_service()),
            "OpenAI": lambda: bool(os.environ.get('OPENAI_API_KEY')),
            "Voyage": lambda: bool(os.environ.get('VOYAGE_API_KEY')),
        }
        for name, check_fn in services.items():
            try:
                ok = check_fn()
                lines.append(f"  {'✅' if ok else '❌'} {name}")
            except Exception:
                lines.append(f"  ❌ {name}")
        
        # 2. Knowledge health
        try:
            from openclaw.agents.ira.src.brain.knowledge_health import run_health_check
            report = run_health_check()
            lines.append(f"\n*Knowledge Health:* {report.overall_score}/100")
            lines.append(f"  Checks passed: {report.checks_passed}")
            lines.append(f"  Checks failed: {report.checks_failed}")
            if report.issues:
                for issue in report.issues[:3]:
                    icon = "🔴" if issue.severity == "critical" else "🟡"
                    lines.append(f"  {icon} {issue.message[:60]}")
        except Exception as e:
            lines.append(f"\n*Knowledge Health:* unavailable ({e})")
        
        # 3. Knowledge gaps
        try:
            import json
            gaps_file = PROJECT_ROOT / "data" / "knowledge_gaps.json"
            if gaps_file.exists():
                gaps = json.loads(gaps_file.read_text())
                if isinstance(gaps, dict):
                    gap_count = len(gaps)
                elif isinstance(gaps, list):
                    gap_count = len(gaps)
                else:
                    gap_count = 0
                lines.append(f"\n*Knowledge Gaps:* {gap_count} detected")
            else:
                lines.append("\n*Knowledge Gaps:* none tracked yet")
        except Exception:
            lines.append("\n*Knowledge Gaps:* unavailable")
        
        # 4. Agent scores
        try:
            import json
            scores_file = PROJECT_ROOT / "openclaw" / "data" / "learned_lessons" / "agent_scores.json"
            if scores_file.exists():
                scores = json.loads(scores_file.read_text())
                lines.append("\n*Agent Scores:*")
                for agent, data in sorted(scores.items()):
                    score = data.get("score", 0)
                    s = data.get("successes", 0)
                    f = data.get("failures", 0)
                    bar = "█" * int(score * 10) + "░" * (10 - int(score * 10))
                    lines.append(f"  {agent}: {bar} {score:.2f} (+{s}/-{f})")
        except Exception:
            pass
        
        # 5. Recent errors
        try:
            import json
            from pathlib import Path
            errors_dir = PROJECT_ROOT / "data" / "logs"
            recent_errors = 0
            if errors_dir.exists():
                for f in sorted(errors_dir.glob("errors_*.jsonl"))[-1:]:
                    recent_errors = sum(1 for _ in f.read_text().splitlines() if _.strip())
            lines.append(f"\n*Recent Errors:* {recent_errors} in last log")
        except Exception:
            pass
        
        # 6. Memory stats
        try:
            from openclaw.agents.ira.src.memory.mem0_memory import get_mem0_service
            mem0 = get_mem0_service()
            total = 0
            for uid in ["machinecraft_customers", "machinecraft_knowledge", "machinecraft_pricing", "machinecraft_general"]:
                memories = mem0.get_all(user_id=uid, limit=1)
                if hasattr(memories, '__len__'):
                    pass  # Can't get count from search, just show categories
            lines.append(f"\n*Memory Categories:* customers, knowledge, pricing, processes, general")
        except Exception:
            pass
        
        # 7. Dream status
        try:
            import json
            dream_log = PROJECT_ROOT / "logs" / f"dream_{datetime.now().strftime('%Y-%m-%d')}.log"
            if dream_log.exists():
                lines.append(f"\n*Last Dream:* today")
            else:
                # Find most recent
                dream_logs = sorted((PROJECT_ROOT / "logs").glob("dream_*.log"))
                if dream_logs:
                    last = dream_logs[-1].stem.replace("dream_", "")
                    lines.append(f"\n*Last Dream:* {last}")
                else:
                    lines.append(f"\n*Last Dream:* never")
        except Exception:
            pass
        
        return GatewayResponse(
            text="\n".join(lines),
            parse_mode="Markdown",
            log_entry={"type": "health_diagnostic"},
        )
    
    # =========================================================================
    # TEACH MODE - Natural language fact ingestion
    # =========================================================================
    
    def _handle_teach(self, facts_text: str, chat_id: str) -> GatewayResponse:
        """Ingest natural language facts into Ira's knowledge.
        
        Extracts structured facts, stores in Mem0, and optionally updates
        hard rules or truth hints if the fact is a rule change.
        
        Usage: /teach FRIMO is no longer actively selling Machinecraft machines in Europe.
               They were our agent but the partnership has cooled off.
        """
        if len(facts_text.strip()) < 10:
            return GatewayResponse(
                text="Usage: `/teach <facts in natural language>`\n\n"
                     "Examples:\n"
                     "• `/teach FRIMO partnership is no longer active for European sales`\n"
                     "• `/teach Dezet in Netherlands ordered PF1-X-1310 in 2025`\n"
                     "• `/teach Our standard lead time is now 14-18 weeks`\n\n"
                     "I'll extract the facts, store them in memory, and use them immediately.",
                parse_mode="Markdown",
            )
        
        try:
            import openai
            api_key = os.environ.get("OPENAI_API_KEY", "")
            client = openai.OpenAI(api_key=api_key)
            
            # Step 1: Extract structured facts
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": (
                        "Extract specific facts from the user's teaching input. "
                        "Output each fact as a standalone declarative statement, one per line.\n\n"
                        "For each fact, also output a CATEGORY on the same line after a | separator.\n"
                        "Categories: CUSTOMER, PARTNER, PRODUCT, PRICING, PROCESS, RULE, GENERAL\n\n"
                        "Example input: 'FRIMO is no longer selling our machines in Europe. "
                        "They were our agent but partnership cooled off.'\n"
                        "Example output:\n"
                        "FRIMO is no longer actively selling Machinecraft machines in Europe | PARTNER\n"
                        "FRIMO partnership with Machinecraft has cooled off | PARTNER\n"
                        "FRIMO should not be referred to as an active sales agent | RULE\n\n"
                        "Be precise. Preserve names, numbers, dates exactly as given."
                    )},
                    {"role": "user", "content": facts_text},
                ],
                max_tokens=500,
                temperature=0.1,
            )
            
            extracted = resp.choices[0].message.content.strip()
            facts = []
            for line in extracted.split("\n"):
                line = line.strip()
                if not line or len(line) < 5:
                    continue
                parts = line.rsplit("|", 1)
                fact_text = parts[0].strip()
                category = parts[1].strip().upper() if len(parts) > 1 else "GENERAL"
                facts.append({"text": fact_text, "category": category})
            
            if not facts:
                return GatewayResponse(text="I couldn't extract specific facts from that. Could you rephrase?")
            
            # Step 2: Store in Mem0
            stored_count = 0
            from datetime import datetime
            try:
                from openclaw.agents.ira.src.memory.mem0_memory import get_mem0_service
                mem0 = get_mem0_service()
                
                category_to_user_id = {
                    "CUSTOMER": "machinecraft_customers",
                    "PARTNER": "machinecraft_customers",
                    "PRODUCT": "machinecraft_knowledge",
                    "PRICING": "machinecraft_pricing",
                    "PROCESS": "machinecraft_processes",
                    "RULE": "machinecraft_knowledge",
                    "GENERAL": "machinecraft_general",
                }
                
                for fact in facts:
                    uid = category_to_user_id.get(fact["category"], "machinecraft_general")
                    try:
                        mem0.add_memory(
                            text=f"TAUGHT BY RUSHABH: {fact['text']}",
                            user_id=uid,
                            metadata={
                                "source": "telegram_teach",
                                "category": fact["category"],
                                "timestamp": datetime.now().isoformat(),
                                "taught_by": "rushabh",
                            },
                        )
                        stored_count += 1
                    except Exception as e:
                        logger.warning(f"Failed to store fact in Mem0: {e}")
            except ImportError:
                return GatewayResponse(text="Mem0 not available. Facts could not be stored.")
            
            # Step 3: Check if any facts are rule changes that should update hard_rules.txt
            rule_facts = [f for f in facts if f["category"] == "RULE"]
            rules_updated = False
            if rule_facts:
                try:
                    hard_rules_path = PROJECT_ROOT / "data" / "brain" / "hard_rules.txt"
                    if hard_rules_path.exists():
                        current_rules = hard_rules_path.read_text()
                        new_rules = "\n".join(f"  {f['text']}" for f in rule_facts)
                        addition = (
                            f"\n\nRULE (TAUGHT {datetime.now().strftime('%Y-%m-%d')}):\n"
                            f"──────────────────────────\n{new_rules}\n"
                        )
                        # Insert before the closing line
                        if "======" in current_rules:
                            parts = current_rules.rsplit("=" * 10, 1)
                            updated = parts[0] + addition + "=" * 70 + "\n"
                            hard_rules_path.write_text(updated)
                            rules_updated = True
                except Exception as e:
                    logger.warning(f"Failed to update hard rules: {e}")
            
            # Build response
            response = f"Learned {stored_count} fact{'s' if stored_count != 1 else ''}:\n\n"
            for fact in facts:
                response += f"  [{fact['category']}] {fact['text']}\n"
            
            if rules_updated:
                response += f"\nAlso updated hard rules with {len(rule_facts)} rule change{'s' if len(rule_facts) != 1 else ''}."
            
            response += "\n\nThese are live now — I'll use them in my next response."
            
            logger.info(f"[TEACH] Stored {stored_count} facts from Rushabh")
            
            return GatewayResponse(
                text=response,
                log_entry={"type": "teach", "facts_count": stored_count},
            )
            
        except Exception as e:
            logger.error(f"Teach mode error: {e}")
            return GatewayResponse(text=f"Teaching failed: {e}")
    
    # =========================================================================
    # DEEP DIVE HANDLERS (Conversational multi-topic research)
    # =========================================================================
    
    def _handle_deepdive_start(self, query: str, chat_id: str) -> GatewayResponse:
        """Start a deep dive session with conversation phase."""
        try:
            from openclaw.agents.ira.src.brain.deep_dive import start_session
            response = start_session(chat_id, query)
            return GatewayResponse(
                text=f"🔬 *Deep Dive Mode*\n\n{response}",
                parse_mode="Markdown",
                log_entry={"type": "deepdive_start", "query": query[:100]},
            )
        except Exception as e:
            logger.error(f"Deep dive start error: {e}")
            return GatewayResponse(text=f"Deep dive failed to start: {e}")
    
    def _handle_deepdive_reply(self, text: str, chat_id: str) -> GatewayResponse:
        """Handle a reply during the deep dive conversation phase."""
        try:
            from openclaw.agents.ira.src.brain.deep_dive import (
                continue_conversation, plan_research, execute_research
            )
            
            follow_up = continue_conversation(chat_id, text)
            
            if follow_up is not None:
                return GatewayResponse(
                    text=f"🔬 *Deep Dive*\n\n{follow_up}",
                    parse_mode="Markdown",
                    log_entry={"type": "deepdive_conversation"},
                )
            
            # Conversation done -- move to planning and execution
            plan = plan_research(chat_id)
            
            plan_text = "🔬 *Deep Dive — Research Plan*\n\n"
            plan_text += f"Breaking this into {len(plan)} parallel research tasks:\n\n"
            for i, task in enumerate(plan):
                plan_text += f"{i+1}. *{task.get('topic', 'Task')}*\n"
                plan_text += f"   {task.get('rationale', '')}\n\n"
            plan_text += "Starting research now... this may take a few minutes."
            
            plan_msg_id = self.send_message(plan_text, parse_mode="Markdown")
            
            # Execute research in background thread
            import threading
            def _run_deep_dive():
                try:
                    def on_progress(msg):
                        if plan_msg_id:
                            try:
                                self.edit_message(
                                    plan_msg_id,
                                    f"🔬 *Deep Dive — Researching*\n\n{msg}",
                                    parse_mode="Markdown",
                                )
                            except Exception:
                                pass
                        self.send_typing_action()
                    
                    report = execute_research(chat_id, on_progress=on_progress)
                    
                    if len(report) > 4000:
                        # Split long reports into multiple messages
                        chunks = [report[i:i+3900] for i in range(0, len(report), 3900)]
                        if plan_msg_id:
                            self.edit_message(
                                plan_msg_id,
                                f"🔬 *Deep Dive — Complete*\n\n{chunks[0]}",
                                parse_mode="Markdown",
                            )
                        for chunk in chunks[1:]:
                            self.send_message(chunk, parse_mode="Markdown")
                    else:
                        if plan_msg_id:
                            self.edit_message(
                                plan_msg_id,
                                f"🔬 *Deep Dive — Report*\n\n{report}",
                                parse_mode="Markdown",
                            )
                        else:
                            self.send_message(
                                f"🔬 *Deep Dive — Report*\n\n{report}",
                                parse_mode="Markdown",
                            )
                except Exception as e:
                    logger.error(f"Deep dive execution error: {e}")
                    self.send_message(f"Deep dive research failed: {e}")
            
            thread = threading.Thread(target=_run_deep_dive, daemon=True)
            thread.start()
            
            return GatewayResponse(
                text=None,
                log_entry={"type": "deepdive_executing", "tasks": len(plan)},
            )
            
        except Exception as e:
            logger.error(f"Deep dive reply error: {e}")
            return GatewayResponse(text=f"Deep dive error: {e}")
    
    def _handle_deepdive_cancel(self, chat_id: str) -> GatewayResponse:
        """Cancel an active deep dive session."""
        try:
            from openclaw.agents.ira.src.brain.deep_dive import cancel_session
            if cancel_session(chat_id):
                return GatewayResponse(text="Deep dive cancelled.")
            return GatewayResponse(text="No active deep dive session.")
        except Exception:
            return GatewayResponse(text="No active deep dive session.")
    
    # =========================================================================
    # DEEP THINKING HANDLERS
    # =========================================================================
    
    def handle_research_command(self, query: str, chat_id: str) -> GatewayResponse:
        """
        Handle /research <query> command - Manus-style deep research.
        
        Multi-step iterative research across ALL knowledge sources:
        Qdrant (4 collections), Mem0 (7 stores), Neo4j, Machine DB, knowledge files.
        
        Usage: /research What European customers have we had for PF1 machines?
        """
        if not query or len(query.strip()) < 5:
            return GatewayResponse(
                text="Usage: `/research <your question>`\n\n"
                     "Example: `/research What European customers have bought PF1 machines?`\n\n"
                     "This runs a deep research process - you'll see:\n"
                     "• Query decomposition into sub-questions\n"
                     "• Searches across Qdrant, Mem0, Neo4j, Machine DB\n"
                     "• Gap analysis and follow-up searches\n"
                     "• Synthesized report with sources\n\n"
                     "Takes 30-90 seconds.",
                success=False
            )
        
        try:
            from openclaw.agents.ira.src.brain.deep_research_engine import deep_research
            
            def send_update(msg: str):
                try:
                    self.send_message(msg, parse_mode="Markdown")
                except Exception:
                    self.send_message(msg)
            
            import threading
            def run_research():
                try:
                    result = deep_research(
                        query=query,
                        on_progress=send_update,
                        max_iterations=8,
                        max_time_seconds=180,
                    )
                    
                    report = result.report
                    footer = (
                        f"\n\n---\n"
                        f"📊 _{result.total_findings} findings across {len(result.steps)} research steps "
                        f"({result.total_duration_ms/1000:.1f}s)_\n"
                        f"✅ _Confidence: {result.confidence}_"
                    )
                    
                    full_msg = report + footer
                    if len(full_msg) > 4000:
                        chunks = [full_msg[i:i+4000] for i in range(0, len(full_msg), 4000)]
                        for chunk in chunks:
                            try:
                                self.send_message(chunk, parse_mode="Markdown")
                            except Exception:
                                self.send_message(chunk)
                    else:
                        try:
                            self.send_message(full_msg, parse_mode="Markdown")
                        except Exception:
                            self.send_message(full_msg)
                    
                    # Store report in conversation history so follow-up questions work
                    self._last_response = report[:2000]
                    self._last_generation_path = "deep_research"
                    try:
                        from memory_service import get_memory_service
                        memory = get_memory_service()
                        memory.update_context_after_response(
                            channel="telegram",
                            identifier=chat_id or "",
                            user_message=f"/research {query}",
                            response_text=report[:1500],
                            mode="research",
                            intent=query,
                        )
                    except Exception:
                        pass
                    
                except Exception as e:
                    logger.error(f"Deep research failed: {e}", exc_info=True)
                    self.send_message(f"❌ Research failed: {str(e)[:200]}")
            
            thread = threading.Thread(target=run_research, daemon=True)
            thread.start()
            
            return GatewayResponse(
                text=None,
                log_entry={"type": "deep_research", "query": query[:100]}
            )
            
        except ImportError as e:
            # Fall back to basic thinking
            return self.handle_think_command(query, chat_id)
        except Exception as e:
            return self._make_error_response(e, "Research")
    
    def handle_think_command(self, query: str, chat_id: str) -> GatewayResponse:
        """
        Handle /think <query> command - Force deep thinking on any query.
        
        Usage: /think What European customers have we had for PF1 machines?
        """
        if not query or len(query.strip()) < 5:
            return GatewayResponse(
                text="Usage: `/think <your question>`\n\n"
                     "Example: `/think What European customers have we had for PF1 machines?`\n\n"
                     "This triggers deep analysis - I'll research across emails, customers, "
                     "and documents before responding.",
                success=False
            )
        
        try:
            from thinking_integration import handle_with_thinking_sync
            
            def send_msg(cid: str, text: str):
                self.send_message(text)
            
            was_async, response = handle_with_thinking_sync(
                chat_id=chat_id,
                query=query,
                send_message=send_msg,
                force_deep_thinking=True
            )
            
            if was_async:
                # Already acknowledged, response will come later
                return GatewayResponse(
                    text=None,  # Don't send duplicate
                    log_entry={"type": "think_command", "query": query[:100], "async": True}
                )
            elif response:
                return GatewayResponse(
                    text=response,
                    log_entry={"type": "think_command", "query": query[:100], "async": False}
                )
            else:
                return GatewayResponse(
                    text="🧠 Starting deep analysis...",
                    log_entry={"type": "think_command", "query": query[:100]}
                )
                
        except ImportError as e:
            return GatewayResponse(
                text=f"⚠️ Deep thinking not available: {e}",
                success=False
            )
        except Exception as e:
            return GatewayResponse(
                text=f"❌ Error starting analysis: {e}",
                success=False
            )
    
    def handle_thinking_status(self) -> GatewayResponse:
        """Handle /thinking command - Show status of thinking jobs."""
        try:
            from thinking_integration import handle_thinking_status_command
            result = handle_thinking_status_command(self.expected_chat_id)
            return GatewayResponse(
                text=result,
                log_entry={"type": "thinking_status"}
            )
        except ImportError as e:
            return GatewayResponse(
                text=f"⚠️ Deep thinking not available: {e}",
                success=False
            )
        except Exception as e:
            return GatewayResponse(
                text=f"❌ Error: {e}",
                success=False
            )
    
    def handle_cancel_thinking(self, chat_id: str) -> GatewayResponse:
        """Handle /cancel_thinking command - Cancel active thinking jobs."""
        try:
            from thinking_integration import handle_cancel_thinking_command
            result = handle_cancel_thinking_command(chat_id)
            return GatewayResponse(
                text=result,
                log_entry={"type": "cancel_thinking"}
            )
        except ImportError as e:
            return GatewayResponse(
                text=f"⚠️ Deep thinking not available: {e}",
                success=False
            )
        except Exception as e:
            return GatewayResponse(
                text=f"❌ Error: {e}",
                success=False
            )
    
    # =========================================================================
    # PLASTINDIA LEAD EMAIL DRAFTING
    # =========================================================================
    
    def handle_leads_list(self, category: Optional[str] = None) -> GatewayResponse:
        """
        Handle /leads command - List Plastindia exhibition leads.
        
        Usage: /leads or /leads A
        """
        try:
            sys.path.insert(0, str(BRAIN_DIR))
            from lead_email_drafter import list_plastindia_leads
            
            result = list_plastindia_leads(category)
            return GatewayResponse(
                text=result,
                parse_mode="Markdown",
                log_entry={"type": "leads_list", "category": category}
            )
        except ImportError as e:
            return GatewayResponse(
                text=f"❌ Lead drafter not available: {e}",
                success=False
            )
        except Exception as e:
            return GatewayResponse(
                text=f"❌ Error listing leads: {e}",
                success=False
            )
    
    def handle_lead_draft(self, query: str) -> GatewayResponse:
        """
        Handle "Draft email for [company]" command.
        
        Usage: "Draft email for Dhanya Plastics" or "/draft A2"
        """
        try:
            sys.path.insert(0, str(BRAIN_DIR))
            from lead_email_drafter import draft_email_for_lead
            
            result = draft_email_for_lead(query)
            return GatewayResponse(
                text=result,
                parse_mode="Markdown",
                log_entry={"type": "lead_draft", "query": query}
            )
        except ImportError as e:
            return GatewayResponse(
                text=f"❌ Lead drafter not available: {e}",
                success=False
            )
        except Exception as e:
            return GatewayResponse(
                text=f"❌ Error drafting email: {e}",
                success=False
            )
    
    def handle_email_command(self, args: str, chat_id: str) -> GatewayResponse:
        """
        Handle /email command - Manus-style email generation.
        
        Usage: /email <recipient> [company] [name] [purpose]
        
        Examples:
        /email john@bmw.de BMW "John Smith" follow_up
        /email sales@toyota.com Toyota "" cold_outreach
        /email contact@supplier.com
        """
        import threading
        import asyncio
        
        # Parse arguments
        parts = args.split()
        if not parts:
            return GatewayResponse(
                text="Usage: `/email <recipient> [company] [name] [purpose]`\n\n"
                     "Examples:\n"
                     "• `/email john@bmw.de BMW John follow_up`\n"
                     "• `/email sales@toyota.com Toyota \"\" cold_outreach`\n\n"
                     "Purposes: follow_up, cold_outreach, quote_response, "
                     "meeting_request, thank_you, introduction"
            )
        
        recipient_email = parts[0]
        company = parts[1] if len(parts) > 1 else ""
        recipient_name = parts[2] if len(parts) > 2 else ""
        purpose = parts[3] if len(parts) > 3 else "follow_up"
        
        # Validate email format
        if "@" not in recipient_email:
            return GatewayResponse(
                text=f"❌ Invalid email: `{recipient_email}`\n\nPlease provide a valid email address."
            )
        
        # Send acknowledgment
        self.send_message(
            f"📧 **Generating email for {recipient_email}**\n"
            f"Company: {company or '(auto-detect)'}\n"
            f"Name: {recipient_name or '(auto-detect)'}\n"
            f"Purpose: {purpose}\n\n"
            f"_Starting Manus-style research & drafting..._",
            parse_mode="Markdown"
        )
        
        # Run email generation in background
        def send_update(msg: str):
            if msg.strip():
                self.send_message(msg, parse_mode="Markdown")
        
        async def run_email_generation():
            try:
                # Add email_agent to path
                email_agent_dir = Path(__file__).parent.parent / "email_agent"
                sys.path.insert(0, str(email_agent_dir))
                
                from manus_style_email import generate_email
                
                result = await generate_email(
                    recipient_email=recipient_email,
                    company=company,
                    recipient_name=recipient_name,
                    purpose=purpose,
                    on_status=send_update
                )
                
                # Send final email
                self.send_message(
                    f"📧 **GENERATED EMAIL**\n\n"
                    f"**Subject:** {result.subject}\n\n"
                    f"---\n\n"
                    f"{result.body}\n\n"
                    f"---\n"
                    f"_Quality: {result.confidence:.0%} | "
                    f"Time: {result.generation_time_seconds:.0f}s | "
                    f"Drafts: {result.drafts_generated}_\n"
                    f"_Research: {result.research_summary}_",
                    parse_mode="Markdown"
                )
                
            except ImportError as e:
                self.send_message(f"❌ Email agent not available: {e}")
            except Exception as e:
                self.send_message(f"❌ Email generation failed: {str(e)[:200]}")
        
        # Start in background thread
        loop = asyncio.new_event_loop()
        thread = threading.Thread(
            target=lambda: loop.run_until_complete(run_email_generation()),
            daemon=True
        )
        thread.start()
        
        return GatewayResponse(
            text=None,  # Already sent acknowledgment
            log_entry={"type": "email_command", "recipient": recipient_email, "purpose": purpose}
        )
    
    def _try_deep_thinking(self, text: str, chat_id: str) -> Optional[GatewayResponse]:
        """
        Legacy deep thinking auto-detection. Disabled -- the agentic pipeline
        (tool_orchestrator) now handles all queries with multi-step reasoning.
        Use /research or /deepdive for explicit deep research mode.
        """
        return None
        
        # Legacy code below kept for reference but never reached
        try:
            from thinking_integration import handle_with_thinking_sync
            from thinking_jobs import should_use_deep_thinking
            
            if not should_use_deep_thinking(text):
                return None
            
            if any(kw in text.lower() for kw in ['quick', 'fast', 'briefly', 'short']):
                return None
            
            def send_msg(cid: str, msg_text: str):
                self.send_message(msg_text)
            
            was_async, response = handle_with_thinking_sync(
                chat_id=chat_id,
                query=text,
                send_message=send_msg
            )
            
            if was_async:
                logger.info(f"Deep thinking started for: {text[:50]}...")
                return GatewayResponse(
                    text=None,
                    log_entry={"type": "deep_thinking_auto", "query": text[:100]}
                )
            elif response:
                return GatewayResponse(
                    text=response,
                    log_entry={"type": "deep_thinking_auto", "query": text[:100]}
                )
            
            # Fall through to standard processing
            return None
            
        except ImportError:
            # Deep thinking not available, use standard processing
            return None
        except Exception as e:
            logger.error(f"Deep thinking check failed: {e}")
            return None
    
    _thinking_steps = []
    
    def _update_thinking_status(self, msg_id: int, stage: str, elapsed: float):
        """Update the thinking indicator with current tool/agent activity."""
        tool_labels = {
            "memory":             "Recalling memories...",
            "research":           "Clio searching knowledge base...",
            "research_skill":     "Clio searching knowledge base...",
            "iris":               "Iris gathering intelligence...",
            "web_search":         "Iris searching the web...",
            "customer_lookup":    "Looking up customer data...",
            "memory_search":      "Searching long-term memory...",
            "writing":            "Calliope composing response...",
            "writing_skill":      "Calliope composing response...",
            "verifying":          "Vera fact-checking...",
            "fact_checking_skill":"Vera fact-checking...",
            "polishing":          "Final polish...",
            "ask_user":           "Preparing a question for you...",
        }
        label = tool_labels.get(stage, f"Working on: {stage}...")
        
        if stage not in [s for s, _ in self._thinking_steps]:
            self._thinking_steps.append((stage, label))
        
        lines = ["🧠 *Thinking*\n"]
        for i, (s, lbl) in enumerate(self._thinking_steps):
            if s == stage:
                lines.append(f"▸ {lbl}")
            else:
                lines.append(f"✓ {lbl.replace('...', '')}")
        lines.append(f"\n_{elapsed:.0f}s_")
        
        text = "\n".join(lines)
        try:
            self.edit_message(msg_id, text, parse_mode="Markdown")
        except Exception:
            pass
    
    def process_message(self, message: TelegramMessage) -> None:
        """Process a single message and send response.
        
        Shows a live thinking indicator that updates as the pipeline progresses,
        then replaces it with the final response.
        """
        print(f"\n{'─'*40}")
        print(f"From: {message.from_user}")

        if message.document or message.photo:
            file_desc = (message.document or {}).get("file_name", "photo")
            print(f"File: {file_desc}")
            self.send_typing_action()
            status_msg_id = self.send_message(
                f"📥 Receiving `{file_desc}`...\n\n▸ Downloading from Telegram...",
                parse_mode="Markdown",
            )
            start_time = time.time()
            response = self.handle_document_upload(message)
            elapsed = time.time() - start_time
            if response.text:
                if status_msg_id:
                    success = self.edit_message(status_msg_id, response.text)
                    if not success:
                        self.send_message(response.text)
                else:
                    self.send_message(response.text)
            print(f"Document processed ({elapsed:.1f}s)")
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "from_user": message.from_user,
                "message": f"[file upload] {file_desc}",
                "success": response.success,
                "response_time_s": round(elapsed, 1),
            }
            if response.log_entry:
                log_entry.update(response.log_entry)
            append_to_log(TELEGRAM_ACTIVITY_LOG, log_entry)
            return

        print(f"Text: {message.text[:80]}{'...' if len(message.text) > 80 else ''}")
        
        is_command = message.text.startswith("/")
        start_time = time.time()
        thinking_msg_id = None
        self._thinking_steps = []
        
        if not is_command:
            thinking_msg_id = self.send_message(
                "🧠 *Thinking*\n\n▸ Analyzing your request...",
                parse_mode="Markdown"
            )
        else:
            self.send_typing_action()
        
        # Track tool calls from the agentic pipeline for live progress
        _thinking_done = threading.Event()
        _pending_tool_calls = []
        
        def _on_tool_call(tool_name):
            _pending_tool_calls.append(tool_name)
        
        self._current_progress_callback = _on_tool_call
        
        def _animate_thinking():
            if not thinking_msg_id:
                return
            last_count = 0
            while not _thinking_done.is_set():
                _thinking_done.wait(timeout=2.5)
                if _thinking_done.is_set():
                    break
                elapsed = time.time() - start_time
                if len(_pending_tool_calls) > last_count:
                    for tool in _pending_tool_calls[last_count:]:
                        self._update_thinking_status(thinking_msg_id, tool, elapsed)
                    last_count = len(_pending_tool_calls)
                self.send_typing_action()
        
        if thinking_msg_id:
            _thinker = threading.Thread(target=_animate_thinking, daemon=True)
            _thinker.start()
        
        response = self.route_message(message)
        
        _thinking_done.set()
        
        if response.text:
            if thinking_msg_id:
                success = self.edit_message(
                    thinking_msg_id,
                    response.text,
                    parse_mode=response.parse_mode,
                    reply_markup=response.reply_markup
                )
                if not success:
                    self.send_message(
                        response.text,
                        parse_mode=response.parse_mode,
                        reply_markup=response.reply_markup
                    )
            else:
                self.send_message(
                    response.text,
                    parse_mode=response.parse_mode,
                    reply_markup=response.reply_markup
                )
            elapsed = time.time() - start_time
            print(f"Response sent ({elapsed:.1f}s)")
        elif thinking_msg_id:
            self.edit_message(thinking_msg_id, "Done.")
        
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "from_user": message.from_user,
            "message": message.text[:200],
            "success": response.success,
            "response_time_s": round(time.time() - start_time, 1),
        }
        if response.log_entry:
            log_entry.update(response.log_entry)
        
        append_to_log(TELEGRAM_ACTIVITY_LOG, log_entry)
    
    def poll_once(self) -> int:
        """Poll for messages once and process them."""
        messages = self.fetch_updates()
        
        for message in messages:
            try:
                self.process_message(message)
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                track_error(
                    "telegram_gateway", 
                    e, 
                    {
                        "phase": "process_message",
                        "message_preview": message.text[:50] if message.text else "",
                        "chat_id": message.chat_id,
                    },
                    severity="error"
                )
                self.send_message(f"❌ Error: {e}")
        
        return len(messages)
    
    def poll_loop(self, interval: int = 2) -> None:
        """
        Poll continuously at specified interval.
        
        ⚠️  DEV/DEBUG ONLY - DO NOT USE IN PRODUCTION
        
        In production, use agent_main.py which:
        - Owns the single Telegram consumer
        - Prevents duplicate message processing
        - Coordinates with Gmail polling
        - Persists state properly
        """
        print("\n" + "=" * 50)
        print("⚠️  DEV/DEBUG MODE ONLY")
        print("=" * 50)
        print("This standalone loop is for DEBUGGING ONLY.")
        print("For production, use: ./ira start")
        print("")
        print(f"Polling interval: {interval}s")
        print("Press Ctrl+C to stop")
        print("=" * 50 + "\n")
        
        self.send_message("🔧 Ira gateway (DEV MODE). Type /help for commands.")
        
        while True:
            try:
                self.poll_once()
                time.sleep(interval)
            except KeyboardInterrupt:
                print("\n\nGateway stopped.")
                self.send_message("🛑 Ira gateway offline.")
                break
            except Exception as e:
                print(f"Error in poll loop: {e}")
                track_error("telegram_gateway", e, {"phase": "poll_loop"}, severity="error")
                time.sleep(interval * 2)


def main():
    parser = argparse.ArgumentParser(
        description="""Telegram Gateway - Telegram Interface Module for Ira

⚠️  PRODUCTION NOTE:
    For production use, run the unified agent instead:
    ./ira start  OR  python agent_main.py --foreground
    
    This CLI is for DEBUGGING/TESTING only.""",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Poll once and exit (safe for debugging)"
    )
    parser.add_argument(
        "--loop",
        action="store_true",
        help="⚠️ DEV ONLY: Poll continuously (use ./ira start for production)"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=2,
        help="Poll interval in seconds (default: 2)"
    )
    
    args = parser.parse_args()
    
    # Run startup validation first
    try:
        from startup_validator import validate_startup, print_startup_report
        print("\n🔍 Running startup validation...")
        startup_report = validate_startup(quick=args.once)  # Quick check for --once mode
        
        if not startup_report.can_start:
            print_startup_report(startup_report)
            print("\n❌ Cannot start due to critical issues. Fix them and try again.")
            sys.exit(1)
        
        if startup_report.warnings:
            print(f"⚠️ Startup warnings: {len(startup_report.warnings)} (non-blocking)")
        
        print(f"✅ Startup validation passed ({startup_report.startup_time_ms:.0f}ms)")
        
    except ImportError:
        print("⚠️ Startup validator not available - skipping pre-flight checks")
    except Exception as e:
        print(f"⚠️ Startup validation error: {e}")
    
    gateway = TelegramGateway()
    
    # Configure bot menu commands on startup
    if gateway.set_my_commands():
        print("✅ Bot menu commands configured")
    else:
        print("⚠️ Failed to configure bot menu commands")
    
    # Run knowledge health check on startup
    if KNOWLEDGE_HEALTH_AVAILABLE:
        try:
            monitor = get_health_monitor()
            report = monitor.run_health_check()
            
            if report.overall_score >= 80:
                print(f"✅ Knowledge health: {report.overall_score:.0f}/100")
            elif report.overall_score >= 50:
                print(f"⚠️ Knowledge health: {report.overall_score:.0f}/100")
                for issue in report.issues[:3]:
                    print(f"   - {issue.message}")
            else:
                print(f"❌ Knowledge health: {report.overall_score:.0f}/100 (CRITICAL)")
                for issue in report.issues[:5]:
                    print(f"   - {issue.message}")
                # Send alert for critical issues
                monitor.send_health_alert(report)
        except Exception as e:
            print(f"⚠️ Health check failed: {e}")
    
    if args.loop:
        print("\n" + "!"*60)
        print("! WARNING: --loop mode is for DEBUGGING ONLY")
        print("! For production, use: ./ira start")
        print("!"*60 + "\n")
        
        # Start proactive outreach scheduler in background
        try:
            from openclaw.agents.ira.src.conversation import start_outreach_scheduler
            start_outreach_scheduler()
            print("✅ Proactive outreach scheduler started")
        except Exception as e:
            print(f"⚠️ Outreach scheduler not started: {e}")
        
        # Start hourly self-health check
        def _hourly_health_check():
            while True:
                try:
                    time.sleep(3600)  # 1 hour
                    from openclaw.agents.ira.src.brain.knowledge_health import run_health_check
                    report = run_health_check()
                    logger.info(f"[SELF-CHECK] Health: {report.overall_score}/100, "
                                f"passed={report.checks_passed}, failed={report.checks_failed}")
                    if report.checks_failed > 0:
                        for issue in report.issues:
                            if issue.auto_fixable and issue.fix_action:
                                logger.info(f"[SELF-CHECK] Auto-fixing: {issue.message}")
                            elif issue.severity == "critical":
                                logger.warning(f"[SELF-CHECK] Critical: {issue.message}")
                except Exception as _hc_err:
                    logger.debug(f"[SELF-CHECK] Health check error: {_hc_err}")
        
        _health_thread = threading.Thread(target=_hourly_health_check, daemon=True)
        _health_thread.start()
        print("✅ Hourly self-health check started")
        
        gateway.poll_loop(args.interval)
    elif args.once:
        count = gateway.poll_once()
        print(f"\nProcessed {count} message(s)")
    else:
        parser.print_help()
        print("\n" + "-"*60)
        print("TIP: For production, run: ./ira start")
        print("-"*60)


if __name__ == "__main__":
    main()
