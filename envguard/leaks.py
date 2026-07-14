"""Secret-leak detection for envguard."""

import re
from typing import Dict, List, Tuple


SECRET_PATTERNS = {
    "AWS_ACCESS_KEY": re.compile(r"AKIA[0-9A-Z]{16}"),
    "PRIVATE_KEY": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "GENERIC_SECRET": re.compile(
        r"(?i)(secret|password|token|api[_-]?key)\s*=\s*\S{16,}"
    ),
}


def find_leaks(env: Dict[str, str]) -> List[Tuple[str, str]]:
    """Return list of (key, pattern_name) for any suspected secret values.

    Matches against both the value and the 'key=value' line so that
    high-entropy values behind obvious key names are caught too.
    """
    leaks: List[Tuple[str, str]] = []
    for key, val in env.items():
        line = f"{key}={val}"
        for name, pat in SECRET_PATTERNS.items():
            if pat.search(val) or pat.search(line):
                leaks.append((key, name))
                break
    return leaks
