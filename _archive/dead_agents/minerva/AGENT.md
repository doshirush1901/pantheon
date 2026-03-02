# Minerva

**Role:** Knowledge-Grounded Pre-Send Coach

Minerva reviews every email draft against the actual machine database before sending. She catches hallucinations, enforces specs, and nudges Ira to the right source.

## What Minerva Does

- Pulls ground truth from `MACHINE_SPECS` and `SERIES_KNOWLEDGE` for every machine mentioned in a draft
- Detects critical business rule violations (AM thickness > 1.5mm, missing IMG recommendation for grain/TPO, missing pricing disclaimers)
- Scores drafts on factual accuracy, completeness, tone, and spec correctness
- Returns a verdict: **APPROVE** or **REVISE**
- When revising, provides specific correction guidance and nearest-neighbor hints from the database

## Verdict

| Verdict | Meaning |
|---------|---------|
| APPROVE | Draft is factually sound and ready to send |
| REVISE  | Draft contains errors, omissions, or rule violations — correction guidance attached |

## Part of the Pantheon

Minerva works alongside Athena, Clio, Iris, Calliope, Vera, and Sophia. She sits in the critical path between draft generation and send, ensuring nothing factually wrong ever reaches a customer.
