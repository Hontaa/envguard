"""envguard — Python-native validator for .env / config files.

Free OSS core. Paid layer (hosted dashboard, team alerts, secret-leak
history) lives behind an API key on the SaaS.
"""

from .core import parse_env, validate, ValidationResult, ValidationError
from .leaks import find_leaks
from .diff import diff_envs

__all__ = [
    "parse_env",
    "validate",
    "ValidationResult",
    "ValidationError",
    "find_leaks",
    "diff_envs",
]
