import os
import re
from dataclasses import dataclass
from typing import List, Dict, Any


@dataclass
class Rule:
    name: str
    patterns: List[re.Pattern]


def load_rules() -> tuple[List[Rule], str]:
    """Load category rules.

    Priority:
      1) MONEY_BACKWARD_CATEGORIES_YAML env
      2) ./dashboard/categories.yaml
      3) ./dashboard/categories.example.yaml

    Returns (rules, default_category)
    """
    path = os.environ.get("MONEY_BACKWARD_CATEGORIES_YAML")
    if not path:
        if os.path.exists("dashboard/categories.yaml"):
            path = "dashboard/categories.yaml"
        else:
            path = "dashboard/categories.example.yaml"

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


def _read_yaml(path: str) -> Dict[str, Any]:
    # Avoid adding a dependency. Use PyYAML if available, else minimal parser.
    try:
        import yaml  # type: ignore

        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception:
        # Minimal fallback: fail with guidance.
        raise RuntimeError(
            f"Failed to read YAML rules from {path}. Install PyYAML: pip install pyyaml"
        )
