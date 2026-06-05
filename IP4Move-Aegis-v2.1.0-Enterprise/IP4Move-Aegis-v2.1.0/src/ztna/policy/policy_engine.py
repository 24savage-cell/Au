"""
ABAC策略引擎模块

提供属性基访问控制策略评估
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

from src.common.base_component import BaseComponent

logger = logging.getLogger(__name__)


class PolicyDecision(Enum):
    """策略决策结果"""
    PERMIT = "permit"
    DENY = "deny"
    NOT_APPLICABLE = "not_applicable"
    INDETERMINATE = "indeterminate"


@dataclass
class ABACPolicy:
    """ABAC策略"""
    policy_id: str
    name: str
    description: str
    subject_attributes: dict[str, Any]
    resource_attributes: dict[str, Any]
    action_attributes: dict[str, Any]
    environment_attributes: dict[str, Any]
    effect: PolicyDecision
    priority: int
    enabled: bool = True


class PolicyEngine(BaseComponent):
    """
    ABAC策略引擎

    评估属性基访问控制策略
    """

    @property
    def component_name(self) -> str:
        return "策略引擎"

    def __init__(self, config: Optional[dict] = None):
        super().__init__(config)
        self._policies: list[ABACPolicy] = []

    def add_policy(self, policy: ABACPolicy) -> None:
        """添加策略"""
        self._policies.append(policy)
        self._policies.sort(key=lambda p: p.priority, reverse=True)

    def evaluate(
        self,
        subject: dict[str, Any],
        resource: dict[str, Any],
        action: dict[str, Any],
        environment: dict[str, Any]
    ) -> PolicyDecision:
        """
        评估策略

        Args:
            subject: 主体属性
            resource: 资源属性
            action: 操作属性
            environment: 环境属性

        Returns:
            决策结果
        """
        if not self.enabled:
            return PolicyDecision.PERMIT

        for policy in self._policies:
            if not policy.enabled:
                continue

            if self._match_policy(policy, subject, resource, action, environment):
                return policy.effect

        return PolicyDecision.NOT_APPLICABLE

    def _match_policy(
        self,
        policy: ABACPolicy,
        subject: dict,
        resource: dict,
        action: dict,
        environment: dict
    ) -> bool:
        """匹配策略"""
        return (
            self._match_attributes(policy.subject_attributes, subject) and
            self._match_attributes(policy.resource_attributes, resource) and
            self._match_attributes(policy.action_attributes, action) and
            self._match_attributes(policy.environment_attributes, environment)
        )

    def _match_attributes(self, required: dict, actual: dict) -> bool:
        """匹配属性"""
        for key, value in required.items():
            if key not in actual or actual[key] != value:
                return False
        return True

    def get_stats(self) -> dict[str, Any]:
        return {
            "policies": len(self._policies),
            "enabled": self.enabled
        }
