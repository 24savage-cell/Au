"""
ZTNA (Zero Trust Network Access) 零信任网络访问模块

该模块提供零信任安全架构实现，包括：
- 身份提供商（多源身份聚合、SSO集成）
- 设备指纹（硬件/软件/行为特征）
- 行为生物识别（击键/鼠标动力学）
- 多因素认证（TOTP/WebAuthn/SMS/Push）
- ABAC策略引擎（属性基访问控制）
- 属性存储（用户/设备/环境属性）
- 风险计算器（多因子风险评分、ML修正）
- 微隧道（Noise Protocol加密隧道）
- 会话管理（生命周期、并发控制）
- 持续认证（会话中持续验证）
- 策略执行点（PEP）
- 策略决策点（PDP）

作者: IP4Move Security Team
版本: 1.0.5
"""

from .identity.identity_provider import IdentityProvider, IdentityToken
from .identity.device_fingerprint import DeviceFingerprint, DeviceProfile
from .identity.behavior_biometrics import BehaviorBiometrics, KeystrokeProfile
from .identity.mfa_manager import MFAManager, MFAMethod, TOTPProvider, WebAuthnProvider
from .policy.policy_engine import PolicyEngine, ABACPolicy, PolicyDecision
from .policy.attribute_store import AttributeStore, UserAttributes, DeviceAttributes
from .policy.risk_calculator import RiskCalculator, RiskFactors, RiskScore
from .access.micro_tunnel import MicroTunnel, NoiseProtocolTunnel
from .access.session_manager import SessionManager, Session, SessionState
from .access.continuous_auth import ContinuousAuth, AuthContinuityChecker
from .enforcement.pep import PolicyEnforcementPoint, EnforcementAction
from .enforcement.pdp import PolicyDecisionPoint, DecisionRequest, DecisionResponse

__version__ = "1.0.5"
__author__ = "IP4Move Security Team"

__all__ = [
    # 身份
    "IdentityProvider",
    "IdentityToken",
    "DeviceFingerprint",
    "DeviceProfile",
    "BehaviorBiometrics",
    "KeystrokeProfile",
    "MFAManager",
    "MFAMethod",
    "TOTPProvider",
    "WebAuthnProvider",
    # 策略
    "PolicyEngine",
    "ABACPolicy",
    "PolicyDecision",
    "AttributeStore",
    "UserAttributes",
    "DeviceAttributes",
    "RiskCalculator",
    "RiskFactors",
    "RiskScore",
    # 访问
    "MicroTunnel",
    "NoiseProtocolTunnel",
    "SessionManager",
    "Session",
    "SessionState",
    "ContinuousAuth",
    "AuthContinuityChecker",
    # 执行
    "PolicyEnforcementPoint",
    "EnforcementAction",
    "PolicyDecisionPoint",
    "DecisionRequest",
    "DecisionResponse",
]


class ZTNAEngine:
    """
    ZTNA引擎主类
    
    整合所有ZTNA组件，提供统一的零信任访问控制接口
    """
    
    def __init__(self, config: dict | None = None):
        """
        初始化ZTNA引擎
        
        Args:
            config: 配置字典
        """
        self.config = config or {}
        
        # 初始化组件
        self._identity_provider = IdentityProvider(self.config.get("identity", {}))
        self._device_fingerprint = DeviceFingerprint(self.config.get("device", {}))
        self._behavior_biometrics = BehaviorBiometrics(self.config.get("behavior", {}))
        self._mfa_manager = MFAManager(self.config.get("mfa", {}))
        self._policy_engine = PolicyEngine(self.config.get("policy", {}))
        self._attribute_store = AttributeStore(self.config.get("attributes", {}))
        self._risk_calculator = RiskCalculator(self.config.get("risk", {}))
        self._session_manager = SessionManager(self.config.get("session", {}))
        self._continuous_auth = ContinuousAuth(self.config.get("continuous", {}))
        self._pep = PolicyEnforcementPoint(self.config.get("pep", {}))
        self._pdp = PolicyDecisionPoint(self.config.get("pdp", {}))
        
        self._initialized = False
        
    async def initialize(self) -> None:
        """初始化所有组件"""
        if self._initialized:
            return
            
        await self._identity_provider.initialize()
        await self._device_fingerprint.initialize()
        await self._behavior_biometrics.initialize()
        await self._mfa_manager.initialize()
        await self._policy_engine.initialize()
        await self._attribute_store.initialize()
        await self._risk_calculator.initialize()
        await self._session_manager.initialize()
        await self._continuous_auth.initialize()
        await self._pep.initialize()
        await self._pdp.initialize()
        
        self._initialized = True
        
    async def shutdown(self) -> None:
        """关闭所有组件"""
        await self._identity_provider.shutdown()
        await self._device_fingerprint.shutdown()
        await self._behavior_biometrics.shutdown()
        await self._mfa_manager.shutdown()
        await self._policy_engine.shutdown()
        await self._attribute_store.shutdown()
        await self._risk_calculator.shutdown()
        await self._session_manager.shutdown()
        await self._continuous_auth.shutdown()
        await self._pep.shutdown()
        await self._pdp.shutdown()
        
        self._initialized = False
        
    @property
    def identity(self) -> IdentityProvider:
        """获取身份提供商"""
        return self._identity_provider
        
    @property
    def device(self) -> DeviceFingerprint:
        """获取设备指纹"""
        return self._device_fingerprint
        
    @property
    def behavior(self) -> BehaviorBiometrics:
        """获取行为生物识别"""
        return self._behavior_biometrics
        
    @property
    def mfa(self) -> MFAManager:
        """获取MFA管理器"""
        return self._mfa_manager
        
    @property
    def policy(self) -> PolicyEngine:
        """获取策略引擎"""
        return self._policy_engine
        
    @property
    def attributes(self) -> AttributeStore:
        """获取属性存储"""
        return self._attribute_store
        
    @property
    def risk(self) -> RiskCalculator:
        """获取风险计算器"""
        return self._risk_calculator
        
    @property
    def session(self) -> SessionManager:
        """获取会话管理器"""
        return self._session_manager
        
    @property
    def continuous_auth(self) -> ContinuousAuth:
        """获取持续认证器"""
        return self._continuous_auth
        
    @property
    def pep(self) -> PolicyEnforcementPoint:
        """获取策略执行点"""
        return self._pep
        
    @property
    def pdp(self) -> PolicyDecisionPoint:
        """获取策略决策点"""
        return self._pdp
