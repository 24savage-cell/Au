"""
IP信誉模块

提供多源聚合的IP信誉评分
"""

import asyncio
import ipaddress
import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class IPReputationLevel(Enum):
    """IP信誉等级"""
    TRUSTED = "trusted"      # 可信
    CLEAN = "clean"          # 干净
    NEUTRAL = "neutral"      # 中性
    SUSPICIOUS = "suspicious" # 可疑
    MALICIOUS = "malicious"  # 恶意


@dataclass
class IPReputationScore:
    """IP信誉分数"""
    ip: str
    score: float  # 0-100, 越高越危险
    level: IPReputationLevel
    sources: list[str]
    categories: list[str]
    first_seen: datetime
    last_seen: datetime
    confidence: float
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "ip": self.ip,
            "score": self.score,
            "level": self.level.value,
            "sources": self.sources,
            "categories": self.categories,
            "first_seen": self.first_seen.isoformat(),
            "last_seen": self.last_seen.isoformat(),
            "confidence": self.confidence
        }


class IPReputationFeed:
    """
    IP信誉源
    
    聚合多个来源的IP信誉数据
    """
    
    def __init__(self, config: Optional[dict] = None):
        """
        初始化IP信誉源
        
        Args:
            config: 配置字典
        """
        self.config = config or {}
        self.enabled = self.config.get("enabled", True)
        
        # 信誉数据存储
        self._reputation_db: dict[str, IPReputationScore] = {}
        
        # 信誉源列表
        self._sources: list[str] = self.config.get("sources", [
            "virustotal", "abuseipdb", "shodan", "greynoise"
        ])
        
        self._initialized = False
        
    async def initialize(self) -> None:
        """初始化信誉源"""
        if self._initialized:
            return
            
        logger.info("初始化IP信誉源...")
        self._initialized = True
        logger.info("IP信誉源初始化完成")
        
    async def shutdown(self) -> None:
        """关闭信誉源"""
        self._initialized = False
        logger.info("IP信誉源已关闭")
        
    async def check_ip(self, ip: str) -> IPReputationScore:
        """
        检查IP信誉
        
        Args:
            ip: IP地址
            
        Returns:
            信誉分数
        """
        # 验证IP
        try:
            ipaddress.ip_address(ip)
        except ValueError:
            return IPReputationScore(
                ip=ip,
                score=0,
                level=IPReputationLevel.NEUTRAL,
                sources=[],
                categories=["invalid"],
                first_seen=datetime.utcnow(),
                last_seen=datetime.utcnow(),
                confidence=0
            )
            
        # 检查缓存
        if ip in self._reputation_db:
            return self._reputation_db[ip]
            
        # 查询信誉
        score = await self._query_reputation(ip)
        self._reputation_db[ip] = score
        
        return score
        
    async def _query_reputation(self, ip: str) -> IPReputationScore:
        """
        查询IP信誉
        
        Args:
            ip: IP地址
            
        Returns:
            信誉分数
        """
        # 模拟从多个源查询
        # 实际实现中会调用API
        
        # 检查是否为私有IP
        try:
            ip_obj = ipaddress.ip_address(ip)
            if ip_obj.is_private:
                return IPReputationScore(
                    ip=ip,
                    score=0,
                    level=IPReputationLevel.NEUTRAL,
                    sources=["internal"],
                    categories=["private"],
                    first_seen=datetime.utcnow(),
                    last_seen=datetime.utcnow(),
                    confidence=1.0
                )
        except ValueError:
            pass
            
        # 模拟威胁情报查询
        # 实际实现中会查询VirusTotal、AbuseIPDB等
        is_threat = self._simulate_threat_check(ip)
        
        if is_threat:
            return IPReputationScore(
                ip=ip,
                score=85,
                level=IPReputationLevel.MALICIOUS,
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
                level=IPReputationLevel.CLEAN,
                sources=self._sources,
                categories=["clean"],
                first_seen=datetime.utcnow(),
                last_seen=datetime.utcnow(),
                confidence=0.8
            )
            
    def _simulate_threat_check(self, ip: str) -> bool:
        """
        模拟威胁检查
        
        Args:
            ip: IP地址
            
        Returns:
            是否威胁
        """
        # 简单的模拟：检查IP是否以特定数字开头
        parts = ip.split(".")
        if len(parts) == 4:
            first_octet = int(parts[0])
            # 模拟一些恶意IP
            return first_octet in [10, 192, 172]
        return False
        
    def get_stats(self) -> dict[str, Any]:
        """
        获取统计信息
        
        Returns:
            统计信息
        """
        return {
            "cached_ips": len(self._reputation_db),
            "sources": self._sources,
            "enabled": self.enabled
        }
