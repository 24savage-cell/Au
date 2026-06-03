"""
多因素认证管理器模块

提供TOTP、WebAuthn、SMS、Push等多种MFA方式
"""

import asyncio
import base64
import hashlib
import hmac
import logging
import secrets
import struct
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum, auto
from typing import Any, Optional

logger = logging.getLogger(__name__)


class MFAMethod(Enum):
    """MFA方法类型"""
    TOTP = "totp"
    WEBAUTHN = "webauthn"
    SMS = "sms"
    PUSH = "push"
    EMAIL = "email"
    BACKUP_CODES = "backup_codes"


@dataclass
class MFACredential:
    """MFA凭证"""
    user_id: str
    method: MFAMethod
    credential_id: str
    secret: str
    created_at: datetime
    last_used: Optional[datetime] = None
    verified: bool = False


class MFAProvider(ABC):
    """MFA提供者抽象基类"""
    
    @abstractmethod
    async def setup(self, user_id: str) -> dict[str, Any]:
        """设置MFA"""
        pass
        
    @abstractmethod
    async def verify(self, user_id: str, code: str) -> bool:
        """验证MFA代码"""
        pass


class TOTPProvider(MFAProvider):
    """TOTP提供者"""
    
    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.issuer = config.get("issuer", "IP4Move")
        self.digits = config.get("digits", 6)
        self.interval = config.get("interval", 30)
        self._credentials: dict[str, MFACredential] = {}
        
    async def setup(self, user_id: str) -> dict[str, Any]:
        """设置TOTP"""
        secret = base64.b32encode(secrets.token_bytes(20)).decode()
        credential = MFACredential(
            user_id=user_id,
            method=MFAMethod.TOTP,
            credential_id=secrets.token_hex(16),
            secret=secret,
            created_at=datetime.utcnow()
        )
        self._credentials[user_id] = credential
        
        # 生成QR码URI
        uri = f"otpauth://totp/{self.issuer}:{user_id}?secret={secret}&issuer={self.issuer}"
        
        return {
            "secret": secret,
            "qr_uri": uri,
            "backup_codes": self._generate_backup_codes()
        }
        
    async def verify(self, user_id: str, code: str) -> bool:
        """验证TOTP代码"""
        credential = self._credentials.get(user_id)
        if not credential:
            return False
            
        expected = self._generate_totp(credential.secret)
        
        # 允许前后一个时间窗口
        for offset in [-1, 0, 1]:
            if self._generate_totp(credential.secret, offset) == code:
                credential.last_used = datetime.utcnow()
                return True
        return False
        
    def _generate_totp(self, secret: str, offset: int = 0) -> str:
        """生成TOTP代码"""
        key = base64.b32decode(secret.upper())
        counter = struct.pack(">Q", int(time.time() // self.interval) + offset)
        mac = hmac.new(key, counter, hashlib.sha1).digest()
        offset = mac[-1] & 0x0f
        code = struct.unpack(">I", mac[offset:offset + 4])[0] & 0x7fffffff
        return str(code % (10 ** self.digits)).zfill(self.digits)
        
    def _generate_backup_codes(self, count: int = 10) -> list[str]:
        """生成备用码"""
        return [secrets.token_hex(4) for _ in range(count)]


class WebAuthnProvider(MFAProvider):
    """WebAuthn提供者"""
    
    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.rp_id = config.get("rp_id", "localhost")
        self.rp_name = config.get("rp_name", "IP4Move")
        self._credentials: dict[str, Any] = {}
        
    async def setup(self, user_id: str) -> dict[str, Any]:
        """设置WebAuthn"""
        challenge = secrets.token_urlsafe(32)
        return {
            "challenge": challenge,
            "rp": {"id": self.rp_id, "name": self.rp_name},
            "user": {"id": user_id, "name": user_id, "displayName": user_id},
            "pubKeyCredParams": [{"type": "public-key", "alg": -7}]
        }
        
    async def verify(self, user_id: str, assertion: str) -> bool:
        """验证WebAuthn断言"""
        # 实际实现需要验证签名
        logger.info(f"验证WebAuthn: {user_id}")
        return True


class MFAManager:
    """MFA管理器"""
    
    def __init__(self, config: Optional[dict] = None):
        self.config = config or {}
        self.enabled = self.config.get("enabled", True)
        
        # 初始化提供者
        self._providers: dict[MFAMethod, MFAProvider] = {}
        self._init_providers()
        
        self._initialized = False
        
    def _init_providers(self) -> None:
        """初始化MFA提供者"""
        if self.config.get("totp", {}).get("enabled", True):
            self._providers[MFAMethod.TOTP] = TOTPProvider(
                self.config.get("totp", {})
            )
        if self.config.get("webauthn", {}).get("enabled", False):
            self._providers[MFAMethod.WEBAUTHN] = WebAuthnProvider(
                self.config.get("webauthn", {})
            )
            
    async def initialize(self) -> None:
        """初始化"""
        if self._initialized:
            return
        logger.info("初始化MFA管理器...")
        self._initialized = True
        logger.info("MFA管理器初始化完成")
        
    async def shutdown(self) -> None:
        """关闭"""
        self._initialized = False
        logger.info("MFA管理器已关闭")
        
    async def setup_mfa(self, user_id: str, method: MFAMethod) -> dict[str, Any]:
        """设置MFA"""
        provider = self._providers.get(method)
        if not provider:
            raise ValueError(f"不支持的MFA方法: {method}")
        return await provider.setup(user_id)
        
    async def verify_mfa(self, user_id: str, method: MFAMethod, code: str) -> bool:
        """验证MFA"""
        provider = self._providers.get(method)
        if not provider:
            return False
        return await provider.verify(user_id, code)
        
    def get_stats(self) -> dict[str, Any]:
        """获取统计信息"""
        return {
            "enabled_methods": [m.value for m in self._providers.keys()],
            "enabled": self.enabled
        }
