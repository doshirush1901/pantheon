# Knowledge Health System

**Created:** 2026-02-27  
**Purpose:** Prevent knowledge gaps, hallucinations, and business rule violations

---

## Problem Solved

When asked "Suggest the right machine for 4mm ABS...", Ira:
- ❌ Suggested AM Series (wrong - AM can only handle ≤2mm)
- ❌ Said "[insert estimated price range]" (hallucination)
- ❌ Didn't use the actual price list that was in `data/imports/`

**Root Causes:**
1. Critical documents not indexed
2. Business rules not codified
3. No detection of hallucinations
4. No validation before sending responses

---

## Solution: Knowledge Health Monitor

### File: `openclaw/agents/ira/skills/brain/knowledge_health.py`

A proactive system that:

### 1. Startup Health Check
Runs automatically when gateway starts:
```
✅ Knowledge health: 95/100
   - All critical documents indexed
   - Truth hints coverage OK
   - Business rules defined
```

### 2. Critical Document Detection
Ensures required documents are indexed:

| Document Type | Pattern | Required Content |
|--------------|---------|------------------|
| Price List | `price.*list` | PF1, INR, price |
| Spec Sheets | `spec.*sheet` | dimension, mm |
| Machine Selection Guide | `selection.*guide` | material, thickness |

### 3. Business Rules Enforcement
Hardcoded rules that prevent mistakes:

```python
BUSINESS_RULES = [
    {
        "id": "am_thickness_limit",
        "name": "AM Series Thickness Limit",
        "description": "AM Series can only handle ≤2mm",
        "violation_pattern": r"([3-9]|1[0-9])\s*mm.*thick",
        "correct_response": "Use PF1 Series for >2mm"
    },
    {
        "id": "price_must_be_specific",
        "name": "Prices Must Be Specific",
        "violation_pattern": r"\[.*insert.*\]|contact.*pric",
        "correct_response": "Quote INR prices from price list"
    },
]
```

### 4. Hallucination Detection
Patterns that indicate hallucination:
- `[insert ...]` - Placeholder text
- `approximately`, `around` - Vague when specific data exists
- `contact for pricing` - When we have price list
- `I don't have specific` - Without trying retrieval

### 5. Response Validation
Before sending every response:
```python
is_safe, warnings = validate_response(query, response, citations)
if not is_safe:
    # Block or modify response
```

### 6. Auto-Fix Capabilities
Some issues can be fixed automatically:
- Missing documents → Re-run `reindex_docs.py`
- Stale index → Re-index newer files

### 7. Telegram Alerts
Critical issues trigger immediate Telegram notification:
```
⚠️ Knowledge Health Alert

Score: 40/100
Critical issues: 2

• Price list not indexed
• No truth hint for machine selection
```

---

## Integration Points

### Gateway Startup (`telegram_gateway.py`)
```python
if KNOWLEDGE_HEALTH_AVAILABLE:
    monitor = get_health_monitor()
    report = monitor.run_health_check()
    if report.overall_score < 50:
        monitor.send_health_alert(report)
```

### Response Flow (TODO)
```python
# Before sending response
is_safe, warnings = validate_health(query, response.text)
if not is_safe:
    # Enhance response or add disclaimer
```

---

## CLI Usage

```bash
# Run health check
python knowledge_health.py --check

# Auto-fix issues
python knowledge_health.py --check --fix

# Send alert to Telegram
python knowledge_health.py --check --alert
```

---

## How It Prevents Future Mistakes

| Mistake | Detection | Prevention |
|---------|-----------|------------|
| Missing price list | `_check_critical_documents()` | Alert + auto-reindex |
| AM for thick material | Business rule `am_thickness_limit` | Response validation |
| Vague pricing | Hallucination pattern `\[.*insert.*\]` | Block response |
| Stale data | `_check_index_freshness()` | Alert + auto-reindex |
| Uncorrected facts | `_check_unlearned_corrections()` | Flagged for review |

---

## Future Enhancements

1. **Real-time learning** - Detect corrections in chat and auto-add to truth hints
2. **Confidence calibration** - Track when low confidence = wrong answer
3. **Scheduled deep audit** - Nightly comprehensive check
4. **A/B testing** - Compare responses with/without validation
5. **User feedback loop** - "Was this answer helpful?" button

---

*System built to prevent the AM vs PF1 mistake from ever happening again.*
