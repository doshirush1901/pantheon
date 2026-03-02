---
name: feedback_handler
description: Process user feedback and corrections to learn and improve IRA's knowledge and behavior.
---

# Feedback Handler

Use this skill when the user provides feedback, corrections, or complaints about IRA's previous responses.

**This is crucial for IRA's continuous learning - ALWAYS process feedback properly!**

## How to detect feedback

Look for these patterns in user messages:
- "No, that's wrong" / "That's not correct"
- "Actually, it's X not Y"
- "X is a competitor/customer"  
- "Should be X instead of Y"
- "Fix this" / "Correct this"
- "Remember this"
- "Don't do X" / "Always do Y"

## How to use

**Via Multi-Agent System (Recommended):**

```python
from src.agents import get_chief_of_staff

cos = get_chief_of_staff()
# The CoS will automatically route feedback to the ReflectorAgent
response = await cos.process_message(feedback_message, user_id, channel)
```

**Direct Reflector Agent Call:**

```python
from src.agents.reflector import get_reflector

reflector = get_reflector()
result = await reflector.process_feedback(
    feedback="<user feedback>",
    original_response="<your original response>",
    user_id="<user_id>"
)
```

### Arguments
- `feedback`: The feedback message from the user
- `original_response`: Your original response that is being corrected
- `user_id`: User identifier (email or chat ID)

## What the pipeline does

1. **DETECT** - Identify this is feedback (not a new question)
2. **CLASSIFY** - What type? (spec, price, fact, entity, style, behavior)
3. **EXTRACT** - What exactly was wrong vs correct
4. **VALIDATE** - Sanity check the correction
5. **UPDATE KNOWLEDGE**:
   - Mem0: Store as high-priority correction memory
   - Machine Database: Log spec/price changes for review
   - Truth Hints: Add correction hints
   - Learned Corrections: Update competitor/customer lists
6. **UPDATE LOGIC**:
   - Guardrails: Add behavioral rules
   - Procedural Memory: Update procedures
7. **CONFIRM** - Generate acknowledgment message
8. **PREVENT** - Log for future prevention

## Feedback types handled

| Type | Example | Updates |
|------|---------|---------|
| spec_correction | "The heater is 125kW not 100kW" | Mem0, Machine DB, Truth Hints |
| price_correction | "It's ₹60L not ₹65L" | Mem0, Machine DB, Truth Hints |
| entity_correction | "Kiefel is a competitor" | Learned Corrections list |
| style_preference | "I prefer detailed specs" | Procedural Memory |
| behavior_correction | "Don't recommend competitors" | Guardrails |
| hallucination | "You made that up" | Truth Hints, Guardrails |

## Example output

```
Got it! I've learned from your feedback:

📝 **PF1-C-2015 price**
   • Wrong: ₹65 Lakhs
   • Correct: ₹60 Lakhs

**Updates applied:**
   ✅ mem0:stored_as_high_priority_memory
   ✅ machine_database:PF1-C-2015:price_inr
   ✅ truth_hints:added_correction_hint

I won't make this mistake again. Thanks for helping me improve!
```

## When to use this skill

- When user says "that's wrong" or similar
- When user provides corrections
- When user identifies competitors/customers
- When user gives style preferences
- When user complains about repeated mistakes

## Important rules

1. ALWAYS acknowledge feedback explicitly
2. Show what was learned
3. Thank the user for helping improve
4. If critical (wrong price to customer), flag for immediate review
5. Store corrections with high priority so they override old data
