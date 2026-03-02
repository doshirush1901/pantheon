---
name: run_reflection
description: Triggered after every user interaction to analyze quality, log errors, and extract lessons.
trigger: auto_post_interaction
---

# Run Reflection

Use this skill automatically after every user interaction to analyze the conversation, evaluate response quality, and continuously improve IRA's performance.

**This skill should be triggered after EVERY interaction - it's how IRA learns!**

## When to trigger

This skill runs automatically after:
- Every email response sent
- Every chat/Telegram message responded to
- Every API query answered
- Every quote generated

## How to use

### Automatic (Recommended)

The Chief of Staff should call this at the end of every interaction:

```python
from src.agents.reflector import get_reflector, ConversationTranscript, ConversationTurn

reflector = get_reflector()
transcript = ConversationTranscript(
    conversation_id="<unique_id>",
    user_id="<user_email_or_id>",
    channel="email",  # or "telegram", "api"
    turns=[
        ConversationTurn(role="user", content="<user_message>"),
        ConversationTurn(role="assistant", content="<ira_response>"),
    ],
    final_response="<final_response_sent>",
    sources_used=["machine_database", "qdrant:ira_chunks_v4"],
    processing_time_seconds=12.5,
)

result = await reflector.run_reflection(transcript)
```

### CLI (Manual)

```bash
exec python -c "
import asyncio
from src.agents.reflector import get_reflector, ConversationTranscript, ConversationTurn

async def main():
    reflector = get_reflector()
    transcript = ConversationTranscript(
        conversation_id='manual-test',
        user_id='test@example.com',
        channel='cli',
        turns=[
            ConversationTurn(role='user', content='What is the price of PF1-C-2015?'),
            ConversationTurn(role='assistant', content='The PF1-C-2015 is priced at ₹60 Lakhs.'),
        ],
        final_response='The PF1-C-2015 is priced at ₹60 Lakhs.',
        sources_used=['machine_database'],
        processing_time_seconds=5.0,
    )
    result = await reflector.run_reflection(transcript)
    print(f'Score: {result.overall_score:.2f}')
    print(f'Issues: {len(result.issues_found)}')
    print(f'Lessons: {len(result.lessons_extracted)}')

asyncio.run(main())
"
```

## What the reflection does

### 1. Analyze Conversation Transcript
- Parse all user messages and assistant responses
- Identify the user's original query and intent
- Extract entities mentioned (machines, materials, prices)

### 2. Evaluate Response Quality

Scores across 6 dimensions (0-1 scale):

| Dimension | What it checks |
|-----------|----------------|
| **Factual Accuracy** | AM series ≤1.5mm rule, pricing disclaimers, hallucination patterns |
| **Helpfulness** | Does response address the query? Specific data provided? |
| **Completeness** | All parts of multi-part queries answered? |
| **Tone** | Channel-appropriate formality? Not too casual? |
| **Structure** | Readable paragraphs? Bullet points where needed? |
| **Responsiveness** | Processing time acceptable? |

### 3. Log Issues to errors.md

If **critical issues** are found (score < 0.5 in any dimension):

```markdown
### ERR-XXX: Description
- **Date**: 2024-XX-XX
- **Category**: specification_error / pricing_error / tone_issue / hallucination
- **Severity**: critical / warning
- **Description**: What went wrong
- **Context**: Snippet from the response
- **Prevention**: [To be defined]
- **Status**: Open
```

### 4. Extract Lessons to lessons.md

If **successful patterns** are detected (high scores, positive feedback):

```markdown
### Pattern Name
- **Lesson**: What worked well
- **Source**: user_feedback / quality_evaluation
- **Priority**: Critical / High / Medium / Low
```

### 5. Generate Recommendations

Based on analysis, returns actionable recommendations:
- "Run fact_checker before writer for all technical responses"
- "Ensure researcher retrieves data matching query intent"
- "Pass recipient context to writer for tone calibration"

## Output

The reflection returns a `ReflectionResult`:

```python
{
    "interaction_id": "conv-12345",
    "overall_score": 0.85,
    "quality_scores": [...],  # Per-dimension scores
    "issues_found": [...],    # List of issues
    "lessons_extracted": [...],  # List of lessons
    "errors_logged": 1,       # Count written to errors.md
    "lessons_logged": 0,      # Count written to lessons.md  
    "recommendations": [...]  # Actionable improvements
}
```

## Integration with Chief of Staff

The Chief of Staff should include reflection in its main loop:

```python
# In chief_of_staff/agent.py

async def _reflect_on_interaction(self, request, response, execution_result):
    """Trigger reflector agent for continuous learning."""
    reflector = get_reflector()
    
    transcript = ConversationTranscript(
        conversation_id=request.request_id,
        user_id=request.user_id,
        channel=request.channel,
        turns=[
            ConversationTurn(role="user", content=request.message),
            ConversationTurn(role="assistant", content=response.response),
        ],
        final_response=response.response,
        sources_used=response.sources_used,
        processing_time_seconds=response.processing_time_seconds,
    )
    
    result = await reflector.run_reflection(transcript, verbose=False)
    
    if result.overall_score < 0.6:
        logger.warning(f"Low quality score: {result.overall_score:.2f}")
```

## Critical Rules Checked

The reflector enforces these critical rules:

1. **AM Series Thickness**: Must be ≤1.5mm - ALWAYS
2. **Pricing Disclaimer**: Any price must include "subject to configuration and current pricing"
3. **Hallucination Patterns**: Detects unrealistic numbers, superlatives, unverified claims

## Files Modified

- `src/agents/chief_of_staff/errors.md` - Appends new errors
- `src/agents/chief_of_staff/lessons.md` - Appends new lessons

## Best Practices

1. **Always trigger** - Even for simple interactions
2. **Include full context** - Sources used, processing time
3. **Review errors.md weekly** - Address recurring patterns
4. **Run dream mode nightly** - For deeper consolidation

## Related Skills

- `feedback_handler` - Process explicit user corrections
- `run_dream_mode` - Overnight learning consolidation
- `store_memory` - Store important facts in Mem0
