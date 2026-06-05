"""
信誉评估公共模块

提供跨多个信誉源(IP、域名、文件哈希)共享的枚举和基类。
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any


class ReputationLevel(Enum):
    """信誉等级 (IP/域名/文件哈希通用)"""
    TRUSTED = "trusted"
    CLEAN = "clean"
    NEUTRAL = "neutral"
    SUSPICIOUS = "suspicious"
    MALICIOUS = "malicious"


@dataclass
class BaseReputationScore:
    """
    信誉评分基类

    子类添加特定标识字段(ip/domain/file_hash)并调用 _base_to_dict()
    来复用序列化逻辑。
    """
    score: float
    level: ReputationLevel
    sources: list[str]
    first_seen: datetime
    last_seen: datetime
    confidence: float

    def _base_to_dict(self) -> dict[str, Any]:
        """共享的序列化字段"""
        return {
            "score": self.score,
            "level": self.level.value,
            "sources": self.sources,
            "first_seen": self.first_seen.isoformat(),
            "last_seen": self.last_seen.isoformat(),
            "confidence": self.confidence,
        }
