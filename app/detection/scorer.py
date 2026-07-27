import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class DetectionDecision(str, Enum):
    ALLOW = "allow"
    FLAG = "flag"
    BLOCK = "block"


@dataclass
class RiskScore:
    score: float
    decision: DetectionDecision
    triggered_rules: list[str] = field(default_factory=list)
    max_severity: str = "none"
    threshold_block: float = 0.7
    threshold_flag: float = 0.3


class Scorer:
    """Aggregates detection signals into a risk score and decision."""

    def __init__(
        self,
        block_threshold: float = 0.7,
        flag_threshold: float = 0.3,
    ):
        self.block_threshold = block_threshold
        self.flag_threshold = flag_threshold

    def compute(self, matches: list) -> RiskScore:
        """
        Compute risk score from a list of match objects.
        Each match must have: weight, severity, rule_id attributes.
        """
        if not matches:
            return RiskScore(
                score=0.0,
                decision=DetectionDecision.ALLOW,
                triggered_rules=[],
                max_severity="none",
                threshold_block=self.block_threshold,
                threshold_flag=self.flag_threshold,
            )

        # Severity multiplier
        severity_multiplier = {
            "low": 0.5,
            "medium": 1.0,
            "high": 1.5,
        }

        # Weighted aggregation
        weighted_sum = 0.0
        total_weight = 0.0
        triggered = []
        max_sev = "none"
        sev_order = {"none": 0, "low": 1, "medium": 2, "high": 3}

        for m in matches:
            mult = severity_multiplier.get(m.severity, 1.0)
            weighted_sum += m.weight * mult
            total_weight += 1.0
            triggered.append(m.rule_id)

            # Track max severity
            if sev_order.get(m.severity, 0) > sev_order.get(max_sev, 0):
                max_sev = m.severity

        # Normalize score to 0-1 range
        score = min(weighted_sum / max(total_weight, 1.0), 1.0)

        # Decision logic
        if score >= self.block_threshold:
            # Only block if there are high-severity matches
            if max_sev == "high":
                decision = DetectionDecision.BLOCK
            else:
                decision = DetectionDecision.FLAG
        elif score >= self.flag_threshold:
            decision = DetectionDecision.FLAG
        else:
            decision = DetectionDecision.ALLOW

        logger.debug(
            "Risk score: %.2f, decision: %s, rules: %s",
            score, decision.value, triggered,
        )

        return RiskScore(
            score=round(score, 4),
            decision=decision,
            triggered_rules=triggered,
            max_severity=max_sev,
            threshold_block=self.block_threshold,
            threshold_flag=self.flag_threshold,
        )
