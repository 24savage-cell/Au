"""
传输层模块 (安全修复版 - 性能优化版)

修复内容:
1. 严格消息大小验证防止内存耗尽
2. 添加连接超时和空闲检测
3. 防止慢速读取攻击
4. 添加速率限制
5. 改进错误处理防止信息泄露
6. 添加连接数限制

性能优化:
1. 添加 ConnectionPool 类管理 TCP 连接复用
2. 实现连接保活和空闲超时回收
3. SecureTransport.connect() 优先从连接池获取
"""

import asyncio
import struct
import logging
import time
import threading
from typing import Optional, Callable, Awaitable, Dict, Set, Tuple, Any

from src.common.rate_limiter import RateLimiter
from src.common.exceptions import NetworkError

logger = logging.getLogger(__name__)

# 安全常量
HEADER_FORMAT = "!I"      # 4字节长度前缀
HEADER_SIZE = 4
MAX_MESSAGE_SIZE = 4 * 1024 * 1024  # 4MB 最大消息 (从16MB降低)
MIN_MESSAGE_SIZE = 1       # 最小消息大小
READ_TIMEOUT = 30.0        # 读取超时(秒)
WRITE_TIMEOUT = 30.0       # 写入超时(秒)
IDLE_TIMEOUT = 300.0       # 空闲超时(秒)
MAX_CONNECTIONS_PER_IP = 100  # 每IP最大连接数
RATE_LIMIT_WINDOW = 60.0   # 速率限制窗口(秒)
MAX_MESSAGES_PER_WINDOW = 1000  # 每窗口最大消息数

# 连接池常量
POOL_MAX_SIZE = 50         # 连接池最大大小
POOL_IDLE_TIMEOUT = 60.0   # 连接池空闲超时(秒)
POOL_KEEPALIVE_INTERVAL = 30.0  # 连接保活间隔(秒)

# 全局默认连接管理器 (向后兼容)
_default_connection_manager: Optional["ConnectionManager"] = None
_default_manager_lock = threading.Lock()


class ConnectionManager:
    """
    连接管理器

    封装连接追踪逻辑，支持多进程部署时替换为共享状态实现。
    """

    def __init__(self):
        self._connection_counts: Dict[str, int] = {}
        self._lock = threading.Lock()

    def get_count(self, client_ip: str) -> int:
        """获取指定 IP 的连接数"""
        with self._lock:
            return self._connection_counts.get(client_ip, 0)

    def increment(self, client_ip: str) -> int:
        """增加连接计数，返回增加后的计数"""
        with self._lock:
            count = self._connection_counts.get(client_ip, 0) + 1
            self._connection_counts[client_ip] = count
            return count

    def decrement(self, client_ip: str) -> int:
        """减少连接计数，返回减少后的计数"""
        with self._lock:
            count = self._connection_counts.get(client_ip, 0)
            count = max(0, count - 1)
            self._connection_counts[client_ip] = count
            return count

    def check_limit(self, client_ip: str, max_connections: int) -> bool:
        """检查是否超过连接限制"""
        return self.get_count(client_ip) >= max_connections


def _get_default_manager() -> ConnectionManager:
    """获取全局默认连接管理器 (延迟初始化)"""
    global _default_connection_manager
    if _default_connection_manager is None:
        with _default_manager_lock:
            if _default_connection_manager is None:
                _default_connection_manager = ConnectionManager()
    return _default_connection_manager


class TransportSecurityError(NetworkError):
    """传输安全错误"""
    pass


class PooledConnection:
    """连接池中的连接包装器"""

    def __init__(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        host: str,
        port: int,
    ):
        self.reader = reader
        self.writer = writer
        self.host = host
        self.port = port
        self.created_at = time.time()
        self.last_used = time.time()
        self.use_count = 0
        self._is_closed = False

    @property
    def is_closed(self) -> bool:
        """检查连接是否已关闭"""
        if self._is_closed:
            return True
        # 检查底层连接状态
        if self.writer.is_closing():
            return True
        return False

    @property
    def idle_time(self) -> float:
        """返回连接空闲时间"""
        return time.time() - self.last_used

    def mark_used(self) -> None:
        """标记连接为已使用"""
        self.last_used = time.time()
        self.use_count += 1

    async def close(self) -> None:
        """关闭连接"""
        self._is_closed = True
        try:
            self.writer.close()
            await self.writer.wait_closed()
        except Exception as e:
            logger.debug(f"关闭连接池连接异常 ({self.host}:{self.port}): {e}")


class ConnectionPool:
    """
    TCP 连接池

    管理 TCP 连接复用，实现连接保活和空闲超时回收。
    """

    def __init__(
        self,
        max_size: int = POOL_MAX_SIZE,
        idle_timeout: float = POOL_IDLE_TIMEOUT,
        keepalive_interval: float = POOL_KEEPALIVE_INTERVAL,
    ):
        self._max_size = max_size
        self._idle_timeout = idle_timeout
        self._keepalive_interval = keepalive_interval
        # 连接池: (host, port) -> [PooledConnection]
        self._pools: Dict[Tuple[str, int], list] = {}
        self._lock = asyncio.Lock()
        self._cleanup_task: Optional[asyncio.Task] = None
        self._is_running = False
        self._stats = {
            "hits": 0,
            "misses": 0,
            "created": 0,
            "reclaimed": 0,
        }

    async def start(self) -> None:
        """启动连接池"""
        self._is_running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.debug("连接池已启动")

    async def stop(self) -> None:
        """停止连接池并关闭所有连接"""
        self._is_running = False
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        # 关闭所有连接
        async with self._lock:
            for pool in self._pools.values():
                for conn in pool:
                    await conn.close()
            self._pools.clear()
        logger.debug("连接池已停止")

    async def acquire(
        self,
        host: str,
        port: int,
        timeout: float = 30.0,
    ) -> Optional[PooledConnection]:
        """
        从连接池获取连接

        Args:
            host: 目标主机
            port: 目标端口
            timeout: 连接超时

        Returns:
            PooledConnection 或 None（池中没有可用连接时）
        """
        key = (host, port)

        async with self._lock:
            pool = self._pools.get(key, [])
            # 查找可用的连接
            for i, conn in enumerate(pool):
                if not conn.is_closed and conn.idle_time < self._idle_timeout:
                    # 找到可用连接
                    conn.mark_used()
                    # 从池中移除（使用后再归还）
                    pool.pop(i)
                    self._stats["hits"] += 1
                    return conn

        # 池中没有可用连接
        self._stats["misses"] += 1
        return None

    async def release(self, conn: PooledConnection) -> None:
        """
        归还连接到连接池

        Args:
            conn: 要归还的连接
        """
        if conn.is_closed:
            return

        key = (conn.host, conn.port)

        async with self._lock:
            if key not in self._pools:
                self._pools[key] = []

            pool = self._pools[key]
            if len(pool) < self._max_size:
                conn.mark_used()
                pool.append(conn)
            else:
                # 池已满，关闭连接
                await conn.close()

    async def _cleanup_loop(self) -> None:
        """定期清理过期连接"""
        while self._is_running:
            try:
                await self._cleanup_idle_connections()
                await asyncio.sleep(self._keepalive_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.debug(f"连接池清理异常: {e}")

    async def _cleanup_idle_connections(self) -> None:
        """清理空闲超时的连接"""
        now = time.time()
        async with self._lock:
            for key, pool in self._pools.items():
                expired = []
                kept = []
                for conn in pool:
                    if conn.is_closed or now - conn.last_used > self._idle_timeout:
                        expired.append(conn)
                    else:
                        kept.append(conn)

                # 关闭过期连接
                for conn in expired:
                    await conn.close()
                    self._stats["reclaimed"] += 1

                self._pools[key] = kept

    def get_stats(self) -> Dict[str, Any]:
        """获取连接池统计信息"""
        total_pooled = sum(len(pool) for pool in self._pools.values())
        return {
            **self._stats,
            "total_pooled": total_pooled,
            "pool_keys": len(self._pools),
        }


# 全局连接池
_global_connection_pool: Optional[ConnectionPool] = None
_pool_lock = asyncio.Lock()


async def _get_global_pool() -> ConnectionPool:
    """获取全局连接池（延迟初始化）"""
    global _global_connection_pool
    if _global_connection_pool is None:
        async with _pool_lock:
            if _global_connection_pool is None:
                _global_connection_pool = ConnectionPool()
                await _global_connection_pool.start()
    return _global_connection_pool


class SecureTransport:
    """
    安全网络传输层

    提供可靠的异步消息传输:
    - TCP 传输
    - 消息分帧
    - 自动重连
    - 流量控制
    - 速率限制
    - 连接管理
    - 连接池复用
    """

    def __init__(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        on_message: Optional[Callable[[bytes], Awaitable[None]]] = None,
        client_ip: Optional[str] = None,
        connection_manager: Optional["ConnectionManager"] = None,
        pooled_conn: Optional[PooledConnection] = None,
    ):
        self._reader = reader
        self._writer = writer
        self._on_message = on_message
        self._is_closed = False
        self._read_task: Optional[asyncio.Task] = None
        self._bytes_sent = 0
        self._bytes_received = 0
        self._messages_sent = 0
        self._messages_received = 0
        self._last_activity = time.time()
        self._client_ip = client_ip or "unknown"
        self._rate_limiter = RateLimiter(
            window=RATE_LIMIT_WINDOW,
            max_requests=MAX_MESSAGES_PER_WINDOW
        )
        self._lock = asyncio.Lock()
        self._connection_manager = connection_manager
        self._pooled_conn = pooled_conn
        self._host: Optional[str] = None
        self._port: Optional[int] = None

    @property
    def is_closed(self) -> bool:
        return self._is_closed

    @property
    def stats(self) -> Dict[str, Any]:
        return {
            "bytes_sent": self._bytes_sent,
            "bytes_received": self._bytes_received,
            "messages_sent": self._messages_sent,
            "messages_received": self._messages_received,
            "is_closed": self._is_closed,
            "idle_time": time.time() - self._last_activity,
        }

    def _check_rate_limit(self) -> bool:
        """检查消息速率限制"""
        return self._rate_limiter.check("messages")

    def _check_idle_timeout(self) -> bool:
        """检查空闲超时"""
        return time.time() - self._last_activity < IDLE_TIMEOUT

    async def send(self, data: bytes) -> bool:
        """发送数据 (长度前缀分帧) - 安全版本"""
        if self._is_closed:
            return False

        # 验证数据大小
        if len(data) > MAX_MESSAGE_SIZE:
            logger.error(f"Message too large: {len(data)} > {MAX_MESSAGE_SIZE}")
            self._is_closed = True
            return False

        if len(data) < MIN_MESSAGE_SIZE:
            logger.error(f"Message too small: {len(data)}")
            return False

        # 速率限制检查
        if not self._check_rate_limit():
            logger.warning(f"Rate limit exceeded for {self._client_ip}")
            self._is_closed = True
            return False

        try:
            # 抗AI时序分析: 微随机扰动发送时序
            import random
            jitter_ms = random.gauss(0, 0.5)
            if abs(jitter_ms) > 0.01:
                await asyncio.sleep(max(0, jitter_ms / 1000.0))

            header = struct.pack(HEADER_FORMAT, len(data))

            # 使用超时写入
            async with self._lock:
                self._writer.write(header + data)
                await asyncio.wait_for(
                    self._writer.drain(),
                    timeout=WRITE_TIMEOUT
                )

            self._bytes_sent += len(data) + HEADER_SIZE
            self._messages_sent += 1
            self._last_activity = time.time()
            return True

        except asyncio.TimeoutError:
            logger.error(f"Write timeout for {self._client_ip}")
            self._is_closed = True
            return False
        except (ConnectionError, OSError) as e:
            logger.error(f"Send failed: {e}")
            self._is_closed = True
            return False

    async def receive(self) -> Optional[bytes]:
        """接收一条消息 - 安全版本"""
        if self._is_closed:
            return None

        # 检查空闲超时
        if not self._check_idle_timeout():
            logger.warning(f"Idle timeout for {self._client_ip}")
            self._is_closed = True
            return None

        try:
            # 读取头部 (带超时)
            header = await asyncio.wait_for(
                self._reader.readexactly(HEADER_SIZE),
                timeout=READ_TIMEOUT
            )

            length = struct.unpack(HEADER_FORMAT, header)[0]

            # 严格验证消息大小
            if length > MAX_MESSAGE_SIZE:
                logger.error(f"Message size exceeds limit: {length} > {MAX_MESSAGE_SIZE}")
                self._is_closed = True
                return None

            if length < MIN_MESSAGE_SIZE:
                logger.error(f"Message size below minimum: {length}")
                self._is_closed = True
                return None

            # 读取数据 (带超时)
            data = await asyncio.wait_for(
                self._reader.readexactly(length),
                timeout=READ_TIMEOUT
            )

            # 验证读取的数据长度
            if len(data) != length:
                logger.error(f"Incomplete read: {len(data)} != {length}")
                self._is_closed = True
                return None

            self._bytes_received += length + HEADER_SIZE
            self._messages_received += 1
            self._last_activity = time.time()
            return data

        except asyncio.TimeoutError:
            logger.warning(f"Read timeout for {self._client_ip}")
            self._is_closed = True
            return None
        except asyncio.IncompleteReadError:
            logger.debug("Connection closed by peer")
            self._is_closed = True
            return None
        except struct.error as e:
            logger.error(f"Invalid header format: {e}")
            self._is_closed = True
            return None
        except (ConnectionError, OSError) as e:
            logger.error(f"Receive failed: {e}")
            self._is_closed = True
            return None

    async def read_loop(self) -> None:
        """持续读取消息 - 安全版本"""
        while not self._is_closed:
            # 检查空闲超时
            if not self._check_idle_timeout():
                logger.info(f"Closing idle connection from {self._client_ip}")
                break

            data = await self.receive()
            if data is None:
                break

            if self._on_message:
                try:
                    await self._on_message(data)
                except NetworkError as e:
                    logger.error(f"Message processing error: {e}")
                    # 继续处理下一条消息，不中断连接
                except Exception as e:
                    logger.error(f"Message processing error: {e}")
                    # 继续处理下一条消息，不中断连接

    def start_reading(self) -> None:
        """启动读取循环"""
        self._read_task = asyncio.create_task(self.read_loop())

    async def close(self) -> None:
        """关闭传输 - 安全版本"""
        if self._is_closed:
            return

        self._is_closed = True

        if self._read_task:
            self._read_task.cancel()
            try:
                await self._read_task
            except asyncio.CancelledError:
                pass

        # 如果这是连接池中的连接，归还到连接池
        if self._pooled_conn and self._host and self._port:
            pool = await _get_global_pool()
            await pool.release(self._pooled_conn)
        else:
            # 否则直接关闭
            try:
                if self._writer:
                    self._writer.close()
                    await self._writer.wait_closed()
            except Exception as e:
                logger.debug(f"关闭传输层连接异常: {e}")

        # 减少连接计数
        if self._connection_manager:
            self._connection_manager.decrement(self._client_ip)

    @classmethod
    async def connect(
        cls,
        host: str,
        port: int,
        on_message: Optional[Callable[[bytes], Awaitable[None]]] = None,
        timeout: float = 30,
        use_pool: bool = True,
    ) -> "SecureTransport":
        """
        连接到远程节点 - 安全版本（支持连接池）

        Args:
            host: 目标主机
            port: 目标端口
            on_message: 消息回调
            timeout: 连接超时
            use_pool: 是否使用连接池
        """
        # 尝试从连接池获取连接
        pooled_conn = None
        if use_pool:
            pool = await _get_global_pool()
            pooled_conn = await pool.acquire(host, port, timeout)

        if pooled_conn:
            # 使用连接池中的连接
            transport = cls(
                pooled_conn.reader,
                pooled_conn.writer,
                on_message,
                host,
                pooled_conn=pooled_conn,
            )
            transport._host = host
            transport._port = port
            logger.debug(f"从连接池获取连接: {host}:{port}")
            return transport

        # 创建新连接
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port),
            timeout=timeout,
        )

        # 获取对端IP
        sock = writer.get_extra_info('socket')
        client_ip = None
        if sock:
            try:
                client_ip = sock.getpeername()[0]
            except Exception as e:
                logger.debug(f"获取对端IP失败: {e}")

        transport = cls(reader, writer, on_message, client_ip)
        transport._host = host
        transport._port = port
        logger.debug(f"新建连接: {host}:{port}")
        return transport

    @classmethod
    async def create_server(
        cls,
        host: str,
        port: int,
        on_connect: Callable,
        max_connections: int = 1000,
        connection_manager: Optional["ConnectionManager"] = None,
    ) -> asyncio.Server:
        """创建服务器 - 安全版本"""
        # 使用传入的连接管理器或默认实例
        mgr = connection_manager or _get_default_manager()

        async def handle_connection(reader, writer):
            # 获取客户端IP
            client_ip = None
            try:
                sock = writer.get_extra_info('socket')
                if sock:
                    client_ip = sock.getpeername()[0]
            except Exception as e:
                logger.debug(f"获取客户端IP失败: {e}")

            client_ip = client_ip or "unknown"

            # 检查每IP连接数限制
            if mgr.check_limit(client_ip, MAX_CONNECTIONS_PER_IP):
                logger.warning(f"Connection limit exceeded for {client_ip}")
                writer.close()
                try:
                    await writer.wait_closed()
                except Exception as e:
                    logger.debug(f"关闭超限连接异常 ({client_ip}): {e}")
                return

            # 增加连接计数
            mgr.increment(client_ip)

            try:
                transport = cls(reader, writer, client_ip=client_ip, connection_manager=mgr)
                await on_connect(transport)
            finally:
                # 确保连接计数减少
                mgr.decrement(client_ip)

        server = await asyncio.start_server(handle_connection, host, port)
        logger.info(f"Server started: {host}:{port}")
        return server

    @staticmethod
    def get_timing_entropy() -> float:
        """计算传输时序的熵值"""
        import math
        import random
        # 模拟100个发送时序样本
        samples = [abs(random.gauss(0, 0.5)) for _ in range(100)]
        # 计算直方图
        bins = [0] * 10
        min_v = min(samples) if samples else 0
        max_v = max(samples) if samples else 1
        if max_v <= min_v:
            return 0.0
        for s in samples:
            idx = min(9, int((s - min_v) / (max_v - min_v) * 10))
            bins[idx] += 1
        # 计算熵
        total = len(samples)
        entropy = 0.0
        for count in bins:
            if count > 0:
                p = count / total
                entropy -= p * math.log2(p)
        return entropy


# 向后兼容
Transport = SecureTransport
