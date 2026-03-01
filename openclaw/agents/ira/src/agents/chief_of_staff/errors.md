# Error Log & Prevention Guide

This file tracks errors encountered and how to prevent them in future planning.

## Critical Errors

### ERR-001: Incorrect AM Series Thickness
- **Date**: 2024-01-15
- **Description**: Stated AM-500 can process 2mm material (incorrect - max is 1.5mm)
- **Impact**: Customer confusion, credibility issue
- **Root Cause**: Researcher pulled outdated spec sheet
- **Prevention**: fact_checker MUST validate all AM series thickness claims
- **Status**: Guardrail added

### ERR-002: Missing Pricing Disclaimer
- **Date**: 2024-01-22
- **Description**: Quote sent without "subject to configuration" disclaimer
- **Impact**: Customer expected quoted price as final
- **Root Cause**: Writer skipped disclaimer template
- **Prevention**: fact_checker validates all pricing responses have disclaimer
- **Status**: Guardrail added

### ERR-003: Competitor Misidentification
- **Date**: 2024-02-01
- **Description**: Identified Plastiform as competitor (they're actually our customer)
- **Impact**: Relationship concern, unprofessional
- **Root Cause**: Researcher didn't check CRM before competitor research
- **Prevention**: Always check identity/CRM before competitor classification
- **Status**: Planning rule added

## Warning Patterns

### WARN-001: Incomplete Research
- **Pattern**: Answers that say "I don't have information" when data exists
- **Trigger**: Single-source lookup failure
- **Mitigation**: Researcher should query 3+ sources before declaring no data
- **Status**: Monitoring

### WARN-002: Tone Mismatch
- **Pattern**: Overly formal emails to established customers, casual to new leads
- **Trigger**: Missing recipient context in writer delegation
- **Mitigation**: Chief of Staff must pass relationship stage to writer
- **Status**: Planning rule added

### WARN-003: Slow Response on Urgent Queries
- **Pattern**: Complex planning for simple urgent questions
- **Trigger**: Over-delegation for "ASAP" marked queries
- **Mitigation**: Detect urgency and use fast-path for simple questions
- **Status**: Planning rule added

## Hallucination Prevention

### Never Generate
- Machine models that don't exist in our catalog
- Prices without checking machine_database
- Delivery times without checking operations
- Competitor product specifications without research

### Always Verify
- Any numerical specification (dimensions, power, capacity)
- Pricing and discount information
- Customer history and past purchases
- Lead times and availability

## Recovery Procedures

### When Fact Checker Fails Validation
1. Log the specific failure reason
2. Route back to researcher for correction
3. If 3+ failures, escalate to human review
4. Update errors.md with new pattern

### When Agent Times Out
1. Return partial results with disclaimer
2. Log timeout for pattern analysis
3. Consider breaking into smaller tasks next time

### When Conflicting Sources Found
1. Prefer authoritative sources (machine_database > emails)
2. Note conflict in response if relevant
3. Flag for human review if pricing related

---

## Error Analysis Dashboard

| Category | Count (30d) | Trend |
|----------|-------------|-------|
| Specification errors | 2 | ↓ |
| Pricing errors | 1 | ↓ |
| Tone issues | 3 | → |
| Timeout errors | 5 | ↑ |

## Adding New Errors

When a new error occurs:
1. Assign ERR-XXX or WARN-XXX ID
2. Document: Date, Description, Impact, Root Cause
3. Define Prevention rule
4. Update planner.py if structural change needed
5. Set Status: Open → In Progress → Resolved/Monitoring

Last updated: 2024-02-28
