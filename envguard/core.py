"""Core parsing + schema validation for envguard."""

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class ValidationError:
    key: str
    message: str


@dataclass
class ValidationResult:
    errors: List[ValidationError] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def __bool__(self) -> bool:  # convenience: if result:
        return self.ok


def parse_env(text: str) -> Dict[str, str]:
    """Parse .env text into a dict.

    Skips blank lines and comments. Strips surrounding quotes.
    """
    result: Dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        result[key] = val
    return result


def validate(env: Dict[str, str], schema: Dict[str, dict]) -> ValidationResult:
    """Validate parsed env against a schema.

    schema form:
        {
            "API_URL": {"required": True, "type": "url"},
            "PORT":    {"required": True, "type": "int"},
            "DEBUG":   {"required": False, "type": "bool"},
        }
    Supported types: str, int, bool, url.
    Unknown keys present in env but absent from schema are flagged.
    """
    res = ValidationResult()

    for key, spec in schema.items():
        required = spec.get("required", False)
        if required and key not in env:
            res.errors.append(ValidationError(key, "missing required key"))
            continue
        if key in env and "type" in spec:
            val = env[key]
            t = spec["type"]
            if t == "int" and not _is_int(val):
                res.errors.append(ValidationError(key, f"expected int, got {val!r}"))
            elif t == "bool" and not _is_bool(val):
                res.errors.append(ValidationError(key, f"expected bool, got {val!r}"))
            elif t == "url" and not _is_url(val):
                res.errors.append(ValidationError(key, f"expected url, got {val!r}"))

    for key in env:
        if key not in schema:
            res.errors.append(ValidationError(key, "unknown key not declared in schema"))

    return res


def _is_int(v: str) -> bool:
    try:
        int(v)
        return True
    except (ValueError, TypeError):
        return False


def _is_bool(v: str) -> bool:
    return v.lower() in ("true", "false", "1", "0", "yes", "no")


def _is_url(v: str) -> bool:
    return bool(re.match(r"^https?://", v))
