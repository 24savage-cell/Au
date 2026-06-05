"""
隧道管理模块 (v1.0.5 真实实现 - 策略模式重构版)

实现内容:
1. UDP 隧道: 使用 asyncio.DatagramProtocol 创建真实的 UDP socket，实现 send/receive
2. ICMP 隧道: 使用 raw socket 发送/接收 ICMP echo request/reply（需要 root 权限）
3. Tunnel dataclass 添加 _transport 字段（用于 asyncio Datagram）
4. create_tunnel() 中 UDP 分支创建真实的 UDP endpoint
5. create_tunnel() 中 ICMP 分支创建 raw socket
6. send() 和 receive() 支持 UDP 和 ICMP 数据传输
7. ICMP 隧道: 将数据封装在 ICMP echo 的 data 字段中，添加魔数头标识
8. scapy 回退: 使用 struct 构造 ICMP 包

性能优化:
1. 使用策略模式分离 TCP/UDP/ICMP 处理

ICMP 隧道协议:
  [4字节: 魔数 0x49504D31 ("IPM1")] [2字节: 序列号] [2字节: tunnel_id] [变长: payload]
  封装为 ICMP Echo Request，type=8, code=0
"""

import asyncio
import uuid
import time
import random
import struct
import socket
import logging
import os
from typing import Optional, Dict, List, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

# 尝试导入 scapy
try:
    from scapy.all import IP, ICMP, Raw
    _SCAPY_AVAILABLE = True
except ImportError:
    _SCAPY_AVAILABLE = False

# ==================== ICMP 隧道常量 ====================
ICMP_MAGIC = b"IPM1"           # ICMP 隧道魔数 (4字节)
ICMP_HEADER_SIZE = 8           # ICMP 头部大小 (type + code + checksum + id + seq)
ICMP_TUNNEL_HEADER_SIZE = 8    # 隧道头部: 4(魔数) + 2(序列号) + 2(tunnel_id)
ICMP_ECHO_REQUEST = 8          # ICMP Echo Request 类型
ICMP_ECHO_REPLY = 0            # ICMP Echo Reply 类型
ICMP_MAX_PAYLOAD = 1400        # ICMP 隧道最大 payload 大小
ICMP_SOCKET_RECV_SIZE = 65535  # ICMP raw socket 接收缓冲区大小


class TunnelState(Enum):
    """隧道状态"""
    INITIALIZING = "initializing"
    CONNECTED = "connected"
    ACTIVE = "active"
    CLOSING = "closing"
    CLOSED = "closed"
    ERROR = "error"


class TunnelProtocol(Enum):
    """隧道协议"""
    TCP = "tcp"
    UDP = "udp"
    ICMP = "icmp"


@dataclass
class TunnelConfig:
    """隧道配置"""
    protocol: TunnelProtocol = TunnelProtocol.TCP
    keepalive_interval: float = 30
    max_retries: int = 3
    timeout: float = 30
    mtu: int = 1400
    disguise_protocol: Optional[str] = None  # doh, quic, tls


@dataclass
class Tunnel:
    """隧道实例"""
    tunnel_id: str
    config: TunnelConfig
    state: TunnelState = TunnelState.INITIALIZING
    created_at: float = field(default_factory=time.time)
    last_activity: float = field(default_factory=time.time)
    bytes_sent: int = 0
    bytes_received: int = 0
    remote_address: Optional[str] = None
    remote_port: Optional[int] = None
    _reader: Optional[asyncio.StreamReader] = None
    _writer: Optional[asyncio.StreamWriter] = None
    _transport: Optional[asyncio.DatagramTransport] = None  # UDP asyncio transport
    _udp_protocol: Optional['UDPClientProtocol'] = None      # UDP 协议实例
    _icmp_socket: Optional[socket.socket] = None              # ICMP raw socket
    _icmp_seq: int = 0                                        # ICMP 序列号计数器
    _icmp_recv_buffer: asyncio.Queue = field(default_factory=asyncio.Queue)  # ICMP 接收缓冲区
    _icmp_recv_task: Optional[asyncio.Task] = None            # ICMP 接收任务

    @property
    def is_active(self) -> bool:
        """检查隧道是否处于活跃状态"""
        return self.state in (TunnelState.CONNECTED, TunnelState.ACTIVE)

    @property
    def age(self) -> float:
        """返回隧道已创建的时间（秒）"""
        return time.time() - self.created_at

    @property
    def idle_time(self) -> float:
        """返回隧道空闲时间（秒）"""
        return time.time() - self.last_activity


# ==================== ICMP 工具函数 ====================

def _icmp_checksum(data: bytes) -> int:
    """
    计算 ICMP 校验和（RFC 1071）

    16位反码求和，将进位折叠回低位。
    """
    if len(data) % 2 == 1:
        data = data + b'\x00'

    total = 0
    for i in range(0, len(data), 2):
        word = (data[i] << 8) + data[i + 1]
        total += word

    while total >> 16:
        total = (total & 0xFFFF) + (total >> 16)

    return ~total & 0xFFFF


def _build_icmp_echo_request(
    icmp_id: int,
    seq: int,
    payload: bytes,
) -> bytes:
    """
    构造 ICMP Echo Request 包（使用 struct）

    ICMP 头部格式 (8字节):
      [1字节: type=8] [1字节: code=0] [2字节: checksum] [2字节: identifier] [2字节: sequence]
    """
    # 构造 ICMP 头部（校验和先填 0）
    header = struct.pack("!BBHHH", ICMP_ECHO_REQUEST, 0, 0, icmp_id, seq)

    # 计算校验和
    checksum_data = header + payload
    chksum = _icmp_checksum(checksum_data)

    # 重新构造带校验和的头部
    header = struct.pack("!BBHHH", ICMP_ECHO_REQUEST, 0, chksum, icmp_id, seq)
    return header + payload


def _parse_icmp_echo_reply(data: bytes) -> Optional[Tuple[int, int, bytes]]:
    """
    解析 ICMP Echo Reply 包

    Returns:
        (icmp_id, sequence, payload) 或 None
    """
    if len(data) < ICMP_HEADER_SIZE:
        return None

    icmp_type, code, checksum, icmp_id, seq = struct.unpack("!BBHHH", data[:ICMP_HEADER_SIZE])

    if icmp_type != ICMP_ECHO_REPLY:
        return None

    payload = data[ICMP_HEADER_SIZE:]
    return (icmp_id, seq, payload)


def _build_icmp_tunnel_payload(tunnel_id_int: int, seq: int, data: bytes) -> bytes:
    """
    构造 ICMP 隧道 payload

    格式: [4字节: 魔数 "IPM1"] [2字节: 序列号] [2字节: tunnel_id] [变长: data]
    """
    tunnel_id_bytes = struct.pack("!H", tunnel_id_int & 0xFFFF)
    seq_bytes = struct.pack("!H", seq & 0xFFFF)
    return ICMP_MAGIC + seq_bytes + tunnel_id_bytes + data


def _parse_icmp_tunnel_payload(payload: bytes) -> Optional[Tuple[int, int, bytes]]:
    """
    解析 ICMP 隧道 payload

    Returns:
        (tunnel_id, seq, data) 或 None（格式不匹配时）
    """
    if len(payload) < ICMP_TUNNEL_HEADER_SIZE:
        return None

    magic = payload[:4]
    if magic != ICMP_MAGIC:
        return None

    seq = struct.unpack("!H", payload[4:6])[0]
    tunnel_id = struct.unpack("!H", payload[6:8])[0]
    data = payload[8:]
    return (tunnel_id, seq, data)


def _build_icmp_tunnel_packet(
    icmp_id: int,
    seq: int,
    tunnel_id_int: int,
    tunnel_seq: int,
    data: bytes,
) -> bytes:
    """
    构造完整的 ICMP 隧道包

    将隧道 payload 封装在 ICMP Echo Request 中。
    """
    tunnel_payload = _build_icmp_tunnel_payload(tunnel_id_int, tunnel_seq, data)
    return _build_icmp_echo_request(icmp_id, seq, tunnel_payload)


# ==================== UDP 协议处理器 ====================

class UDPClientProtocol(asyncio.DatagramProtocol):
    """
    UDP 客户端协议处理器

    用于 UDP 隧道的 send/receive。
    """

    def __init__(self, tunnel: Tunnel):
        self._tunnel = tunnel
        self._transport: Optional[asyncio.DatagramTransport] = None
        self._recv_queue: asyncio.Queue = asyncio.Queue()

    def connection_made(self, transport: asyncio.DatagramTransport) -> None:
        """UDP 连接建立"""
        self._transport = transport

    def datagram_received(self, data: bytes, addr: Tuple[str, int]) -> None:
        """收到 UDP 数据报"""
        self._recv_queue.put_nowait(data)

    def error_received(self, exc: Exception) -> None:
        """UDP 错误"""
        logger.warning(f"UDP 隧道 {self._tunnel.tunnel_id} 错误: {exc}")

    def connection_lost(self, exc: Optional[Exception]) -> None:
        """UDP 连接丢失"""
        if exc:
            logger.error(f"UDP 隧道 {self._tunnel.tunnel_id} 连接丢失: {exc}")

    def send(self, data: bytes) -> None:
        """发送 UDP 数据"""
        if self._transport and self._tunnel.remote_address and self._tunnel.remote_port:
            self._transport.sendto(data, (self._tunnel.remote_address, self._tunnel.remote_port))

    async def recv(self, timeout: float = 30.0) -> Optional[bytes]:
        """接收 UDP 数据"""
        try:
            return await asyncio.wait_for(self._recv_queue.get(), timeout=timeout)
        except asyncio.TimeoutError:
            return None


# ==================== ICMP 接收任务 ====================

async def _icmp_recv_loop(tunnel: Tunnel) -> None:
    """
    ICMP 接收循环

    从 raw socket 读取 ICMP Echo Reply，解析隧道 payload，
    放入隧道的接收缓冲区。
    """
    if tunnel._icmp_socket is None:
        return

    tunnel_id_int = int(tunnel.tunnel_id, 16) & 0xFFFF
    loop = asyncio.get_event_loop()

    while tunnel.is_active:
        try:
            # 使用 asyncio 的 socket 接收
            data = await loop.sock_recv(tunnel._icmp_socket, ICMP_SOCKET_RECV_SIZE)
            if not data:
                continue

            # 跳过 IP 头部（前 20 字节）
            ip_header_len = (data[0] & 0x0F) * 4
            if len(data) < ip_header_len + ICMP_HEADER_SIZE:
                continue

            icmp_data = data[ip_header_len:]
            result = _parse_icmp_echo_reply(icmp_data)
            if result is None:
                continue

            icmp_id, seq, payload = result

            # 解析隧道 payload
            tunnel_result = _parse_icmp_tunnel_payload(payload)
            if tunnel_result is None:
                continue

            recv_tunnel_id, recv_seq, recv_data = tunnel_result

            # 检查 tunnel_id 是否匹配
            if recv_tunnel_id != tunnel_id_int:
                continue

            # 放入接收缓冲区
            await tunnel._icmp_recv_buffer.put(recv_data)
            tunnel.bytes_received += len(recv_data)
            tunnel.last_activity = time.time()

        except asyncio.CancelledError:
            break
        except socket.timeout:
            continue
        except Exception as e:
            if tunnel.is_active:
                logger.debug(f"ICMP 接收异常: {e}")
            break


# ==================== 策略模式: 隧道传输策略 ====================

class TunnelTransportStrategy(ABC):
    """隧道传输策略抽象基类"""

    @abstractmethod
    async def send(self, tunnel: Tunnel, data: bytes) -> bool:
        """发送数据"""
        pass

    @abstractmethod
    async def receive(self, tunnel: Tunnel, max_size: int = 65536) -> Optional[bytes]:
        """接收数据"""
        pass


class TCPTransportStrategy(TunnelTransportStrategy):
    """TCP 传输策略"""

    async def send(self, tunnel: Tunnel, data: bytes) -> bool:
        """通过 TCP 发送数据"""
        if tunnel._writer:
            tunnel._writer.write(data)
            await tunnel._writer.drain()
            tunnel.bytes_sent += len(data)
            tunnel.last_activity = time.time()
            return True
        return False

    async def receive(self, tunnel: Tunnel, max_size: int = 65536) -> Optional[bytes]:
        """通过 TCP 接收数据"""
        if tunnel._reader:
            data = await tunnel._reader.read(max_size)
            if data:
                tunnel.bytes_received += len(data)
                tunnel.last_activity = time.time()
                return data
        return None


class UDPTransportStrategy(TunnelTransportStrategy):
    """UDP 传输策略"""

    async def send(self, tunnel: Tunnel, data: bytes) -> bool:
        """通过 UDP 发送数据"""
        if tunnel._udp_protocol:
            tunnel._udp_protocol.send(data)
            tunnel.bytes_sent += len(data)
            tunnel.last_activity = time.time()
            return True
        return False

    async def receive(self, tunnel: Tunnel, max_size: int = 65536) -> Optional[bytes]:
        """通过 UDP 接收数据"""
        if tunnel._udp_protocol:
            data = await tunnel._udp_protocol.recv(timeout=tunnel.config.timeout)
            if data:
                tunnel.bytes_received += len(data)
                tunnel.last_activity = time.time()
                return data
        return None


class ICMPTransportStrategy(TunnelTransportStrategy):
    """ICMP 传输策略"""

    async def send(self, tunnel: Tunnel, data: bytes) -> bool:
        """通过 ICMP 发送数据"""
        if tunnel._icmp_socket:
            tunnel_id_int = int(tunnel.tunnel_id, 16) & 0xFFFF
            tunnel._icmp_seq += 1

            # 构造 ICMP 隧道包
            icmp_id = tunnel_id_int & 0xFFFF
            icmp_seq = tunnel._icmp_seq & 0xFFFF
            tunnel_seq = tunnel._icmp_seq & 0xFFFF

            # 分片发送（如果数据超过 ICMP 最大 payload）
            offset = 0
            while offset < len(data):
                chunk = data[offset:offset + ICMP_MAX_PAYLOAD]
                packet = _build_icmp_tunnel_packet(
                    icmp_id, icmp_seq, tunnel_id_int, tunnel_seq, chunk
                )
                tunnel._icmp_socket.sendto(
                    packet,
                    (tunnel.remote_address or "0.0.0.0", 0),
                )
                offset += ICMP_MAX_PAYLOAD

            tunnel.bytes_sent += len(data)
            tunnel.last_activity = time.time()
            return True
        return False

    async def receive(self, tunnel: Tunnel, max_size: int = 65536) -> Optional[bytes]:
        """通过 ICMP 接收数据"""
        try:
            data = await asyncio.wait_for(
                tunnel._icmp_recv_buffer.get(),
                timeout=tunnel.config.timeout,
            )
            return data
        except asyncio.TimeoutError:
            return None


# ==================== 策略工厂 ====================

class TransportStrategyFactory:
    """传输策略工厂"""

    _strategies: Dict[TunnelProtocol, TunnelTransportStrategy] = {
        TunnelProtocol.TCP: TCPTransportStrategy(),
        TunnelProtocol.UDP: UDPTransportStrategy(),
        TunnelProtocol.ICMP: ICMPTransportStrategy(),
    }

    @classmethod
    def get_strategy(cls, protocol: TunnelProtocol) -> TunnelTransportStrategy:
        """获取指定协议的传输策略"""
        return cls._strategies.get(protocol, cls._strategies[TunnelProtocol.TCP])


# ==================== TunnelManager ====================

class TunnelManager:
    """
    隧道管理器 (v1.0.5 真实实现 - 策略模式重构版)

    管理多个隧道连接的创建、维护和销毁。
    支持 TCP、UDP、ICMP 三种隧道协议。
    使用策略模式分离不同协议的处理逻辑。
    """

    def __init__(self, default_config: Optional[TunnelConfig] = None):
        self._default_config = default_config or TunnelConfig()
        self._tunnels: Dict[str, Tunnel] = {}
        self._lock = asyncio.Lock()
        self._keepalive_task: Optional[asyncio.Task] = None
        self._is_running = False

    @property
    def active_count(self) -> int:
        """返回活跃隧道数量"""
        return sum(1 for t in self._tunnels.values() if t.is_active)

    @property
    def total_count(self) -> int:
        """返回总隧道数量"""
        return len(self._tunnels)

    async def create_tunnel(
        self,
        remote_address: str,
        remote_port: int,
        config: Optional[TunnelConfig] = None,
    ) -> Tunnel:
        """
        创建新隧道

        Args:
            remote_address: 远程地址
            remote_port: 远程端口
            config: 隧道配置

        Returns:
            隧道实例
        """
        cfg = config or self._default_config
        tunnel_id = str(uuid.uuid4())[:8]

        tunnel = Tunnel(
            tunnel_id=tunnel_id,
            config=cfg,
            remote_address=remote_address,
            remote_port=remote_port,
        )

        async with self._lock:
            self._tunnels[tunnel_id] = tunnel

        try:
            if cfg.protocol == TunnelProtocol.TCP:
                # TCP 隧道: 使用 asyncio.open_connection
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(remote_address, remote_port),
                    timeout=cfg.timeout,
                )
                tunnel._reader = reader
                tunnel._writer = writer
                tunnel.state = TunnelState.CONNECTED

            elif cfg.protocol == TunnelProtocol.UDP:
                # UDP 隧道: 创建真实的 UDP endpoint
                loop = asyncio.get_event_loop()
                udp_protocol = UDPClientProtocol(tunnel)
                transport, _ = await loop.create_datagram_endpoint(
                    lambda: udp_protocol,
                    remote_addr=(remote_address, remote_port),
                )
                tunnel._transport = transport
                tunnel._udp_protocol = udp_protocol
                tunnel.state = TunnelState.CONNECTED

            elif cfg.protocol == TunnelProtocol.ICMP:
                # ICMP 隧道: 创建 raw socket
                try:
                    icmp_socket = socket.socket(
                        family=socket.AF_INET,
                        type=socket.SOCK_RAW,
                        proto=socket.IPPROTO_ICMP,
                    )
                    icmp_socket.settimeout(1.0)
                    tunnel._icmp_socket = icmp_socket

                    # 启动 ICMP 接收任务
                    tunnel._icmp_recv_task = asyncio.create_task(
                        _icmp_recv_loop(tunnel)
                    )

                    tunnel.state = TunnelState.CONNECTED
                    logger.info(f"ICMP 隧道 {tunnel_id} raw socket 已创建")
                except PermissionError:
                    logger.error("ICMP 隧道需要 root 权限")
                    tunnel.state = TunnelState.ERROR
                    raise RuntimeError("ICMP 隧道需要 root 权限以创建 raw socket")
                except OSError as e:
                    logger.error(f"ICMP raw socket 创建失败: {e}")
                    tunnel.state = TunnelState.ERROR
                    raise

            tunnel.state = TunnelState.ACTIVE
            tunnel.last_activity = time.time()
            logger.info(f"隧道 {tunnel_id} 已建立: {remote_address}:{remote_port} ({cfg.protocol.value})")
        except Exception as e:
            tunnel.state = TunnelState.ERROR
            logger.error(f"隧道 {tunnel_id} 创建失败: {e}")
            raise

        return tunnel

    async def send(self, tunnel_id: str, data: bytes) -> bool:
        """
        通过隧道发送数据

        使用策略模式处理不同协议的发送逻辑。
        """
        tunnel = self._tunnels.get(tunnel_id)
        if not tunnel or not tunnel.is_active:
            return False

        try:
            strategy = TransportStrategyFactory.get_strategy(tunnel.config.protocol)
            result = await strategy.send(tunnel, data)
            if not result:
                tunnel.state = TunnelState.ERROR
            return result
        except Exception as e:
            logger.error(f"隧道 {tunnel_id} 发送失败: {e}")
            tunnel.state = TunnelState.ERROR
            return False

    async def receive(self, tunnel_id: str, max_size: int = 65536) -> Optional[bytes]:
        """
        从隧道接收数据

        使用策略模式处理不同协议的接收逻辑。
        """
        tunnel = self._tunnels.get(tunnel_id)
        if not tunnel or not tunnel.is_active:
            return None

        try:
            strategy = TransportStrategyFactory.get_strategy(tunnel.config.protocol)
            return await strategy.receive(tunnel, max_size)
        except Exception as e:
            logger.error(f"隧道 {tunnel_id} 接收失败: {e}")
            tunnel.state = TunnelState.ERROR
            return None

    async def close_tunnel(self, tunnel_id: str) -> bool:
        """关闭隧道"""
        tunnel = self._tunnels.get(tunnel_id)
        if not tunnel:
            return False

        tunnel.state = TunnelState.CLOSING

        # 关闭 TCP 连接
        try:
            if tunnel._writer:
                tunnel._writer.close()
                await tunnel._writer.wait_closed()
        except Exception:
            pass

        # 关闭 UDP transport
        try:
            if tunnel._transport:
                tunnel._transport.close()
        except Exception:
            pass

        # 关闭 ICMP socket
        try:
            if tunnel._icmp_recv_task:
                tunnel._icmp_recv_task.cancel()
                try:
                    await tunnel._icmp_recv_task
                except asyncio.CancelledError:
                    pass
            if tunnel._icmp_socket:
                tunnel._icmp_socket.close()
        except Exception:
            pass

        tunnel.state = TunnelState.CLOSED
        logger.info(f"隧道 {tunnel_id} 已关闭")
        return True

    async def close_all(self) -> int:
        """关闭所有隧道"""
        count = 0
        for tunnel_id in list(self._tunnels.keys()):
            if await self.close_tunnel(tunnel_id):
                count += 1
        return count

    async def _keepalive_loop(self) -> None:
        """Keepalive 循环"""
        while self._is_running:
            try:
                now = time.time()
                for tunnel in list(self._tunnels.values()):
                    if tunnel.is_active:
                        if now - tunnel.last_activity > tunnel.config.keepalive_interval:
                            # 发送 keepalive
                            await self._send_keepalive(tunnel)
            except asyncio.CancelledError:
                break
            await asyncio.sleep(5)

    async def _send_keepalive(self, tunnel: Tunnel) -> None:
        """向指定隧道发送 keepalive"""
        try:
            if tunnel.config.protocol == TunnelProtocol.TCP:
                if tunnel._writer:
                    try:
                        tunnel._writer.write(b"\x00")
                        await tunnel._writer.drain()
                    except Exception:
                        tunnel.state = TunnelState.ERROR
            elif tunnel.config.protocol == TunnelProtocol.UDP:
                if tunnel._udp_protocol:
                    try:
                        tunnel._udp_protocol.send(b"\x00")
                    except Exception:
                        tunnel.state = TunnelState.ERROR
            elif tunnel.config.protocol == TunnelProtocol.ICMP:
                if tunnel._icmp_socket:
                    try:
                        tunnel._icmp_seq += 1
                        icmp_id = int(tunnel.tunnel_id, 16) & 0xFFFF
                        packet = _build_icmp_echo_request(
                            icmp_id, tunnel._icmp_seq & 0xFFFF, b""
                        )
                        tunnel._icmp_socket.sendto(
                            packet,
                            (tunnel.remote_address or "0.0.0.0", 0),
                        )
                    except Exception:
                        tunnel.state = TunnelState.ERROR
        except Exception as e:
            logger.debug(f"发送 keepalive 失败: {e}")

    async def start(self) -> None:
        """启动隧道管理器"""
        self._is_running = True
        self._keepalive_task = asyncio.create_task(self._keepalive_loop())

    async def stop(self) -> None:
        """停止隧道管理器"""
        self._is_running = False
        if self._keepalive_task:
            self._keepalive_task.cancel()
            try:
                await self._keepalive_task
            except asyncio.CancelledError:
                pass
        await self.close_all()

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_tunnels": len(self._tunnels),
            "active_tunnels": self.active_count,
            "total_bytes_sent": sum(t.bytes_sent for t in self._tunnels.values()),
            "total_bytes_received": sum(t.bytes_received for t in self._tunnels.values()),
        }

    def drift_tunnel_characteristics(self, tunnel_id: str) -> bool:
        """
        隧道特征实时漂移

        定期修改隧道的流量特征（MTU、keepalive间隔等），
        使AI无法通过长期特征追踪隧道。

        Returns:
            是否成功漂移
        """
        tunnel = self._tunnels.get(tunnel_id)
        if not tunnel or not tunnel.is_active:
            return False

        # 随机修改隧道配置
        cfg = tunnel.config
        # MTU 漂移: 在 1200-1400 之间随机
        cfg.mtu = random.randint(1200, 1400)
        # Keepalive 漂移: 在 15-45 秒之间随机
        cfg.keepalive_interval = random.uniform(15, 45)
        # 随机切换伪装协议
        disguise_protocols = [None, "doh", "quic", "tls"]
        cfg.disguise_protocol = random.choice(disguise_protocols)

        tunnel.last_activity = time.time()
        logger.debug(f"隧道 {tunnel_id} 特征漂移: MTU={cfg.mtu}, keepalive={cfg.keepalive_interval:.1f}s")
        return True

    def drift_all_active_tunnels(self) -> int:
        """
        漂移所有活跃隧道的特征

        Returns:
            漂移的隧道数量
        """
        count = 0
        for tunnel_id in list(self._tunnels.keys()):
            if self.drift_tunnel_characteristics(tunnel_id):
                count += 1
        return count
