"""
风险计算器模块

计算多因子风险评分
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from src.common.base_component import BaseComponent

logger = logging.getLogger(__name__)


@dataclass
class RiskFactors:
    """风险因子"""
    authentication_risk: float = 0.0
    device_risk: float = 0.0
    behavior_risk: float = 0.0
    location_risk: float = 0.0
    time_risk: float = 0.0
    threat_intel_risk: float = 0.0


@dataclass
class RiskScore:
    """风险评分"""
    score: float
    level: str
    factors: RiskFactors
    timestamp: datetime

    def to_dict(self) -> dict[str, Any]:
        return {
            "score": self.score,
            "level": self.level,
            "factors": {
                "authentication_risk": self.factors.authentication_risk,
                "device_risk": self.factors.device_risk,
                "behavior_risk": self.factors.behavior_risk,
                "location_risk": self.factors.location_risk,
                "time_risk": self.factors.time_risk,
                "threat_intel_risk": self.factors.threat_intel_risk
            },
            "timestamp": self.timestamp.isoformat()
        }


class RiskCalculator(BaseComponent):
    """
    风险计算器

    基于多因子计算风险评分
    """

    @property
    def component_name(self) -> str:
        return "风险计算器"

    def __init__(self, config: Optional[dict] = None):
        super().__init__(config)
        self.thresholds = self.config.get("thresholds", {
            "low": 30,
            "medium": 60,
            "high": 80
        })

    def calculate(self, factors: RiskFactors) -> RiskScore:
        """
        计算风险评分

        Args:
            factors: 风险因子

        Returns:
            风险评分
        """
        weights = {
            "authentication": 0.25,
            "device": 0.20,
            "behavior": 0.20,
            "location": 0.15,
            "time": 0.10,
            "threat_intel": 0.10
        }

        score = (
            factors.authentication_risk * weights["authentication"] +
            factors.device_risk * weights["device"] +
            factors.behavior_risk * weights["behavior"] +
            factors.location_risk * weights["location"] +
            factors.time_risk * weights["time"] +
            factors.threat_intel_risk * weights["threat_intel"]
        ) * 100

        if score < self.thresholds["low"]:
            level = "low"
        elif score < self.thresholds["medium"]:
            level = "medium"
        elif score < self.thresholds["high"]:
            level = "high"
        else:
            level = "critical"

        return RiskScore(
            score=score,
            level=level,
            factors=factors,
            timestamp=datetime.utcnow()
        )

    def get_stats(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "thresholds": self.thresholds
        }
