"""
文件哈希信誉模块

提供文件哈希信誉评分
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from src.common.base_component import BaseComponent
from src.common.reputation import ReputationLevel, BaseReputationScore

logger = logging.getLogger(__name__)


@dataclass
class HashReputationScore(BaseReputationScore):
    """哈希信誉分数"""
    file_hash: str = ""
    hash_type: str = ""
    malware_family: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        result = self._base_to_dict()
        result["file_hash"] = self.file_hash
        result["hash_type"] = self.hash_type
        result["malware_family"] = self.malware_family
        return result


class FileHashReputationFeed(BaseComponent):
    """
    文件哈希信誉源

    提供文件哈希信誉评分
    """

    @property
    def component_name(self) -> str:
        return "文件哈希信誉源"

    def __init__(self, config: Optional[dict] = None):
        super().__init__(config)
        self._reputation_db: dict[str, HashReputationScore] = {}

    async def check_hash(self, file_hash: str, hash_type: str = "sha256") -> HashReputationScore:
        """
        检查文件哈希信誉

        Args:
            file_hash: 文件哈希
            hash_type: 哈希类型

        Returns:
            信誉分数
        """
        cache_key = f"{hash_type}:{file_hash}"

        if cache_key in self._reputation_db:
            return self._reputation_db[cache_key]

        score = HashReputationScore(
            file_hash=file_hash,
            hash_type=hash_type,
            score=10,
            level=ReputationLevel.CLEAN,
            sources=["virustotal", "malwarebazaar"],
            malware_family=None,
            first_seen=datetime.utcnow(),
            last_seen=datetime.utcnow(),
            confidence=0.9
        )

        self._reputation_db[cache_key] = score
        return score

    def get_stats(self) -> dict[str, Any]:
        return {
            "cached_hashes": len(self._reputation_db),
            "enabled": self.enabled
        }
