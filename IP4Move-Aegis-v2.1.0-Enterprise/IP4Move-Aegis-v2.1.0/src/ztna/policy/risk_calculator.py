"""
风险计算器模块

计算多因子风险评分
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

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


class RiskCalculator:
    """
    风险计算器
    
    基于多因子计算风险评分
    """
    
    def __init__(self, config: Optional[dict] = None):
        self.config = config or {}
        self.enabled = self.config.get("enabled", True)
        self.thresholds = self.config.get("thresholds", {
            "low": 30,
            "medium": 60,
            "high": 80
        })
        self._initialized = False
        
    async def initialize(self) -> None:
        """初始化"""
        if self._initialized:
            return
        logger.info("初始化风险计算器...")
        self._initialized = True
        logger.info("风险计算器初始化完成")
        
    async def shutdown(self) -> None:
        """关闭"""
        self._initialized = False
        logger.info("风险计算器已关闭")
        
    def calculate(self, factors: RiskFactors) -> RiskScore:
        """
        计算风险评分
        
        Args:
            factors: 风险因子
            
        Returns:
            风险评分
        """
        # 加权计算
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
        
        # 确定风险等级
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
        """获取统计信息"""
        return {
            "enabled": self.enabled,
            "thresholds": self.thresholds
        }
