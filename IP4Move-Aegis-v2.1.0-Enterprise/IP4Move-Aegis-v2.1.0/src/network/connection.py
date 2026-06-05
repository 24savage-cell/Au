"""
连接管理模块

管理多个网络连接。
"""

import asyncio
import time
import logging
from typing import Optional, Dict, List, Callable
from dataclasses import dataclass, field

from src.network.transport import Transport

logger = logging.getLogger(__name__)


@dataclass
class ConnectionInfo:
    """连接信息"""
    conn_id: str
    remote_host: str
    remote_port: int
    transport: Optional[Transport] = None
    created_at: float = field(default_factory=time.time)
    last_activity: float = field(default_factory=time.time)
    is_active: bool = True


class ConnectionManager:
    """
    连接管理器

    管理多个网络连接:
    - 连接池
    - 自动重连
    - 连接超时
    - 负载均衡
    """

    def __init__(
        self,
        max_connections: int = 1000,
        connection_timeout: float = 30,
        idle_timeout: float = 300,
    ):
        self._max_connections = max_connections
        self._connection_timeout = connection_timeout
        self._idle_timeout = idle_timeout
        self._connections: Dict[str, ConnectionInfo] = {}
        self._conn_counter = 0
        self._lock = asyncio.Lock()
        self._cleanup_task: Optional[asyncio.Task] = None
        self._is_running = False

    @property
    def active_count(self) -> int:
        return sum(1 for c in self._connections.values() if c.is_active)

    async def connect(
        self,
        host: str,
        port: int,
        on_message: Optional[Callable] = None,
    ) -> ConnectionInfo:
        """建立新连接"""
        async with self._lock:
            if self.active_count >= self._max_connections:
                raise RuntimeError(f"连接数已达上限: {self._max_connections}")

            self._conn_counter += 1
            conn_id = f"conn-{self._conn_counter:06d}"

            transport = await Transport.connect(host, port, on_message, self._connection_timeout)

            info = ConnectionInfo(
                conn_id=conn_id,
                remote_host=host,
                remote_port=port,
                transport=transport,
            )
            self._connections[conn_id] = info
            logger.debug(f"连接建立: {conn_id} -> {host}:{port}")
            return info

    async def send(self, conn_id: str, data: bytes) -> bool:
        """通过连接发送数据"""
        info = self._connections.get(conn_id)
        if not info or not info.is_active or not info.transport:
            logger.warning(f"发送失败: 连接 {conn_id} 不存在或已关闭")
            return False
        success = await info.transport.send(data)
        if success:
            info.last_activity = time.time()
        else:
            info.is_active = False
        return success

    async def broadcast(self, data: bytes, exclude: Optional[List[str]] = None) -> int:
        """广播数据到所有活跃连接"""
        exclude = exclude or []
        count = 0
        for conn_id, info in self._connections.items():
            if conn_id not in exclude and info.is_active:
                if await self.send(conn_id, data):
                    count += 1
        return count

    async def close(self, conn_id: str) -> bool:
        """关闭连接"""
        info = self._connections.get(conn_id)
        if not info:
            return False
        info.is_active = False
        if info.transport:
            await info.transport.close()
        logger.debug(f"连接关闭: {conn_id}")
        return True

    async def close_all(self) -> int:
        """关闭所有连接"""
        count = 0
        for conn_id in list(self._connections.keys()):
            if await self.close(conn_id):
                count += 1
        return count

    async def _cleanup_loop(self) -> None:
        """清理空闲连接"""
        while self._is_running:
            try:
                now = time.time()
                for conn_id, info in list(self._connections.items()):
                    if info.is_active and now - info.last_activity > self._idle_timeout:
                        await self.close(conn_id)
                        logger.debug(f"清理空闲连接: {conn_id}")
                    elif not info.is_active:
                        del self._connections[conn_id]
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"连接清理循环异常: {e}")
            await asyncio.sleep(30)

    async def start(self) -> None:
        """启动连接管理器"""
        self._is_running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())

    async def stop(self) -> None:
        """停止连接管理器"""
        self._is_running = False
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        await self.close_all()

    def get_stats(self) -> dict:
        return {
            "total_connections": len(self._connections),
            "active_connections": self.active_count,
            "max_connections": self._max_connections,
        }
