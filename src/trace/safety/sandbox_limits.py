"""Safety mechanisms and sandbox limits for TRACE execution."""

import os
from pathlib import Path
import re
import sys
from typing import Dict, List, Optional, Set

# Sandbox limits
DEFAULT_TIMEOUT_SECONDS: float = 5.0
MAX_TIMEOUT_SECONDS: float = 15.0
MAX_OUTPUT_BYTES: int = 10 * 1024  # 10 KB max output limit
MAX_FILE_SIZE_BYTES: int = 256 * 1024  # 256 KB max source file size

# Sensitive environment variable patterns to scrub
SENSITIVE_ENV_PATTERNS: List[re.Pattern] = [
    re.compile(r".*KEY.*", re.IGNORECASE),
    re.compile(r".*SECRET.*", re.IGNORECASE),
    re.compile(r".*TOKEN.*", re.IGNORECASE),
    re.compile(r".*PASSWORD.*", re.IGNORECASE),
    re.compile(r".*AUTH.*", re.IGNORECASE),
    re.compile(r"^AWS_.*", re.IGNORECASE),
    re.compile(r"^AZURE_.*", re.IGNORECASE),
    re.compile(r"^GCP_.*", re.IGNORECASE),
    re.compile(r"^DATABASE_URL.*", re.IGNORECASE),
    re.compile(r"^GEMINI_.*", re.IGNORECASE),
    re.compile(r"^OPENAI_.*", re.IGNORECASE),
    re.compile(r"^ANTHROPIC_.*", re.IGNORECASE),
]


class SafetyViolationError(Exception):
    """Raised when an operation violates safety sandbox constraints."""
    pass


def sanitize_environment(base_env: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    """
    Produce a sanitized environment for subprocess execution by stripping
    any secrets, API keys, credentials, and dangerous environment variables.
    """
    source_env = base_env or os.environ
    safe_env: Dict[str, str] = {}
    
    # Standard minimal environment variables required for Python runtime
    safe_keys: Set[str] = {
        "SYSTEMROOT",
        "PATH",
        "PATHEXT",
        "TEMP",
        "TMP",
        "COMSPEC",
        "WINDIR",
        "LANG",
        "LC_ALL",
        "PYTHONPATH",
        "PYTHONHOME",
        "HOME",
        "USERPROFILE",
    }
    
    for key, value in source_env.items():
        # Reject if matches sensitive pattern
        if any(pat.match(key) for pat in SENSITIVE_ENV_PATTERNS):
            continue
            
        key_upper = key.upper()
        if key_upper in safe_keys or key in safe_keys:
            safe_env[key] = value
            
    # Force safe defaults
    safe_env["PYTHONDONTWRITEBYTECODE"] = "1"
    safe_env["PYTHONUNBUFFERED"] = "1"
    
    return safe_env


def validate_path_containment(
    target_path: str | Path,
    allowed_root: Optional[str | Path] = None,
    allow_temp: bool = True
) -> Path:
    """
    Validate that a path does not escape the allowed root directory.
    Prevents path traversal attacks (e.g. ../../../windows/system32).
    """
    resolved_target = Path(target_path).resolve()
    
    # Check if target exists or parent exists
    if not resolved_target.exists() and not resolved_target.parent.exists():
        raise SafetyViolationError(f"Target path does not exist: {target_path}")
        
    if allowed_root:
        resolved_root = Path(allowed_root).resolve()
        try:
            resolved_target.relative_to(resolved_root)
            return resolved_target
        except ValueError:
            # Check temp if allowed
            if allow_temp:
                import tempfile
                temp_dir = Path(tempfile.gettempdir()).resolve()
                try:
                    resolved_target.relative_to(temp_dir)
                    return resolved_target
                except ValueError:
                    pass
            raise SafetyViolationError(
                f"Path traversal blocked: '{target_path}' escapes allowed root '{resolved_root}'"
            )
            
    return resolved_target


def truncate_output(text: str, max_bytes: int = MAX_OUTPUT_BYTES) -> str:
    """Safely truncate standard output or error strings to prevent memory exhaustion."""
    if not text:
        return ""
    encoded = text.encode("utf-8", errors="replace")
    if len(encoded) <= max_bytes:
        return text
        
    truncated = encoded[:max_bytes].decode("utf-8", errors="ignore")
    omitted = len(encoded) - max_bytes
    return f"{truncated}\n... [OUTPUT TRUNCATED: {omitted} additional bytes omitted by TRACE safety limits]"
