---
name: assess_confidence
description: Assess your confidence level in a response before sending it to the user.
---

# Assess Confidence

Use this skill when you are unsure about the accuracy of your response.

## How to use

    exec python src/memory/metacognition.py assess --text "<your draft response to evaluate>"

Returns a confidence score and flags any claims that may need verification.
