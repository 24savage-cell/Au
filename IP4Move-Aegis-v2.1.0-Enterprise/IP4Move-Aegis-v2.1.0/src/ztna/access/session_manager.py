"""
会话管理模块

管理会话生命周期和并发控制
"""

import asyncio
import logging
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from typing import Any, Optional

logger = logging.getLogger(__name__)


class SessionState(Enum):
    """会话状态"""
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    SUSPENDED = "suspended"


@dataclass
class Session:
    """会话"""
    session_id: str
    user_id: str
    device_id: str
    created_at: datetime
    expires_at: datetime
    state: SessionState = SessionState.ACTIVE
    metadata: dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_expired(self) -> bool:
        """检查是否过期"""
        return datetime.utcnow() > self.expires_at


class SessionManager:
    """
    会话管理器
    
    管理用户会话的生命周期
    """
    
    def __init__(self, config: Optional[dict] = None):
        self.config = config or {}
        self.session_ttl = self.config.get("session_ttl", 3600)
        self.max_concurrent = self.config.get("max_concurrent", 5)
        
        self._sessions: dict[str, Session] = {}
        self._user_sessions: dict[str, list[str]] = {}
        self._initialized = False
        
    async def initialize(self) -> None:
        """初始化"""
        if self._initialized:
            return
        logger.info("初始化会话管理器...")
        self._initialized = True
        logger.info("会话管理器初始化完成")
        
    async def shutdown(self) -> None:
        """关闭"""
        self._initialized = False
        logger.info("会话管理器已关闭")
        
    def create_session(self, user_id: str, device_id: str) -> Session:
        """
        创建会话
        
        Args:
            user_id: 用户ID
            device_id: 设备ID
            
        Returns:
            会话对象
        """
        # 检查并发限制
        user_session_ids = self._user_sessions.get(user_id, [])
        if len(user_session_ids) >= self.max_concurrent:
            # 移除最旧的会话
            oldest_id = user_session_ids[0]
            self.terminate_session(oldest_id)
            
        session_id = secrets.token_urlsafe(32)
        now = datetime.utcnow()
        
        session = Session(
            session_id=session_id,
            user_id=user_id,
            device_id=device_id,
            created_at=now,
            expires_at=now + timedelta(seconds=self.session_ttl)
        )
        
        self._sessions[session_id] = session
        
        if user_id not in self._user_sessions:
            self._user_sessions[user_id] = []
        self._user_sessions[user_id].append(session_id)
        
        logger.info(f"创建会话: {session_id} 用户: {user_id}")
        return session
        
    def get_session(self, session_id: str) -> Optional[Session]:
        """获取会话"""
        session = self._sessions.get(session_id)
        if session and session.is_expired:
            session.state = SessionState.EXPIRED
        return session
        
    def terminate_session(self, session_id: str) -> bool:
        """终止会话"""
        session = self._sessions.get(session_id)
        if not session:
            return False
            
        session.state = SessionState.REVOKED
        del self._sessions[session_id]
        
        if session.user_id in self._user_sessions:
            self._user_sessions[session.user_id].remove(session_id)
            
        logger.info(f"终止会话: {session_id}")
        return True
        
    def get_user_sessions(self, user_id: str) -> list[Session]:
        """获取用户所有会话"""
        session_ids = self._user_sessions.get(user_id, [])
        return [self._sessions[sid] for sid in session_ids if sid in self._sessions]
        
    def get_stats(self) -> dict[str, Any]:
        """获取统计信息"""
        return {
            "active_sessions": len(self._sessions),
            "unique_users": len(self._user_sessions)
        }
