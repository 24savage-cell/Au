"""
策略决策点模块

评估访问请求并做出决策
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

from src.common.base_component import BaseComponent

logger = logging.getLogger(__name__)


class DecisionResult(Enum):
    """决策结果"""
    PERMIT = "permit"
    DENY = "deny"
    NOT_APPLICABLE = "not_applicable"
    INDETERMINATE = "indeterminate"


@dataclass
class DecisionRequest:
    """决策请求"""
    subject_id: str
    resource_id: str
    action: str
    environment: dict[str, Any]


@dataclass
class DecisionResponse:
    """决策响应"""
    result: DecisionResult
    obligations: list[str]
    advice: list[str]


class PolicyDecisionPoint(BaseComponent):
    """
    策略决策点

    评估访问请求并返回决策
    """

    @property
    def component_name(self) -> str:
        return "策略决策点"

    async def evaluate(self, request: DecisionRequest) -> DecisionResponse:
        """
        评估请求

        Args:
            request: 决策请求

        Returns:
            决策响应
        """
        logger.info(f"评估请求: {request.subject_id} -> {request.resource_id}")

        return DecisionResponse(
            result=DecisionResult.PERMIT,
            obligations=[],
            advice=["继续监控"]
        )

    def get_stats(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled
        }
