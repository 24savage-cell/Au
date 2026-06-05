"""
Threat Intelligence 高级威胁情报模块

该模块提供威胁情报收集、分析和共享功能，包括：
- STIX/TAXII采集器
- OpenCTI连接器
- MISP连接器
- 开源情报采集
- IOC分析（IP/域名/URL/哈希/邮箱）
- 攻击活动追踪
- 攻击归因引擎（TTP匹配）
- 事件关联（图算法、时序分析）
- MITRE ATT&CK模式匹配
- 情报共享（多源聚合、去重）
- TLP颜色强制执行
- IP信誉（多源聚合评分）
- 域名信誉
- 文件哈希信誉

作者: IP4Move Security Team
版本: 1.0.5
"""

from .collectors.stix_taxii_collector import STIXTAXIICollector, TAXIIClient
from .collectors.opencti_connector import OpenCTIConnector
from .collectors.misp_connector import MISPConnector
from .collectors.osint_collector import OSINTCollector
from .analyzers.ioc_analyzer import IOCAnalyzer, IOCTypes, IOCResult
from .analyzers.campaign_tracker import CampaignTracker, AttackCampaign
from .analyzers.attribution_engine import AttributionEngine, AttributionResult
from .correlation.event_correlator import EventCorrelator, CorrelationGraph
from .correlation.pattern_matcher import MITREPatternMatcher, ATTACKPattern
from .sharing.intel_sharing import IntelSharing, IntelFeed
from .sharing.tlp_enforcer import TLPEnforcer, TLPLevel
from .feeds.ip_reputation import IPReputationFeed, IPReputationScore
from .feeds.domain_reputation import DomainReputationFeed, DomainReputationScore
from .feeds.file_hash_reputation import FileHashReputationFeed, HashReputationScore

__version__ = "1.0.5"
__author__ = "IP4Move Security Team"

__all__ = [
    # 采集器
    "STIXTAXIICollector",
    "TAXIIClient",
    "OpenCTIConnector",
    "MISPConnector",
    "OSINTCollector",
    # 分析器
    "IOCAnalyzer",
    "IOCTypes",
    "IOCResult",
    "CampaignTracker",
    "AttackCampaign",
    "AttributionEngine",
    "AttributionResult",
    # 关联
    "EventCorrelator",
    "CorrelationGraph",
    "MITREPatternMatcher",
    "ATTACKPattern",
    # 共享
    "IntelSharing",
    "IntelFeed",
    "TLPEnforcer",
    "TLPLevel",
    # 信誉
    "IPReputationFeed",
    "IPReputationScore",
    "DomainReputationFeed",
    "DomainReputationScore",
    "FileHashReputationFeed",
    "HashReputationScore",
]


class ThreatIntelEngine:
    """
    威胁情报引擎主类
    
    整合所有威胁情报组件，提供统一的情报处理接口
    """
    
    def __init__(self, config: dict | None = None):
        """
        初始化威胁情报引擎
        
        Args:
            config: 配置字典
        """
        self.config = config or {}
        
        # 初始化组件
        self._stix_collector = STIXTAXIICollector(self.config.get("stix", {}))
        self._opencti_connector = OpenCTIConnector(self.config.get("opencti", {}))
        self._misp_connector = MISPConnector(self.config.get("misp", {}))
        self._osint_collector = OSINTCollector(self.config.get("osint", {}))
        self._ioc_analyzer = IOCAnalyzer(self.config.get("ioc", {}))
        self._campaign_tracker = CampaignTracker(self.config.get("campaign", {}))
        self._attribution_engine = AttributionEngine(self.config.get("attribution", {}))
        self._event_correlator = EventCorrelator(self.config.get("correlation", {}))
        self._pattern_matcher = MITREPatternMatcher(self.config.get("pattern", {}))
        self._intel_sharing = IntelSharing(self.config.get("sharing", {}))
        self._tlp_enforcer = TLPEnforcer(self.config.get("tlp", {}))
        self._ip_reputation = IPReputationFeed(self.config.get("ip_reputation", {}))
        self._domain_reputation = DomainReputationFeed(self.config.get("domain_reputation", {}))
        self._hash_reputation = FileHashReputationFeed(self.config.get("hash_reputation", {}))
        
        self._initialized = False
        
    async def initialize(self) -> None:
        """初始化所有组件"""
        if self._initialized:
            return
            
        await self._stix_collector.initialize()
        await self._opencti_connector.initialize()
        await self._misp_connector.initialize()
        await self._osint_collector.initialize()
        await self._ioc_analyzer.initialize()
        await self._campaign_tracker.initialize()
        await self._attribution_engine.initialize()
        await self._event_correlator.initialize()
        await self._pattern_matcher.initialize()
        await self._intel_sharing.initialize()
        await self._tlp_enforcer.initialize()
        await self._ip_reputation.initialize()
        await self._domain_reputation.initialize()
        await self._hash_reputation.initialize()
        
        self._initialized = True
        
    async def shutdown(self) -> None:
        """关闭所有组件"""
        await self._stix_collector.shutdown()
        await self._opencti_connector.shutdown()
        await self._misp_connector.shutdown()
        await self._osint_collector.shutdown()
        await self._ioc_analyzer.shutdown()
        await self._campaign_tracker.shutdown()
        await self._attribution_engine.shutdown()
        await self._event_correlator.shutdown()
        await self._pattern_matcher.shutdown()
        await self._intel_sharing.shutdown()
        await self._tlp_enforcer.shutdown()
        await self._ip_reputation.shutdown()
        await self._domain_reputation.shutdown()
        await self._hash_reputation.shutdown()
        
        self._initialized = False
        
    @property
    def stix_collector(self) -> STIXTAXIICollector:
        """获取STIX/TAXII采集器"""
        return self._stix_collector
        
    @property
    def opencti(self) -> OpenCTIConnector:
        """获取OpenCTI连接器"""
        return self._opencti_connector
        
    @property
    def misp(self) -> MISPConnector:
        """获取MISP连接器"""
        return self._misp_connector
        
    @property
    def osint(self) -> OSINTCollector:
        """获取OSINT采集器"""
        return self._osint_collector
        
    @property
    def ioc_analyzer(self) -> IOCAnalyzer:
        """获取IOC分析器"""
        return self._ioc_analyzer
        
    @property
    def campaign_tracker(self) -> CampaignTracker:
        """获取攻击活动追踪器"""
        return self._campaign_tracker
        
    @property
    def attribution(self) -> AttributionEngine:
        """获取归因引擎"""
        return self._attribution_engine
        
    @property
    def correlator(self) -> EventCorrelator:
        """获取事件关联器"""
        return self._event_correlator
        
    @property
    def pattern_matcher(self) -> MITREPatternMatcher:
        """获取模式匹配器"""
        return self._pattern_matcher
        
    @property
    def intel_sharing(self) -> IntelSharing:
        """获取情报共享器"""
        return self._intel_sharing
        
    @property
    def tlp_enforcer(self) -> TLPEnforcer:
        """获取TLP执行器"""
        return self._tlp_enforcer
        
    @property
    def ip_reputation(self) -> IPReputationFeed:
        """获取IP信誉源"""
        return self._ip_reputation
        
    @property
    def domain_reputation(self) -> DomainReputationFeed:
        """获取域名信誉源"""
        return self._domain_reputation
        
    @property
    def hash_reputation(self) -> FileHashReputationFeed:
        """获取文件哈希信誉源"""
        return self._hash_reputation
