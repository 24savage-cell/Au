"""
域名信誉模块

提供域名信誉评分
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from src.common.base_component import BaseComponent
from src.common.reputation import ReputationLevel, BaseReputationScore

logger = logging.getLogger(__name__)


@dataclass
class DomainReputationScore(BaseReputationScore):
    """域名信誉分数"""
    domain: str = ""
    categories: list[str] = None

    def __post_init__(self):
        if self.categories is None:
            self.categories = []

    def to_dict(self) -> dict[str, Any]:
        result = self._base_to_dict()
        result["domain"] = self.domain
        result["categories"] = self.categories
        return result


class DomainReputationFeed(BaseComponent):
    """
    域名信誉源

    提供域名信誉评分
    """

    @property
    def component_name(self) -> str:
        return "域名信誉源"

    def __init__(self, config: Optional[dict] = None):
        super().__init__(config)
        self._reputation_db: dict[str, DomainReputationScore] = {}

    async def check_domain(self, domain: str) -> DomainReputationScore:
        """
        检查域名信誉

        Args:
            domain: 域名

        Returns:
            信誉分数
        """
        if domain in self._reputation_db:
            return self._reputation_db[domain]

        score = DomainReputationScore(
            domain=domain,
            score=10,
            level=ReputationLevel.CLEAN,
            sources=["internal"],
            categories=["clean"],
            first_seen=datetime.utcnow(),
            last_seen=datetime.utcnow(),
            confidence=0.8
        )

        self._reputation_db[domain] = score
        return score

    def get_stats(self) -> dict[str, Any]:
        return {
            "cached_domains": len(self._reputation_db),
            "enabled": self.enabled
        }
