# Lessons Learned

This file contains lessons learned from past interactions that guide the Chief of Staff's planning decisions.

## Response Quality

### Pricing Inquiries
- **Lesson**: Always include "subject to configuration and current pricing" disclaimer
- **Source**: Customer feedback, compliance requirement
- **Priority**: Critical

### Machine Specifications
- **Lesson**: AM series thickness is ALWAYS ≤1.5mm - never state otherwise
- **Source**: Engineering specification, verified Q1 2024
- **Priority**: Critical

### Competitor Mentions
- **Lesson**: When competitors (ILLIG, Kiefel, Multivac) are mentioned, provide objective comparison without disparaging
- **Source**: Sales team guidance
- **Priority**: High

## Planning Patterns

### Complex Queries
- **Lesson**: Break down multi-part questions into individual research tasks before synthesis
- **Source**: Improved answer accuracy observed
- **Priority**: High

### Email Drafts
- **Lesson**: Always run fact_checker before writer for technical emails
- **Source**: Reduced correction rate by 40%
- **Priority**: High

### Quote Generation
- **Lesson**: Sequence: researcher → fact_checker → writer → fact_checker (final)
- **Source**: Best practice from successful quotes
- **Priority**: Medium

## Agent Delegation

### Researcher Agent
- **Lesson**: For pricing queries, researcher should check both machine_database and recent quotes
- **Source**: Price accuracy improvement
- **Priority**: High

### Writer Agent
- **Lesson**: Provide writer with recipient context (new lead vs existing customer) for tone adjustment
- **Source**: Customer satisfaction feedback
- **Priority**: Medium

### Fact Checker Agent
- **Lesson**: Run fact_checker on ALL technical claims, not just pricing
- **Source**: Specification error in Feb 2024
- **Priority**: Critical

## Memory Integration

### Returning Customers
- **Lesson**: Always check mem0 for previous interactions before generating new response
- **Source**: Improved personalization scores
- **Priority**: High

### Feedback Handling
- **Lesson**: When user corrects information, immediately delegate to reflector before responding
- **Source**: Reduced repeat errors
- **Priority**: High

---

## How to Add New Lessons

1. Identify the pattern or issue from interactions
2. Add entry with: Lesson, Source, Priority (Critical/High/Medium/Low)
3. Update planning rules in planner.py if needed
4. Test with sample queries

Last updated: 2024-02-28


## Lessons - 2026-02-28T18:03:39.762572
- Structured responses with bold headers improve clarity


## Lessons - 2026-02-28T18:04:43.929696
- Structured responses with bold headers improve clarity
