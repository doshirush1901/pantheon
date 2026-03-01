# Contributing to Ira

Thank you for your interest in contributing to Ira! This document provides guidelines and information for contributors.

---

## ⚠️ THE COVENANT: THOU SHALT NOT DUPLICATE

> *This covenant was established after the Great Deletion of 2026-02-28, as a preventative measure against the architectural sins of the past. See `/TECHNICAL_DEBT.md` for the full confession.*

**No new file, class, or function may be created if it duplicates functionality that already exists anywhere in the codebase, including the archive.**

If you require functionality from an archived module, you have only two choices:

1. **Resurrect and Maintain:** Un-archive the module, integrate it into the current architecture, and accept full responsibility for its maintenance.
2. **Rewrite and Replace:** Write a new module from scratch that fulfills the requirement, and then **permanently delete the old module and all references to it.**

There is no third option. There is no "copying the good parts." There is no "temporary duplication." The system must evolve through replacement, not addition. This is the only way to prevent the accumulation of technical debt that leads to architectural collapse.

### Prohibited Patterns

| Pattern | Why It's Forbidden |
|---------|-------------------|
| `sys.path.insert()` / `sys.path.append()` | Indicates broken import structure. Fix imports properly. |
| Deprecated-but-imported modules | Creates zombie dependencies. Delete or migrate. |
| Documented-but-nonexistent files | Lies to future developers. Delete the documentation or create the file. |
| Multiple implementations of the same class | Creates maintenance burden and divergent behavior. Unify. |

**Violation of this covenant will be considered a P0 severity bug and must be rectified immediately.**

---

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Project Structure](#project-structure)
- [Coding Standards](#coding-standards)
- [Making Changes](#making-changes)
- [Testing](#testing)
- [Documentation](#documentation)
- [Pull Request Process](#pull-request-process)
- [CI/CD Setup](#cicd-setup-github-secrets)

---

## Code of Conduct

We are committed to providing a friendly, safe, and welcoming environment for all contributors. Please read and follow our [Code of Conduct](CODE_OF_CONDUCT.md) to ensure a welcoming and inclusive environment for all participants.

**TL;DR:** Be respectful, constructive, and professional. Focus on the work, not the person.

---

## Getting Started

### Prerequisites

- Python 3.10 or higher
- Docker and Docker Compose
- Git
- API keys for OpenAI, Voyage AI (optional: Mem0)

### Fork and Clone

```bash
# Fork the repository on GitHub, then clone your fork
git clone https://github.com/YOUR_USERNAME/ira.git
cd ira

# Add upstream remote
git remote add upstream https://github.com/machinecraft/ira.git
```

---

## Development Setup

### 1. Create Virtual Environment

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
```

### 2. Install Dependencies

```bash
# Install all dependencies
pip install -r requirements.txt

# Install development dependencies
pip install pytest pytest-cov black isort flake8
```

### 3. Configure Environment

```bash
cp .env.example .env
# Edit .env with your API keys
```

### 4. Start Infrastructure

```bash
docker-compose up -d
```

### 5. Verify Setup

```bash
# Check configuration
python -c "from openclaw.agents.ira.config import validate_config; print(validate_config())"

# Run a simple test
python openclaw/agents/ira/skills/brain/unified_retriever.py "test query"
```

---

## Project Structure

```
Ira/
├── openclaw/agents/ira/       # Main application
│   ├── agent.py               # Core agent coordinator
│   ├── config.py              # Configuration management
│   ├── core/                  # Core components
│   └── skills/                # Modular capabilities
│       ├── brain/             # RAG & knowledge
│       ├── memory/            # Persistent memory
│       ├── conversation/      # Conversation handling
│       ├── email_channel/     # Email integration
│       └── telegram_channel/  # Telegram bot
├── scripts/                   # Utility scripts
├── data/                      # Data storage
├── docs/                      # Documentation
└── tests/                     # Test suite
```

### Key Files

| File | Purpose |
|------|---------|
| `agent.py` | Central coordinator for all channels |
| `config.py` | Single source of truth for configuration |
| `skills/brain/unified_retriever.py` | RAG retrieval system |
| `skills/memory/brain_orchestrator.py` | Memory pipeline |
| `skills/telegram_channel/telegram_gateway.py` | Telegram integration |

---

## Coding Standards

### Style Guide

We follow PEP 8 with some modifications:

```python
# Line length: 100 characters max
# Use type hints for function signatures
# Use docstrings for public functions

def process_message(
    message: str,
    user_id: str,
    channel: str = "telegram"
) -> Dict[str, Any]:
    """
    Process an incoming message and generate a response.
    
    Args:
        message: The user's message text
        user_id: Unique identifier for the user
        channel: Communication channel (telegram, email, api)
    
    Returns:
        Dictionary containing response text and metadata
    """
    pass
```

### Formatting

```bash
# Format code with Black
black openclaw/ scripts/

# Sort imports with isort
isort openclaw/ scripts/

# Check style with flake8
flake8 openclaw/ scripts/
```

### Naming Conventions

| Type | Convention | Example |
|------|------------|---------|
| Files | snake_case | `unified_retriever.py` |
| Classes | PascalCase | `UnifiedRetriever` |
| Functions | snake_case | `process_message()` |
| Constants | UPPER_SNAKE | `MAX_RETRIES` |
| Private | _leading_underscore | `_internal_method()` |

### Import Order

```python
# 1. Standard library
import json
import os
from datetime import datetime
from typing import Dict, List, Optional

# 2. Third-party packages
import openai
from qdrant_client import QdrantClient

# 3. Local imports
from openclaw.agents.ira.config import get_qdrant_client
from .utils import format_response
```

---

## Making Changes

### Branch Naming

```bash
# Feature branches
git checkout -b feature/add-email-templates

# Bug fixes
git checkout -b fix/memory-leak-in-retriever

# Documentation
git checkout -b docs/update-api-reference
```

### Commit Messages

Follow conventional commits:

```bash
# Format: <type>(<scope>): <description>

# Types:
# feat: New feature
# fix: Bug fix
# docs: Documentation
# refactor: Code refactoring
# test: Adding tests
# chore: Maintenance

# Examples:
git commit -m "feat(brain): add hybrid search with BM25"
git commit -m "fix(memory): prevent duplicate episode storage"
git commit -m "docs(readme): update installation guide"
```

### Keep Changes Focused

- One feature/fix per pull request
- Keep commits atomic and logical
- Squash WIP commits before submitting

---

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_retrieval.py

# Run with coverage
pytest --cov=openclaw --cov-report=html

# Run specific test
pytest tests/test_retrieval.py::test_hybrid_search
```

### Writing Tests

```python
# tests/test_retrieval.py
import pytest
from openclaw.agents.ira.skills.brain.unified_retriever import UnifiedRetriever

class TestUnifiedRetriever:
    @pytest.fixture
    def retriever(self):
        return UnifiedRetriever()
    
    def test_search_returns_results(self, retriever):
        results = retriever.search("test query", top_k=5)
        assert isinstance(results, list)
        assert len(results) <= 5
    
    def test_empty_query_raises_error(self, retriever):
        with pytest.raises(ValueError):
            retriever.search("", top_k=5)
```

### Test Categories

| Category | Location | Purpose |
|----------|----------|---------|
| Unit | `tests/unit/` | Individual functions |
| Integration | `tests/integration/` | Component interactions |
| E2E | `tests/e2e/` | Full workflow tests |

---

## Documentation

### Docstring Format

```python
def search(
    self,
    query: str,
    top_k: int = 10,
    filters: Optional[Dict] = None
) -> List[Dict[str, Any]]:
    """
    Search for relevant documents using hybrid retrieval.
    
    Combines vector similarity search with BM25 keyword matching,
    then reranks results using FlashRank.
    
    Args:
        query: Search query string
        top_k: Maximum number of results to return
        filters: Optional metadata filters
    
    Returns:
        List of result dictionaries with keys:
        - text: Document text
        - score: Relevance score (0-1)
        - metadata: Document metadata
    
    Raises:
        ValueError: If query is empty
        ConnectionError: If Qdrant is unavailable
    
    Example:
        >>> retriever = UnifiedRetriever()
        >>> results = retriever.search("PF1 specifications", top_k=5)
        >>> print(results[0]['text'][:100])
    """
```

### Updating Documentation

1. Update relevant docs in `docs/`
2. Update inline docstrings
3. Update README if API changes
4. Add changelog entry

---

## Pull Request Process

### Before Submitting

```bash
# 1. Sync with upstream
git fetch upstream
git rebase upstream/main

# 2. Run tests
pytest

# 3. Check formatting
black --check openclaw/ scripts/
flake8 openclaw/ scripts/

# 4. Update documentation if needed
```

### PR Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Refactoring

## Testing
How was this tested?

## Checklist
- [ ] Code follows style guidelines
- [ ] Tests pass locally
- [ ] Documentation updated
- [ ] No new warnings
```

### Review Process

1. Submit PR with clear description
2. Address reviewer feedback
3. Ensure CI checks pass
4. Squash commits if requested
5. Maintainer merges when approved

---

## CI/CD Setup: GitHub Secrets

The `quality-gates.yml` workflow requires several secrets to be set in your repository's GitHub settings (`Settings > Secrets and variables > Actions`) for the Nemesis evaluation job to run.

**Required Secrets:**

- `OPENAI_API_KEY`: Your API key for OpenAI, used by the LLM-as-judge in Nemesis.
- `VOYAGE_API_KEY`: Your API key for Voyage AI, used for embeddings.
- `JINA_API_KEY`: Your API key for Jina AI, used by the Iris agent for web searches.

---

## Getting Help

- **Questions**: Open a GitHub Discussion
- **Bugs**: Open a GitHub Issue
- **Security**: See [SECURITY.md](SECURITY.md)

---

## Recognition

Contributors are recognized in our [CONTRIBUTORS.md](CONTRIBUTORS.md) file. Thank you for helping make Ira better!
