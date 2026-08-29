from __future__ import annotations

import re

# Patterns that indicate a potential secret or sensitive value
SECRET_PATTERNS = [
    re.compile(r"[A-Z0-9]{20,}", re.IGNORECASE),        # Generic long uppercase tokens
    re.compile(r"sk-[a-zA-Z0-9]{32,}"),                  # OpenAI-style keys
    re.compile(r"ghp_[a-zA-Z0-9]{36}"),                  # GitHub personal access tokens
    re.compile(r"(AWS_|GROQ_|ANTHROPIC_)[A-Z_]+=\S+"),  # Env var patterns
]

INJECTION_MARKERS = [
    "ignore previous instructions",
    "ignore all prior instructions",
    "disregard your system prompt",
    "you are now",
    "your new instructions are",
    "exfiltrate",
    "send to http",
]


def scan_for_secrets(text: str) -> list[str]:
    """Return a list of matched secret patterns found in text."""
    findings = []
    for pattern in SECRET_PATTERNS:
        if pattern.search(text):
            findings.append(pattern.pattern)
    return findings


def detect_injection(text: str) -> bool:
    """Return True if the text contains prompt injection markers."""
    lowered = text.lower()
    return any(marker in lowered for marker in INJECTION_MARKERS)
