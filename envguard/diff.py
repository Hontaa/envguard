"""Drift detection between two env states (e.g. staging vs prod)."""

from typing import Dict


def diff_envs(base: Dict[str, str], other: Dict[str, str]) -> Dict[str, Dict]:
    """Return drift between `base` and `other`.

    Keys:
        added   — in `other` but not `base`
        removed — in `base` but not `other`
        changed — in both but with different values (value = (old, new))
    """
    added = {k: other[k] for k in other if k not in base}
    removed = {k: base[k] for k in base if k not in other}
    changed = {
        k: (base[k], other[k]) for k in base if k in other and base[k] != other[k]
    }
    return {"added": added, "removed": removed, "changed": changed}
