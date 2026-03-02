---
name: detect_emotion
description: Detect the emotional tone of a user's message to adapt your response style.
---

# Detect Emotion

Use this skill when you sense frustration, excitement, urgency, or other emotional cues.

## How to use

    exec python src/conversation/emotional_intelligence.py detect --text "<the user's message>"

Returns the detected emotion and a recommended response tone.
