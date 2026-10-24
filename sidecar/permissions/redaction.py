"""
Secret Redaction Engine for Swarm.
Redacts API keys, tokens, private keys, and ambient environment secrets
from all outgoing events, logs, audit records, and tool arguments.
"""

import os
import re
from typing import Any, Dict, List, Optional, Union

# Regex patterns for common credentials and secret token formats
SECRET_REGEX_PATTERNS: List[re.Pattern] = [
    # Private Key blocks (RSA, EC, OPENSSH, etc.)
    re.compile(r"-----BEGIN [A-Z\s]+ PRIVATE KEY-----[\s\S]+?-----END [A-Z\s]+ PRIVATE KEY-----", re.MULTILINE),
    # Prefixed API keys (NVIDIA, TinyFish, OpenAI, GitHub, Slack, etc.)
    re.compile(r"\b(?:sk|nvapi|tf|ghp|gho|glpat|xoxb|xoxp|live|test)[_-][a-zA-Z0-9_\-]{14,}\b"),
    # JSON Web Tokens (JWT)
    re.compile(r"\beyJ[a-zA-Z0-9_\-]{10,}\.eyJ[a-zA-Z0-9_\-]{10,}\.[a-zA-Z0-9_\-]{10,}\b"),
    # Bearer tokens in headers or logs
    re.compile(r"(?i)(bearer\s+)[a-zA-Z0-9_\-\.]{16,}"),
    # Key-value secret patterns in json/yaml/cli (e.g. api_key="...", password: "...")
    re.compile(r"(?i)(\"?(?:api[_-]?key|secret|password|access[_-]?token|auth[_-]?token)\"?\s*[:=]\s*['\"]?)([^'\"\s\r\n]{6,})(['\"]?)"),
]

REDACTED_MARKER = "[REDACTED_SECRET]"


def get_ambient_secret_values() -> List[str]:
    """
    Collects string values of sensitive environment variables currently set in os.environ.
    Only captures values of length >= 5 to avoid false-positive replacement of short booleans/numbers.
    """
    secrets: List[str] = []
    sensitive_substrings = ("KEY", "SECRET", "TOKEN", "PASSWORD", "AUTH", "API", "NVIDIA", "OPENROUTER", "TINYFISH")

    for env_name, env_val in os.environ.items():
        name_upper = env_name.upper()
        if (any(sub in name_upper for sub in sensitive_substrings) or name_upper.startswith("SWARM_")) and len(env_val.strip()) >= 5:
            val_clean = env_val.strip()
            # Avoid trivial values
            if val_clean.lower() not in ("true", "false", "mock", "live", "strict", "demo", "none"):
                secrets.append(val_clean)

    # Sort descending by length so longer tokens are redacted before substrings
    secrets.sort(key=len, reverse=True)
    return secrets


def redact(text: Optional[Union[str, bytes]]) -> str:
    """
    Redacts secrets from a string or bytes using regex patterns and ambient environment values.
    """
    if text is None:
        return ""
    if isinstance(text, bytes):
        text = text.decode("utf-8", errors="replace")

    result = str(text)

    # 1. Redact known ambient environment secrets first
    for secret in get_ambient_secret_values():
        if secret in result:
            result = result.replace(secret, REDACTED_MARKER)

    # 2. Redact via regex patterns
    # Private keys
    result = SECRET_REGEX_PATTERNS[0].sub(REDACTED_MARKER, result)
    # Prefixed API keys
    result = SECRET_REGEX_PATTERNS[1].sub(REDACTED_MARKER, result)
    # JWTs
    result = SECRET_REGEX_PATTERNS[2].sub(REDACTED_MARKER, result)
    # Bearer tokens
    result = SECRET_REGEX_PATTERNS[3].sub(rf"\g<1>{REDACTED_MARKER}", result)
    # Key-value pairs
    result = SECRET_REGEX_PATTERNS[4].sub(rf"\g<1>{REDACTED_MARKER}\g<3>", result)

    return result


def redact_data(data: Any) -> Any:
    """
    Recursively redacts dictionary, list, tuple, and scalar values.
    """
    if data is None:
        return None
    if isinstance(data, (str, bytes)):
        return redact(data)
    if isinstance(data, dict):
        return {k: redact_data(v) for k, v in data.items()}
    if isinstance(data, list):
        return [redact_data(v) for v in data]
    if isinstance(data, tuple):
        return tuple(redact_data(v) for v in data)
    return data
