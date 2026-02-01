import os
import re
from dataclasses import dataclass
from typing import List, Dict, Any, Optional


@dataclass
class Rule:
    name: str
    patterns: List[re.Pattern]


def resolve_rules_path() -> str:
    """Resolve the YAML path used for category rules."""
    path = os.environ.get("MONEY_BACKWARD_CATEGORIES_YAML")
    if path:
        return path
    if os.path.exists("dashboard/categories.yaml"):
        return "dashboard/categories.yaml"
    return "dashboard/categories.example.yaml"


def load_rules() -> tuple[List[Rule], str]:
    """Load category rules.

    Priority:
      1) MONEY_BACKWARD_CATEGORIES_YAML env
      2) ./dashboard/categories.yaml
      3) ./dashboard/categories.example.yaml

    Returns (rules, default_category)
    """
    path = resolve_rules_path()

    data = _read_yaml(path)
    rules_raw = data.get("rules", [])
    default = data.get("default", "Uncategorized")

    rules: List[Rule] = []
    for r in rules_raw:
        name = str(r.get("name"))
        pats = [re.compile(p, flags=re.IGNORECASE) for p in r.get("patterns", [])]
        rules.append(Rule(name=name, patterns=pats))

    return rules, str(default)


def categorize(description: str, rules: List[Rule], default: str) -> str:
    for rule in rules:
        for pat in rule.patterns:
            if pat.search(description or ""):
                return rule.name
    return default


def add_rule_pattern(
    *,
    path: str,
    category: str,
    pattern: str,
    create_if_missing: bool = True,
) -> None:
    """Append a pattern to a category rule in YAML.

    - If category exists: append pattern (if not already present)
    - Else if create_if_missing: create a new rule entry.

    Raises if YAML can't be loaded/saved.
    """
    data = _read_yaml(path)
    rules = data.get("rules")
    if not isinstance(rules, list):
        rules = []
        data["rules"] = rules

    target = None
    for r in rules:
        if isinstance(r, dict) and str(r.get("name")) == category:
            target = r
            break

    if target is None:
        if not create_if_missing:
            raise RuntimeError(f"Category '{category}' not found in {path}")
        target = {"name": category, "patterns": []}
        rules.append(target)

    pats = target.get("patterns")
    if not isinstance(pats, list):
        pats = []
        target["patterns"] = pats

    if pattern not in pats:
        pats.append(pattern)

    _write_yaml(path, data)


def _read_yaml(path: str) -> Dict[str, Any]:
    try:
        import yaml  # type: ignore

        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError:
        return {}
    except Exception as e:
        raise RuntimeError(f"Failed to read YAML rules from {path}: {e}")


def _write_yaml(path: str, data: Dict[str, Any]) -> None:
    try:
        import yaml  # type: ignore

        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)
    except Exception as e:
        raise RuntimeError(f"Failed to write YAML rules to {path}: {e}")
