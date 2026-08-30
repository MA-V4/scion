from __future__ import annotations

import re
from dataclasses import dataclass

INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions?", re.IGNORECASE),
    re.compile(r"disregard\s+(your\s+)?(system\s+)?(prompt|instructions?)", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+", re.IGNORECASE),
    re.compile(r"your\s+new\s+(role|instructions?|persona|task)\s+(is|are)", re.IGNORECASE),
    re.compile(r"act\s+as\s+(if\s+you\s+are|a\s+)", re.IGNORECASE),
    re.compile(r"forget\s+(everything|all)\s+(you\s+)?(know|were\s+told)", re.IGNORECASE),
    re.compile(
        r"(send|upload|exfiltrate|transmit)\s+.{0,30}(to\s+http|to\s+\S+\.com)", re.IGNORECASE
    ),
    re.compile(r"reveal\s+(your\s+)?(system\s+prompt|instructions?|api\s+key)", re.IGNORECASE),
    re.compile(r"print\s+(your\s+)?(system\s+prompt|instructions?)", re.IGNORECASE),
    re.compile(r"(rm|del|delete|drop)\s+.{0,20}(database|table|all\s+files?)", re.IGNORECASE),
]

SECRET_PATTERNS = [
    re.compile(r"sk-[a-zA-Z0-9]{32,}"),
    re.compile(r"ghp_[a-zA-Z0-9]{36}"),
    re.compile(r"(AWS|GROQ|ANTHROPIC|OPENAI)_[A-Z_]+=\S+"),
    re.compile(r"Bearer\s+[a-zA-Z0-9\-._~+/]{20,}"),
    re.compile(r"password\s*[:=]\s*\S{8,}", re.IGNORECASE),
]


@dataclass
class ScanResult:
    is_injection: bool
    has_secrets: bool
    injection_matches: list[str]
    secret_matches: list[str]

    @property
    def is_clean(self) -> bool:
        return not self.is_injection and not self.has_secrets


def scan(text: str) -> ScanResult:
    """Scan text for prompt injection attempts and secret leakage."""
    injection_matches = [p.pattern for p in INJECTION_PATTERNS if p.search(text)]
    secret_matches = [p.pattern for p in SECRET_PATTERNS if p.search(text)]

    return ScanResult(
        is_injection=len(injection_matches) > 0,
        has_secrets=len(secret_matches) > 0,
        injection_matches=injection_matches,
        secret_matches=secret_matches,
    )
