"""
协议混淆模块

将数据封装在不同协议 (TCP/UDP/ICMP) 中进行传输。
"""

import os
import struct
import random
import hashlib
import logging
from typing import Optional, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


class ProtocolType(Enum):
    """协议类型"""
    TCP = 1
    UDP = 2
    ICMP = 3


class ProtocolWrapper:
    """
    协议混淆器

    将数据封装在不同传输协议中:
    - TCP: 标准流封装
    - UDP: 数据报封装
    - ICMP: ICMP 隧道封装
    """

    # 协议头魔数
    MAGIC = b"\x4D\x58"  # "MX"

    def __init__(self, protocol: ProtocolType = ProtocolType.TCP):
        self._protocol = protocol
        self._sequence = 0

    @property
    def protocol(self) -> ProtocolType:
        return self._protocol

    def wrap(self, data: bytes) -> bytes:
        """
        封装数据

        格式:
        [MAGIC(2)] [Protocol(1)] [Flags(1)] [Sequence(4)] [Length(4)] [Data] [CRC32(4)]
        """
        self._sequence += 1
        flags = 0x00
        # 随机设置标志位
        flags |= random.randint(0, 1) << 0  # FIN
        flags |= random.randint(0, 1) << 1  # ACK

        header = self.MAGIC
        header += struct.pack("!B", self._protocol.value)
        header += struct.pack("!B", flags)
        header += struct.pack("!I", self._sequence)
        header += struct.pack("!I", len(data))

        payload = header + data

        # CRC32 校验
        crc = self._compute_crc32(payload)
        payload += struct.pack("!I", crc)

        return payload

    def unwrap(self, data: bytes) -> Optional[bytes]:
        """
        解封装数据

        Returns:
            原始数据，格式错误时返回 None
        """
        if len(data) < 16:  # 最小头大小
            return None

        # 验证魔数
        if data[:2] != self.MAGIC:
            logger.warning("协议头魔数不匹配")
            return None

        # 解析头
        protocol = struct.unpack("!B", data[2:3])[0]
        flags = struct.unpack("!B", data[3:4])[0]
        sequence = struct.unpack("!I", data[4:8])[0]
        length = struct.unpack("!I", data[8:12])[0]

        # 验证长度
        if len(data) < 16 + length:
            logger.warning(f"数据长度不匹配: 期望 {length}, 实际 {len(data) - 16}")
            return None

        # 验证 CRC32
        payload = data[:12 + length]
        expected_crc = struct.unpack("!I", data[12 + length : 16 + length])[0]
        actual_crc = self._compute_crc32(payload)
        if expected_crc != actual_crc:
            logger.warning("CRC32 校验失败")
            return None

        # 提取数据
        return data[12 : 12 + length]

    def wrap_tcp(self, data: bytes, src_port: int = 0, dst_port: int = 443) -> bytes:
        """TCP 协议封装"""
        if src_port == 0:
            src_port = random.randint(1024, 65535)
        tcp_header = struct.pack("!HHIIBBHHH",
            src_port,        # 源端口
            dst_port,        # 目标端口
            self._sequence,  # 序列号
            0,               # 确认号
            0x50,            # 数据偏移 (5 * 4 = 20 bytes)
            0x18,            # 标志位 (PSH+ACK)
            65535,           # 窗口大小
            0,               # 校验和 (简化)
            0,               # 紧急指针
        )
        return tcp_header + self.wrap(data)

    def wrap_udp(self, data: bytes, src_port: int = 0, dst_port: int = 53) -> bytes:
        """UDP 协议封装"""
        if src_port == 0:
            src_port = random.randint(1024, 65535)
        udp_header = struct.pack("!HHHH",
            src_port,        # 源端口
            dst_port,        # 目标端口
            len(data) + 8,   # 长度
            0,               # 校验和 (简化)
        )
        return udp_header + self.wrap(data)

    def wrap_icmp(self, data: bytes, icmp_type: int = 8) -> bytes:
        """ICMP 协议封装 (Echo Request)"""
        icmp_header = struct.pack("!BBH",
            icmp_type,       # 类型 (8=Echo Request, 0=Echo Reply)
            0,               # 代码
            0,               # 校验和 (稍后计算)
        )
        icmp_header += struct.pack("!H", self._sequence)  # 标识符
        icmp_header += struct.pack("!H", random.randint(0, 65535))  # 序列号
        # 计算校验和
        icmp_data = icmp_header + data
        checksum = self._compute_icmp_checksum(icmp_data)
        icmp_header = icmp_header[:2] + struct.pack("!H", checksum) + icmp_header[4:]
        return icmp_header + data

    @staticmethod
    def _compute_crc32(data: bytes) -> int:
        """计算 CRC32"""
        import binascii
        return binascii.crc32(data) & 0xFFFFFFFF

    @staticmethod
    def _compute_icmp_checksum(data: bytes) -> int:
        """计算 ICMP 校验和"""
        if len(data) % 2 != 0:
            data += b"\x00"
        total = 0
        for i in range(0, len(data), 2):
            total += (data[i] << 8) + data[i + 1]
        while total >> 16:
            total = (total & 0xFFFF) + (total >> 16)
        return ~total & 0xFFFF

    def wrap_random_protocol(self, data: bytes) -> bytes:
        """
        每包随机选择协议封装

        随机在 TCP/UDP/ICMP 之间切换，
        使AI无法通过协议类型识别流量模式。
        """
        protocol = random.choice([ProtocolType.TCP, ProtocolType.UDP, ProtocolType.ICMP])
        if protocol == ProtocolType.TCP:
            return self.wrap_tcp(data)
        elif protocol == ProtocolType.UDP:
            return self.wrap_udp(data)
        else:
            return self.wrap_icmp(data)

    def wrap_with_protocol_rotation(self, data: bytes, packet_index: int) -> bytes:
        """
        基于包序号的协议轮换封装

        使用确定性但不可预测的协议序列，
        防止AI通过协议分布模式识别。
        """
        # 使用哈希决定协议，确保确定性但不可预测
        protocol_hash = hashlib.md5(f"{packet_index}:{self._sequence}".encode()).digest()
        protocol_val = protocol_hash[0] % 3
        protocol = [ProtocolType.TCP, ProtocolType.UDP, ProtocolType.ICMP][protocol_val]

        if protocol == ProtocolType.TCP:
            return self.wrap_tcp(data)
        elif protocol == ProtocolType.UDP:
            return self.wrap_udp(data)
        else:
            return self.wrap_icmp(data)
