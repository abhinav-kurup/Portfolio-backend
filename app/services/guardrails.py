# app/services/chat/guardrails.py

from __future__ import annotations

import re


# prompt injection / jailbreak
BLOCKED_PATTERNS = [
    "ignore previous instructions",
    "ignore all instructions",
    "reveal system prompt",
    "reveal your prompt",
    "show your instructions",
    "show hidden prompt",
    "print system prompt",
    "developer mode",
    "dan mode",
    "jailbreak",
    "ignore safety",
    "bypass guardrails",
    "forget your rules",
]

# disallowed roleplay / evaluation prompts
BLOCKED_EVAL_PATTERNS = [
    "assume you are a recruiter",
    "act as a recruiter",
    "pretend you are a recruiter",
    "assume you are hiring",
    "act as a hiring manager",
    "would you hire",
    "should i hire",
    "is he a good fit",
    "is he suitable",
    "is he worth hiring",
    "rate this candidate",
    "evaluate this candidate",
    "judge this candidate",
    "judge this profile",
    "score this candidate",
    "how good is abhinav",
    "is abhinav good enough",
    "is this candidate strong",
    "would he pass",
    "would he get hired",
]

# explicit out-of-scope topics
BLOCKED_TOPICS = {
    "politics",
    "religion",
    "relationship",
    "girlfriend",
    "boyfriend",
    "salary",
    "medical",
    "diagnosis",
    "therapy",
    "prescription",
}

# allowed portfolio anchors
ALLOWED_TOPICS = {
    "abhinav",
    "experience",
    "project",
    "projects",
    "backend",
    "python",
    "django",
    "fastapi",
    "aws",
    "cloud",
    "docker",
    "api",
    "system",
    "architecture",
    "database",
    "postgres",
    "redis",
    "llm",
    "ai",
    "rag",
    "langgraph",
    "collabwrite",
    "documind",
    "ebeat",
    "e-beat",
    "workforce",
    "event",
    "certification",
    "skills",
    "resume",
    "background",
    "hire",
    "contact",
}


def _normalize(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"\s+", " ", text)
    return text


def is_in_scope(query: str) -> bool:
    text = _normalize(query)

    if not text:
        return False

    # prompt injection / jailbreak
    if any(pattern in text for pattern in BLOCKED_PATTERNS):
        return False

    # roleplay / hiring simulation / subjective evaluation
    if any(pattern in text for pattern in BLOCKED_EVAL_PATTERNS):
        return False

    # explicit out-of-scope domains
    if any(topic in text for topic in BLOCKED_TOPICS):
        return False

    # must be portfolio-related
    # if not any(topic in text for topic in ALLOWED_TOPICS):
    #     return False

    return True