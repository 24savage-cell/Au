"""
OpenCTI连接器模块

提供与OpenCTI平台的集成
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from src.common.base_component import BaseComponent

logger = logging.getLogger(__name__)


@dataclass
class OpenCTIIndicator:
    """OpenCTI指标"""
    id: str
    pattern: str
    pattern_type: str
    valid_from: datetime
    valid_until: Optional[datetime]
    labels: list[str]
    confidence: int


class OpenCTIConnector(BaseComponent):
    """
    OpenCTI连接器

    连接OpenCTI威胁情报平台
    """

    @property
    def component_name(self) -> str:
        return "OpenCTI连接器"

    def __init__(self, config: Optional[dict] = None):
        super().__init__(config)
        self.api_url = self.config.get("api_url", "")
        self.api_token = self.config.get("api_token", "")
        self._indicators: list[OpenCTIIndicator] = []

    async def fetch_indicators(self) -> list[OpenCTIIndicator]:
        """获取指标"""
        return self._indicators

    def get_stats(self) -> dict[str, Any]:
        return {
            "indicators": len(self._indicators),
            "enabled": self.enabled
        }
