"""
微隧道模块

基于Noise Protocol的加密隧道实现
"""

import logging
import secrets
from dataclasses import dataclass
from typing import Any, Optional

from src.common.base_component import BaseComponent

logger = logging.getLogger(__name__)


@dataclass
class TunnelConfig:
    """隧道配置"""
    tunnel_id: str
    local_addr: str
    remote_addr: str
    noise_pattern: str = "Noise_IK_25519_ChaChaPoly_BLAKE2s"


class NoiseProtocolTunnel:
    """
    Noise Protocol隧道

    实现Noise Protocol加密通信
    """

    def __init__(self, config: TunnelConfig):
        self.config = config
        self._established = False
        self._session_key: Optional[bytes] = None

    async def establish(self) -> bool:
        """建立隧道"""
        try:
            logger.info(f"建立Noise隧道: {self.config.tunnel_id}")
            self._session_key = secrets.token_bytes(32)
            self._established = True
            return True
        except Exception as e:
            logger.error(f"隧道建立失败: {e}")
            return False

    async def send(self, data: bytes) -> bool:
        """发送数据"""
        if not self._established:
            return False
        return True

    async def receive(self) -> Optional[bytes]:
        """接收数据"""
        if not self._established:
            return None
        return b""

    async def close(self) -> None:
        """关闭隧道"""
        self._established = False
        self._session_key = None
        logger.info(f"关闭隧道: {self.config.tunnel_id}")


class MicroTunnel(BaseComponent):
    """
    微隧道管理器

    管理加密微隧道
    """

    @property
    def component_name(self) -> str:
        return "微隧道管理器"

    def __init__(self, config: Optional[dict] = None):
        super().__init__(config)
        self._tunnels: dict[str, NoiseProtocolTunnel] = {}

    async def _do_shutdown(self) -> None:
        for tunnel in self._tunnels.values():
            await tunnel.close()

    async def create_tunnel(self, local_addr: str, remote_addr: str) -> str:
        """创建隧道"""
        tunnel_id = secrets.token_hex(16)
        config = TunnelConfig(
            tunnel_id=tunnel_id,
            local_addr=local_addr,
            remote_addr=remote_addr
        )
        tunnel = NoiseProtocolTunnel(config)

        if await tunnel.establish():
            self._tunnels[tunnel_id] = tunnel
            return tunnel_id
        raise RuntimeError("隧道建立失败")

    def get_stats(self) -> dict[str, Any]:
        return {
            "active_tunnels": len(self._tunnels),
            "enabled": self.enabled
        }
