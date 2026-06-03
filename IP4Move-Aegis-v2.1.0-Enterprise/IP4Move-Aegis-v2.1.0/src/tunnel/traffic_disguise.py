"""
流量伪装模块

将流量伪装为 DoH/QUIC/TLS 等常见协议。
"""

import os
import struct
import random
import time
import logging
from typing import Optional, List
from enum import Enum

logger = logging.getLogger(__name__)


class DisguiseProtocol(Enum):
    """伪装协议类型"""
    DOH = "doh"      # DNS over HTTPS
    QUIC = "quic"     # QUIC 协议
    TLS = "tls"       # TLS 1.3
    HTTP = "http"     # 普通 HTTP


class TrafficDisguise:
    """
    流量伪装器

    将数据伪装为常见协议流量:
    - DoH: DNS over HTTPS 请求
    - QUIC: QUIC 协议包
    - TLS: TLS 1.3 握手/数据
    - HTTP: 普通 HTTP 请求
    """

    def __init__(self, protocol: DisguiseProtocol = DisguiseProtocol.TLS):
        self._protocol = protocol
        self._connection_id = os.urandom(8)

    @property
    def protocol(self) -> DisguiseProtocol:
        return self._protocol

    def disguise(self, data: bytes) -> bytes:
        """
        伪装数据

        Args:
            data: 原始数据

        Returns:
            伪装后的数据包
        """
        if self._protocol == DisguiseProtocol.DOH:
            return self._disguise_as_doh(data)
        elif self._protocol == DisguiseProtocol.QUIC:
            return self._disguise_as_quic(data)
        elif self._protocol == DisguiseProtocol.TLS:
            return self._disguise_as_tls(data)
        elif self._protocol == DisguiseProtocol.HTTP:
            return self._disguise_as_http(data)
        return data

    def undress(self, data: bytes) -> Optional[bytes]:
        """
        从伪装数据中提取原始数据

        Returns:
            原始数据，格式错误时返回 None
        """
        if self._protocol == DisguiseProtocol.DOH:
            return self._extract_from_doh(data)
        elif self._protocol == DisguiseProtocol.QUIC:
            return self._extract_from_quic(data)
        elif self._protocol == DisguiseProtocol.TLS:
            return self._extract_from_tls(data)
        elif self._protocol == DisguiseProtocol.HTTP:
            return self._extract_from_http(data)
        return data

    def _disguise_as_doh(self, data: bytes) -> bytes:
        """伪装为 DNS over HTTPS 请求"""
        # Base64 编码数据作为 DNS 查询
        import base64
        encoded = base64.b64encode(data).decode("ascii")
        # 生成随机域名
        domain = f"{''.join(random.choices('abcdefghijklmnopqrstuvwxyz', k=8))}.dns.example.com"
        # HTTP/2 请求头
        method = random.choice(["GET", "POST"])
        headers = (
            f"{method} /dns-query?dns={encoded} HTTP/2\r\n"
            f"Host: {domain}\r\n"
            f"Accept: application/dns-message\r\n"
            f"Content-Type: application/dns-message\r\n"
            f"User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36\r\n"
            f"\r\n"
        )
        return headers.encode("utf-8")

    def _extract_from_doh(self, data: bytes) -> Optional[bytes]:
        """从 DoH 请求中提取数据"""
        try:
            text = data.decode("utf-8")
            if "dns=" in text:
                import base64
                start = text.index("dns=") + 4
                end = text.index(" ", start) if " " in text[start:] else text.index("\r", start)
                encoded = text[start:end]
                return base64.b64decode(encoded)
        except Exception:
            pass
        return None

    def _disguise_as_quic(self, data: bytes) -> bytes:
        """伪装为 QUIC 协议包"""
        # QUIC Long Header (Initial)
        header_flag = 0xC3  # Long Header, Initial
        version = struct.pack("!I", 0x00000001)  # QUIC v1
        dcid_len = len(self._connection_id)
        scid_len = random.randint(4, 16)
        scid = os.urandom(scid_len)

        # Token (随机)
        token_len = random.randint(0, 32)
        token = os.urandom(token_len)

        # 构建可变长度整数
        def encode_varint(value: int) -> bytes:
            if value < 64:
                return struct.pack("!B", value)
            elif value < 16384:
                return struct.pack("!H", value | 0x4000)
            elif value < 1073741824:
                return struct.pack("!I", value | 0x80000000)
            else:
                return struct.pack("!Q", value | 0xC000000000000000)

        # Payload 长度
        payload_len = len(data) + 16  # 加上伪包号和加密开销
        length = encode_varint(payload_len)

        # 包号
        packet_number = random.randint(0, 255)

        # 组装 QUIC 包
        quic_packet = struct.pack("!B", header_flag)
        quic_packet += version
        quic_packet += struct.pack("!B", dcid_len)
        quic_packet += self._connection_id
        quic_packet += struct.pack("!B", scid_len)
        quic_packet += scid
        quic_packet += encode_varint(token_len)
        quic_packet += token
        quic_packet += length
        quic_packet += struct.pack("!B", packet_number)
        quic_packet += data

        return quic_packet

    def _extract_from_quic(self, data: bytes) -> Optional[bytes]:
        """从 QUIC 包中提取数据"""
        if len(data) < 6:
            return None
        # 验证 QUIC 头标志
        flag = data[0]
        if (flag & 0x80) == 0:  # Short Header
            dcid_len = len(self._connection_id)
            offset = 1 + dcid_len + 1  # flag + dcid + pn
            return data[offset:]
        else:  # Long Header
            offset = 1 + 4  # flag(1) + version(4)
            if offset >= len(data):
                return None
            dcid_len = data[offset]
            offset += 1 + dcid_len
            if offset >= len(data):
                return None
            scid_len = data[offset]
            offset += 1 + scid_len
            if offset >= len(data):
                return None
            # Token length (varint)
            token_len_byte = data[offset]
            token_len_prefix = token_len_byte >> 6
            if token_len_prefix == 0:
                token_len = token_len_byte & 0x3F
                offset += 1
            elif token_len_prefix == 1:
                token_len = struct.unpack("!H", data[offset:offset+2])[0] & 0x3FFF
                offset += 2
            elif token_len_prefix == 2:
                token_len = struct.unpack("!I", data[offset:offset+4])[0] & 0x3FFFFFFF
                offset += 4
            else:
                return None
            offset += token_len
            # Length (varint)
            if offset >= len(data):
                return None
            length_byte = data[offset]
            length_prefix = length_byte >> 6
            if length_prefix == 0:
                offset += 1
            elif length_prefix == 1:
                offset += 2
            elif length_prefix == 2:
                offset += 4
            else:
                offset += 8
            # Packet number (1 byte)
            offset += 1
            if offset >= len(data):
                return None
            return data[offset:]

    def _disguise_as_tls(self, data: bytes) -> bytes:
        """伪装为 TLS 1.3 数据"""
        # TLS Record Header
        content_type = random.choice([0x17, 0x16])  # Application Data / Handshake
        version = b"\x03\x03"  # TLS 1.2 (兼容)
        length = struct.pack("!H", len(data))

        tls_record = bytes([content_type]) + version + length + data
        return tls_record

    def _extract_from_tls(self, data: bytes) -> Optional[bytes]:
        """从 TLS 记录中提取数据"""
        if len(data) < 5:
            return None
        content_type = data[0]
        # version = data[1:3]
        length = struct.unpack("!H", data[3:5])[0]
        if len(data) < 5 + length:
            return None
        return data[5 : 5 + length]

    def _disguise_as_http(self, data: bytes) -> bytes:
        """伪装为 HTTP 请求"""
        import base64
        encoded = base64.b64encode(data).decode("ascii")
        paths = ["/api/v1/data", "/ws/endpoint", "/graphql", "/api/metrics"]
        path = random.choice(paths)
        headers = (
            f"POST {path} HTTP/1.1\r\n"
            f"Host: api.example.com\r\n"
            f"Content-Type: application/octet-stream\r\n"
            f"Content-Length: {len(encoded)}\r\n"
            f"Accept: application/json\r\n"
            f"Connection: keep-alive\r\n"
            f"\r\n"
            f"{encoded}"
        )
        return headers.encode("utf-8")

    def _extract_from_http(self, data: bytes) -> Optional[bytes]:
        """从 HTTP 请求中提取数据"""
        try:
            text = data.decode("utf-8")
            if "\r\n\r\n" in text:
                body = text.split("\r\n\r\n", 1)[1]
                import base64
                return base64.b64decode(body.strip())
        except Exception:
            pass
        return None

    def generate_padding(self, min_size: int = 64, max_size: int = 1400) -> bytes:
        """生成随机填充数据"""
        size = random.randint(min_size, max_size)
        return os.urandom(size)

    def inject_adversarial_noise(self, data: bytes, noise_level: float = 0.05) -> bytes:
        """
        注入对抗性噪声干扰AI分类器

        在数据包的关键位置注入精心构造的噪声，
        使AI分类器（如CNN/RNN流量分类器）产生错误预测。

        策略:
        1. 在包头部注入高熵噪声，干扰特征提取
        2. 在包尾部注入模式化噪声，干扰统计特征
        3. 随机翻转少量比特，对抗梯度攻击

        Args:
            data: 原始数据
            noise_level: 噪声强度 (0.0-1.0)

        Returns:
            添加对抗噪声后的数据
        """
        if not data or noise_level <= 0:
            return data

        data = bytearray(data)
        data_len = len(data)

        # 1. 头部高熵噪声: 干扰AI特征提取层
        header_noise_len = max(4, int(data_len * 0.02 * noise_level))
        for i in range(min(header_noise_len, data_len)):
            data[i] ^= os.urandom(1)[0]

        # 2. 尾部模式化噪声: 干扰统计特征
        tail_start = max(0, data_len - int(data_len * 0.05 * noise_level))
        # 注入类似Netflix/Zoom流量的字节模式
        patterns = [
            bytes([0x47, 0x41, 0x50, 0x31]),  # 类似HLS分片
            bytes([0x00, 0x01, 0x00, 0x01]),  # 类似MPEG-TS
            bytes([0xFF, 0xFB, 0x90, 0x44]),  # 类似MP3帧
        ]
        pattern = random.choice(patterns)
        for i in range(tail_start, data_len, len(pattern)):
            for j, b in enumerate(pattern):
                if i + j < data_len:
                    data[i + j] = data[i + j] ^ b

        # 3. 随机比特翻转: 对抗梯度攻击
        num_flips = max(1, int(data_len * 0.001 * noise_level))
        for _ in range(num_flips):
            pos = random.randint(0, data_len - 1)
            bit = random.randint(0, 7)
            data[pos] ^= (1 << bit)

        return bytes(data)

    def disguise_with_ai_evasion(self, data: bytes) -> bytes:
        """
        带AI规避的流量伪装

        组合使用协议伪装 + 对抗噪声 + 时序扰动。
        """
        disguised = self.disguise(data)
        evaded = self.inject_adversarial_noise(disguised, noise_level=0.08)
        return evaded
