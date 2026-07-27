import logging
from dataclasses import dataclass, field
from typing import Optional

from app.config import settings
from app.detection.normalizer import normalize, NormalizedOutput
from app.detection.rules_engine import RulesEngine, RuleMatch
from app.detection.scorer import Scorer, RiskScore, DetectionDecision

logger = logging.getLogger(__name__)


@dataclass
class DetectionResult:
    risk_score: float
    decision: DetectionDecision
    triggered_rules: list[str]
    normalized_text: str
    has_invisible_chars: bool
    homoglyphs_found: int
    encoding_detected: Optional[str]
    max_severity: str = "none"
    blocked: bool = False
    flagged: bool = False

    def __post_init__(self):
        self.blocked = self.decision == DetectionDecision.BLOCK
        self.flagged = self.decision == DetectionDecision.FLAG


class DetectionPipeline:
    """Main pipeline: normalize -> run rules -> compute score -> decide."""

    def __init__(self):
        self.rules_engine = RulesEngine(
            rules_dir=settings.detection_rules_dir,
        )
        self.scorer = Scorer(
            block_threshold=settings.detection_block_threshold,
            flag_threshold=settings.detection_flag_threshold,
        )
        self._loaded = False

    def load(self) -> None:
        """Load rules (call once at startup)."""
        if not self._loaded:
            self.rules_engine.load_rules()
            self._loaded = True

    def run(self, messages_texts: list[str]) -> DetectionResult:
        """Run the full detection pipeline on a list of message texts."""
        if not settings.detection_enabled:
            return DetectionResult(
                risk_score=0.0,
                decision=DetectionDecision.ALLOW,
                triggered_rules=[],
                normalized_text="",
                has_invisible_chars=False,
                homoglyphs_found=0,
                encoding_detected=None,
            )

        self.load()

        # Combine all messages for analysis
        combined = "\n".join(messages_texts)

        # 1. Normalize
        normalized: NormalizedOutput = normalize(combined)

        # 2. Run rules on normalized text
        matches: list[RuleMatch] = self.rules_engine.match(normalized.normalized)

        # 3. Compute risk score
        risk: RiskScore = self.scorer.compute(matches)

        # 4. Build result
        return DetectionResult(
            risk_score=risk.score,
            decision=risk.decision,
            triggered_rules=risk.triggered_rules,
            normalized_text=normalized.normalized[:200],
            has_invisible_chars=normalized.has_invisible_chars,
            homoglyphs_found=len(normalized.homoglyphs_found),
            encoding_detected=normalized.encoding_detected,
            max_severity=risk.max_severity,
        )
