# Email Handler → BrainOrchestrator Integration Plan

**Created**: 2026-02-27  
**Status**: PLANNING  
**Priority**: HIGH IMPACT

---

## Executive Summary

The `email_handler.py` has a **manual 15-step process** that duplicates 80% of what `BrainOrchestrator` already does. This integration will:
- **Eliminate ~400 lines** of duplicate code
- Give emails the **same cognitive capabilities** as Telegram (episodic memory, metacognition, procedural guidance)
- Enable **true cross-channel consistency** in Ira's responses

---

## Current Architecture (Before)

```
EMAIL HANDLER (15 manual steps):
┌─────────────────────────────────────────────────────────────────┐
│ 1. Start trace                                                  │
│ 2. Check for corrections (FeedbackLearner)                      │
│ 3. Get identity (MemoryService)                                 │
│ 4. Coreference resolution (CoreferenceResolver)                 │
│ 5. Entity extraction (EntityExtractor)                          │
│ 6. Memory retrieval - Mem0 primary + PostgreSQL fallback        │
│ 6.5. Replika conversational enhancement (ConversationalEnhancer)│
│ 7. Conversation modules (GoalManager, StateController, etc.)    │
│ 8. Build context pack (manual)                                  │
│ 9. Generate response (OpenAI)                                   │
│ 10. Apply learned corrections                                   │
│ 11. Extract/store new memories                                  │
│ 12. Update conversation state                                   │
│ 13. Real-time indexing                                          │
│ 14. Record episodic events                                      │
│ 15. End trace                                                   │
└─────────────────────────────────────────────────────────────────┘

TELEGRAM GATEWAY (uses BrainOrchestrator):
┌─────────────────────────────────────────────────────────────────┐
│ 1. Memory trigger evaluation                                    │
│ 2. Unified memory retrieval (Mem0 + PostgreSQL)                 │
│ 3. Episodic retrieval ✅                                        │
│ 4. Procedural matching ✅                                       │
│ 5. Memory weaving ✅                                            │
│ 6. Memory reasoning ✅                                          │
│ 7. Metacognition (confidence calibration) ✅                    │
│ 8. Attention filtering ✅                                       │
│ 9. Graceful degradation                                         │
│ 10. Response generation                                         │
└─────────────────────────────────────────────────────────────────┘
```

**Email is missing**: Episodic retrieval, procedural matching, memory weaving, reasoning, metacognition, attention filtering.

---

## Target Architecture (After)

```
EMAIL HANDLER (simplified - delegates to BrainOrchestrator):
┌─────────────────────────────────────────────────────────────────┐
│ 1. Parse email → EmailData                                      │
│ 2. Extract identity                                             │
│ 3. Apply email-specific preprocessing:                          │
│    - Thread context loading                                     │
│    - Email-specific entity extraction (CC, signatures, etc.)    │
│ 4. ─────────────────────────────────────────────────────────────│
│    │                                                            │
│    │  BrainOrchestrator.process(                                │
│    │      message=email_body,                                   │
│    │      identity_id=identity_id,                              │
│    │      context={                                             │
│    │          "channel": "email",                               │
│    │          "thread_id": thread_id,                           │
│    │          "subject": subject,                               │
│    │          ...email_specific_context                         │
│    │      }                                                     │
│    │  )                                                         │
│    │                                                            │
│ 5. ─────────────────────────────────────────────────────────────│
│ 6. Apply email-specific postprocessing:                         │
│    - Email formatting (greeting, signature)                     │
│    - Email styling (AdaptiveStyleEngine)                        │
│    - Reply-to headers                                           │
│ 7. Store in email DB, real-time index                           │
└─────────────────────────────────────────────────────────────────┘
```

---

## Implementation Plan

### Phase 1: BrainOrchestrator Preparation

#### 1.1 Add Channel Context Support

```python
# brain_orchestrator.py - Update BrainState to include channel info

@dataclass
class BrainState:
    # ... existing fields ...
    
    # NEW: Channel-specific context
    channel: str = "telegram"  # "telegram", "email", "api"
    channel_context: Dict[str, Any] = field(default_factory=dict)
    
    # Email-specific
    thread_id: Optional[str] = None
    subject: Optional[str] = None
    is_reply: bool = False
```

#### 1.2 Add Email-Specific Triggers

```python
# Update MemoryTrigger to handle email context

TRIGGER_PATTERNS = {
    # ... existing patterns ...
    
    # Email-specific triggers
    "email_thread": {
        "patterns": [r"previous email", r"last message", r"thread"],
        "action": "load_thread_context",
    },
    "forwarded": {
        "patterns": [r"^FW:", r"forwarded", r"see below"],
        "action": "parse_forwarded_chain",
    },
    "cc_stakeholders": {
        "patterns": [r"CC.*@", r"loop in", r"adding"],
        "action": "identify_stakeholders",
    },
}
```

#### 1.3 Email Thread Memory Integration

```python
# Add email thread context to episodic memory

def load_email_thread_context(thread_id: str) -> str:
    """Load previous emails in thread for context."""
    # Query email database for thread history
    # Return formatted context
```

---

### Phase 2: EmailHandler Refactor

#### 2.1 New Simplified EmailHandler

```python
# email_handler.py - REFACTORED

class EmailHandler:
    """
    Handles email processing by delegating cognitive work to BrainOrchestrator.
    """
    
    def __init__(self):
        self.brain = BrainOrchestrator()
        self.email_preprocessor = EmailPreprocessor()
        self.email_postprocessor = EmailPostprocessor()
    
    def process_email(self, email_data: EmailData) -> Optional[EmailResponse]:
        """Process email using unified cognitive pipeline."""
        
        # 1. EMAIL-SPECIFIC PREPROCESSING
        identity_id = self._extract_identity(email_data)
        email_context = self.email_preprocessor.prepare(email_data)
        
        # 2. DELEGATE TO BRAIN ORCHESTRATOR
        brain_state = self.brain.process(
            message=email_data.body,
            identity_id=identity_id,
            context={
                "channel": "email",
                "thread_id": email_data.thread_id,
                "subject": email_data.subject,
                "from_email": email_data.from_email,
                "from_name": email_data.from_name,
                "is_reply": email_data.is_reply,
                "is_internal": self._is_internal(email_data.from_email),
                **email_context,
            }
        )
        
        # 3. Generate response using brain state
        if not brain_state.has_response:
            return None
        
        raw_response = self._generate_from_brain_state(brain_state)
        
        # 4. EMAIL-SPECIFIC POSTPROCESSING
        formatted_response = self.email_postprocessor.format(
            response=raw_response,
            email_data=email_data,
            brain_state=brain_state,
        )
        
        # 5. INDEX AND STORE
        self._index_email(email_data, formatted_response)
        
        return EmailResponse(
            to=email_data.from_email,
            subject=self._format_subject(email_data.subject),
            body=formatted_response,
            thread_id=email_data.thread_id,
            in_reply_to=email_data.message_id,
        )
```

#### 2.2 EmailPreprocessor (Email-Specific Logic)

```python
class EmailPreprocessor:
    """Handles email-specific preprocessing before BrainOrchestrator."""
    
    def prepare(self, email_data: EmailData) -> Dict[str, Any]:
        """Prepare email context for brain processing."""
        
        context = {}
        
        # 1. Parse email thread history
        if email_data.thread_id:
            context["thread_history"] = self._load_thread_history(
                email_data.thread_id
            )
        
        # 2. Extract email-specific entities
        # - CC list (stakeholders to consider)
        # - Signature blocks (to ignore)
        # - Forwarded content (separate processing)
        context["cc_list"] = self._extract_cc(email_data)
        context["cleaned_body"] = self._clean_signatures(email_data.body)
        
        # 3. Detect email intent patterns
        context["email_intent"] = self._classify_email_intent(email_data)
        
        # 4. Handle forwarded emails
        if self._is_forwarded(email_data):
            context["forwarded_chain"] = self._parse_forwarded(email_data.body)
        
        return context
```

#### 2.3 EmailPostprocessor (Email Formatting)

```python
class EmailPostprocessor:
    """Handles email-specific formatting after BrainOrchestrator."""
    
    def format(
        self,
        response: str,
        email_data: EmailData,
        brain_state: BrainState,
    ) -> str:
        """Format response as a proper email."""
        
        # 1. Apply email styling (from AdaptiveStyleEngine)
        styled = self._apply_email_style(response, email_data.from_email)
        
        # 2. Add greeting based on relationship
        warmth = brain_state.channel_context.get("warmth", "professional")
        greeting = self._generate_greeting(
            name=email_data.from_name,
            warmth=warmth,
        )
        
        # 3. Add signature
        signature = self._get_signature()
        
        # 4. Format for email (proper line breaks, etc.)
        return f"{greeting}\n\n{styled}\n\n{signature}"
```

---

### Phase 3: What Gets Removed

#### 3.1 Code to Delete from email_handler.py

```python
# REMOVE: These are now handled by BrainOrchestrator

# ❌ Manual memory retrieval (lines ~330-395)
# if MEM0_AVAILABLE:
#     try:
#         mem0 = get_mem0_service()
#         ...

# ❌ Manual Mem0Wrapper class (lines ~352-360)
# class Mem0Wrapper:
#     ...

# ❌ Manual conversational enhancement call (lines ~395-455)
# conv_enhancer = get_conversational_enhancer()
# if conv_enhancer:
#     ...

# ❌ Manual goal/stage/strategy processing (lines ~456-490)
# if CONVERSATION_MODULES_AVAILABLE:
#     goal_manager = GoalManager()
#     ...

# ❌ Manual context pack building (lines ~492-505)
# context_pack = self._build_context_pack(...)

# ❌ Manual correction application (lines ~519-530)
# if FEEDBACK_LEARNER_AVAILABLE:
#     enhanced = enhance_response_with_learning(...)
```

#### 3.2 Lines Saved

| Section | Lines Removed | Reason |
|---------|--------------|--------|
| Memory retrieval | ~65 | BrainOrchestrator.GracefulDegrader |
| Conversational enhancement | ~60 | BrainOrchestrator.MemoryWeaver |
| Conversation modules | ~35 | BrainOrchestrator.TriggerEvaluator |
| Context building | ~50 | BrainOrchestrator.BrainState |
| Feedback learning | ~15 | BrainOrchestrator.FeedbackLearner |
| Coreference | ~30 | Can be moved to preprocessor |
| Entity extraction | ~25 | Can be moved to preprocessor |
| **TOTAL** | **~280** | |

---

### Phase 4: Testing Plan

#### 4.1 Unit Tests

```python
# test_email_brain_integration.py

def test_email_uses_brain_orchestrator():
    """Verify email processing uses BrainOrchestrator."""
    handler = EmailHandler()
    email = EmailData(
        message_id="test-123",
        thread_id="thread-456",
        from_email="john@example.com",
        from_name="John Doe",
        to_email="ira@machinecraft.in",
        subject="PF1 Pricing",
        body="What's the price for PF1-C-1200?",
        date=datetime.now(),
    )
    
    with patch.object(handler.brain, 'process') as mock_process:
        mock_process.return_value = create_mock_brain_state()
        handler.process_email(email)
        
        # Verify BrainOrchestrator was called with correct context
        mock_process.assert_called_once()
        call_args = mock_process.call_args
        assert call_args.kwargs["context"]["channel"] == "email"
        assert call_args.kwargs["context"]["thread_id"] == "thread-456"


def test_email_gets_episodic_memory():
    """Verify emails now have access to episodic memory."""
    handler = EmailHandler()
    # ... test episodic context is available


def test_email_gets_procedural_guidance():
    """Verify emails now have access to procedural memory."""
    handler = EmailHandler()
    # ... test procedural guidance is applied
```

#### 4.2 Integration Tests

```bash
# Test with real email
python -c "
from email_handler import EmailHandler, EmailData
from datetime import datetime

handler = EmailHandler()
email = EmailData(
    message_id='test-001',
    thread_id='thread-001',
    from_email='test@example.com',
    from_name='Test User',
    to_email='ira@machinecraft.in',
    subject='RE: PF1 Quote',
    body='Thanks for the previous info. What about the lead time?',
    date=datetime.now(),
    is_reply=True,
)

response = handler.process_email(email)
print(f'Response: {response.body[:200]}...')
"
```

---

## Migration Checklist

### Pre-Migration
- [ ] Backup current email_handler.py
- [ ] Run existing email tests (baseline)
- [ ] Document current email response quality

### Migration Steps
- [ ] Phase 1.1: Add channel context to BrainState
- [ ] Phase 1.2: Add email-specific triggers
- [ ] Phase 1.3: Add thread context loading
- [ ] Phase 2.1: Create new simplified EmailHandler
- [ ] Phase 2.2: Create EmailPreprocessor
- [ ] Phase 2.3: Create EmailPostprocessor
- [ ] Phase 3: Remove duplicate code

### Post-Migration
- [ ] Run email tests (compare quality)
- [ ] Test cross-channel memory (email → telegram)
- [ ] Verify episodic memory works for emails
- [ ] Verify procedural guidance works for emails
- [ ] Performance benchmark (should be similar or better)

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Email formatting breaks | EmailPostprocessor preserves existing logic |
| Memory retrieval differs | Use same GracefulDegrader as Telegram |
| Thread context lost | EmailPreprocessor explicitly loads it |
| Performance regression | BrainOrchestrator has async option |

---

## Success Metrics

| Metric | Before | After (Target) |
|--------|--------|----------------|
| Lines of code | ~965 | ~400 |
| Duplicate code | 80% | 0% |
| Episodic memory | ❌ | ✅ |
| Procedural guidance | ❌ | ✅ |
| Metacognition | ❌ | ✅ |
| Cross-channel consistency | Partial | Full |

---

## Files to Modify

| File | Action |
|------|--------|
| `email_handler.py` | Major refactor (replace 15-step with 5-step) |
| `brain_orchestrator.py` | Add channel context support |
| `email_preprocessor.py` | NEW - email-specific preprocessing |
| `email_postprocessor.py` | NEW - email formatting |
| `email_tests.py` | NEW - integration tests |

---

## Execution Command

When ready to implement, use this prompt:

```
Implement the Email → BrainOrchestrator integration as described in 
docs/EMAIL_BRAIN_INTEGRATION_PLAN.md. Follow these steps:

1. First, update BrainOrchestrator to support channel context
2. Create EmailPreprocessor class for email-specific logic
3. Create EmailPostprocessor class for email formatting
4. Refactor EmailHandler to use BrainOrchestrator.process()
5. Remove duplicate code from old EmailHandler
6. Write integration tests

Start with Phase 1.1 (channel context support).
```
