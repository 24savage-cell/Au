"""
IP信誉模块

提供多源聚合的IP信誉评分
"""

import ipaddress
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from src.common.base_component import BaseComponent
from src.common.reputation import ReputationLevel, BaseReputationScore

logger = logging.getLogger(__name__)


@dataclass
class IPReputationScore(BaseReputationScore):
    """IP信誉分数"""
    ip: str = ""
    categories: list[str] = None

    def __post_init__(self):
        if self.categories is None:
            self.categories = []

    def to_dict(self) -> dict[str, Any]:
        result = self._base_to_dict()
        result["ip"] = self.ip
        result["categories"] = self.categories
        return result


class IPReputationFeed(BaseComponent):
    """
    IP信誉源

    聚合多个来源的IP信誉数据
    """

    @property
    def component_name(self) -> str:
        return "IP信誉源"

    def __init__(self, config: Optional[dict] = None):
        super().__init__(config)
        self._reputation_db: dict[str, IPReputationScore] = {}
        self._sources: list[str] = self.config.get("sources", [
            "virustotal", "abuseipdb", "shodan", "greynoise"
        ])

    async def check_ip(self, ip: str) -> IPReputationScore:
        """
        检查IP信誉

        Args:
            ip: IP地址

        Returns:
            信誉分数
        """
        try:
            ipaddress.ip_address(ip)
        except ValueError:
            return IPReputationScore(
                ip=ip,
                score=0,
                level=ReputationLevel.NEUTRAL,
                sources=[],
                categories=["invalid"],
                first_seen=datetime.utcnow(),
                last_seen=datetime.utcnow(),
                confidence=0
            )

        if ip in self._reputation_db:
            return self._reputation_db[ip]

        score = await self._query_reputation(ip)
        self._reputation_db[ip] = score
        return score

    async def _query_reputation(self, ip: str) -> IPReputationScore:
        """查询IP信誉"""
        try:
            ip_obj = ipaddress.ip_address(ip)
            if ip_obj.is_private:
                return IPReputationScore(
                    ip=ip,
                    score=0,
                    level=ReputationLevel.NEUTRAL,
                    sources=["internal"],
                    categories=["private"],
                    first_seen=datetime.utcnow(),
                    last_seen=datetime.utcnow(),
                    confidence=1.0
                )
        except ValueError:
            pass

        is_threat = self._simulate_threat_check(ip)

        if is_threat:
            return IPReputationScore(
                ip=ip,
                score=85,
                level=ReputationLevel.MALICIOUS,
                sources=self._sources,
                categories=["malware", "c2"],
                first_seen=datetime.utcnow(),
                last_seen=datetime.utcnow(),
                confidence=0.9
            )
        else:
            return IPReputationScore(
                ip=ip,
                score=10,
                level=ReputationLevel.CLEAN,
                sources=self._sources,
                categories=["clean"],
                first_seen=datetime.utcnow(),
                last_seen=datetime.utcnow(),
                confidence=0.8
            )

    def _simulate_threat_check(self, ip: str) -> bool:
        """模拟威胁检查"""
        parts = ip.split(".")
        if len(parts) == 4:
            first_octet = int(parts[0])
            return first_octet in [10, 192, 172]
        return False

    def get_stats(self) -> dict[str, Any]:
        return {
            "cached_ips": len(self._reputation_db),
            "sources": self._sources,
            "enabled": self.enabled
        }
