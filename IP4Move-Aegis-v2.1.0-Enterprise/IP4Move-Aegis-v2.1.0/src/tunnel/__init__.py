"""
隧道模块

提供隧道管理、协议混淆和流量伪装功能。
"""

from src.tunnel.tunnel_manager import TunnelManager
from src.tunnel.protocol_wrapper import ProtocolWrapper
from src.tunnel.traffic_disguise import TrafficDisguise

__all__ = ["TunnelManager", "ProtocolWrapper", "TrafficDisguise"]
