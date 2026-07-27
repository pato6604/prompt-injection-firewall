import re
import yaml
import logging
import os
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class Rule:
    id: str
    name: str
    description: str
    severity: str  # "low", "medium", "high"
    action: str    # "flag", "block"
    weight: float
    patterns: list[str]
    enabled: bool = True


@dataclass
class RuleMatch:
    rule_id: str
    rule_name: str
    severity: str
    action: str
    weight: float
    pattern_matched: str
    evidence: str  # the text snippet that matched
    score: float


class RulesEngine:
    def __init__(self, rules_dir: str = "app/detection/policies"):
        self.rules_dir = rules_dir
        self._rules: list[Rule] = []
        self._compiled: list[tuple[Rule, re.Pattern]] = []

    def load_rules(self) -> None:
        """Load all YAML rule files from the policies directory."""
        self._rules = []
        self._compiled = []

        if not os.path.isdir(self.rules_dir):
            logger.warning("Rules directory not found: %s", self.rules_dir)
            return

        for filename in sorted(os.listdir(self.rules_dir)):
            if not filename.endswith((".yaml", ".yml")):
                continue
            filepath = os.path.join(self.rules_dir, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                if not data or "rules" not in data:
                    continue
                for rule_data in data["rules"]:
                    rule = Rule(
                        id=rule_data["id"],
                        name=rule_data.get("name", rule_data["id"]),
                        description=rule_data.get("description", ""),
                        severity=rule_data.get("severity", "medium"),
                        action=rule_data.get("action", "flag"),
                        weight=float(rule_data.get("weight", 0.5)),
                        patterns=rule_data.get("patterns", []),
                        enabled=rule_data.get("enabled", True),
                    )
                    self._rules.append(rule)
                    # Pre-compile all patterns
                    for pattern in rule.patterns:
                        try:
                            compiled = re.compile(pattern, re.IGNORECASE)
                            self._compiled.append((rule, compiled))
                        except re.error as e:
                            logger.error(
                                "Invalid regex in rule '%s': %s - %s",
                                rule.id, pattern, e,
                            )
                logger.info(
                    "Loaded %d rules from %s", len(data["rules"]), filename
                )
            except Exception as e:
                logger.error(
                    "Failed to load rules from %s: %s", filepath, e
                )

        logger.info(
            "Total rules loaded: %d, compiled patterns: %d",
            len(self._rules),
            len(self._compiled),
        )

    def match(self, text: str) -> list[RuleMatch]:
        """Run all compiled patterns against the given text."""
        matches = []
        for rule, pattern in self._compiled:
            found = pattern.findall(text)
            if found:
                # Take the first match as evidence (up to 100 chars)
                evidence = str(found[0])[:100] if found else ""
                match = RuleMatch(
                    rule_id=rule.id,
                    rule_name=rule.name,
                    severity=rule.severity,
                    action=rule.action,
                    weight=rule.weight,
                    pattern_matched=pattern.pattern,
                    evidence=evidence,
                    score=rule.weight,
                )
                matches.append(match)
        return matches

    @property
    def rules(self) -> list[Rule]:
        return self._rules
