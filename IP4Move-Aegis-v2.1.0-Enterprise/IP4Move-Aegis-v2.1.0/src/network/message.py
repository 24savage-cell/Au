"""
消息协议模块

定义网络消息格式和序列化。

安全说明:
- 消息包含 HMAC 完整性校验
- 反序列化时验证消息完整性
- payload_len 有最大值限制
"""

import os
import struct
import json
import time
import hashlib
import hmac
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from enum import IntEnum

logger = logging.getLogger(__name__)

# 安全常量
HMAC_KEY_SIZE = 32
HMAC_SIZE = 32
MAX_PAYLOAD_SIZE = 16 * 1024 * 1024  # 16MB
MAX_MESSAGE_SIZE = 17 * 1024 * 1024  # 16MB + header + HMAC


class MessageType(IntEnum):
    """消息类型"""
    # 控制消息
    PING = 0x01
    PONG = 0x02
    HELLO = 0x03
    DISCONNECT = 0x04

    # 路由消息
    DATA = 0x10
    ONION_WRAP = 0x11
    ONION_UNWRAP = 0x12
    PATH_REQUEST = 0x13
    PATH_RESPONSE = 0x14

    # Mixnet 消息
    MIX_BATCH = 0x20
    MIX_FLUSH = 0x21
    MIX_ACK = 0x22

    # DHT 消息
    DHT_PING = 0x30
    DHT_STORE = 0x31
    DHT_FIND_VALUE = 0x32
    DHT_FIND_NODE = 0x33

    # 共识消息
    VOTE_PROPOSAL = 0x40
    VOTE_CAST = 0x41
    VOTE_RESULT = 0x42
    THRESHOLD_SIG = 0x43

    # 安全消息
    KEY_EXCHANGE = 0x50
    KEY_ROTATION = 0x51
    NOISE = 0x52


@dataclass
class Message:
    """网络消息"""
    msg_type: MessageType
    payload: bytes
    msg_id: str = ""
    source: str = ""
    destination: str = ""
    timestamp: float = field(default_factory=time.time)
    ttl: int = 64
    version: int = 1
    # HMAC 密钥 (用于签名/验证)
    _hmac_key: bytes = field(default=b"", repr=False)

    def __post_init__(self):
        if not self.msg_id:
            self.msg_id = os.urandom(16).hex()
        # 验证 msg_id 长度不超过 32 字符
        if len(self.msg_id) > 32:
            logger.warning(
                f"消息 ID 长度 {len(self.msg_id)} 超过 32 字符限制，"
                f"使用 SHA256 哈希截断"
            )
            self.msg_id = hashlib.sha256(self.msg_id.encode()).hexdigest()[:32]

    def serialize(self, hmac_key: Optional[bytes] = None) -> bytes:
        """
        序列化消息
        
        Args:
            hmac_key: HMAC 密钥，用于消息完整性校验
                     如果不提供，使用实例的 _hmac_key
        
        安全说明:
        - 消息末尾附加 HMAC-SHA256 签名
        - 防止消息在网络传输中被篡改
        """
        key = hmac_key or self._hmac_key
        
        header = struct.pack(
            "!BBH32s32s32sQBI",
            self.version,
            self.msg_type,
            self.ttl,
            self.msg_id.encode()[:32].ljust(32, b"\x00"),
            self.source.encode()[:32].ljust(32, b"\x00"),
            self.destination.encode()[:32].ljust(32, b"\x00"),
            int(self.timestamp * 1000),
            len(self.payload),
            0,  # reserved
        )
        message_data = header + self.payload
        
        # 添加 HMAC 完整性校验
        if key:
            mac = hmac.new(key, message_data, hashlib.sha256).digest()
            return message_data + mac
        else:
            # 无密钥时添加空 HMAC (向后兼容)
            return message_data + (b"\x00" * HMAC_SIZE)

    @classmethod
    def deserialize(cls, data: bytes, hmac_key: Optional[bytes] = None, verify: bool = True) -> "Message":
        """
        反序列化消息
        
        Args:
            data: 原始字节数据
            hmac_key: HMAC 密钥，用于验证消息完整性
            verify: 是否验证 HMAC (默认 True)
        
        Raises:
            ValueError: 消息格式错误或 HMAC 验证失败
        
        安全说明:
        - 验证 HMAC 确保消息未被篡改
        - payload_len 有最大值限制，防止内存耗尽
        """
        min_header_size = 1 + 1 + 2 + 32 + 32 + 32 + 8 + 1 + 4  # 113 bytes (与 serialize 格式 !BBH32s32s32sQBI 一致)
        
        if len(data) < min_header_size + HMAC_SIZE:
            raise ValueError("消息数据太短")

        offset = 0
        version = data[offset]
        offset += 1
        
        # 安全修复: 验证消息类型
        try:
            msg_type = MessageType(data[offset])
        except ValueError:
            raise ValueError(f"无效的消息类型: {data[offset]}")
        offset += 1
        
        ttl = struct.unpack("!H", data[offset:offset+2])[0]
        offset += 2
        msg_id = data[offset:offset+32].rstrip(b"\x00").decode('utf-8', errors='replace')
        offset += 32
        source = data[offset:offset+32].rstrip(b"\x00").decode('utf-8', errors='replace')
        offset += 32
        destination = data[offset:offset+32].rstrip(b"\x00").decode('utf-8', errors='replace')
        offset += 32
        timestamp_ms = struct.unpack("!Q", data[offset:offset+8])[0]
        offset += 8
        payload_len = data[offset]  # B format (1 byte), 与 serialize 一致
        offset += 1
        offset += 4  # reserved (I, 4 bytes, 与 serialize 一致)

        # 安全修复: 验证 payload_len
        if payload_len > MAX_PAYLOAD_SIZE:
            raise ValueError(f"payload_len 超过最大值: {payload_len} > {MAX_PAYLOAD_SIZE}")
        
        # 验证数据长度
        expected_len = min_header_size + payload_len + HMAC_SIZE
        if len(data) < expected_len:
            raise ValueError(f"消息数据不完整: 期望 {expected_len} 字节, 实际 {len(data)} 字节")

        payload = data[offset:offset+payload_len]
        timestamp = timestamp_ms / 1000.0
        
        # HMAC 验证
        received_mac = data[-HMAC_SIZE:]
        message_data = data[:-HMAC_SIZE]
        
        if verify and hmac_key:
            expected_mac = hmac.new(hmac_key, message_data, hashlib.sha256).digest()
            if not hmac.compare_digest(received_mac, expected_mac):
                raise ValueError("HMAC 验证失败: 消息可能被篡改")
        elif verify and received_mac != b"\x00" * HMAC_SIZE:
            # 有 HMAC 但没有提供密钥
            logger.warning("消息包含 HMAC 但未提供验证密钥")

        return cls(
            version=version,
            msg_type=msg_type,
            ttl=ttl,
            msg_id=msg_id,
            source=source,
            destination=destination,
            timestamp=timestamp,
            payload=payload,
            _hmac_key=hmac_key or b"",
        )

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "msg_type": self.msg_type.name,
            "msg_id": self.msg_id,
            "source": self.source,
            "destination": self.destination,
            "timestamp": self.timestamp,
            "payload_size": len(self.payload),
        }


class MessageProtocol:
    """
    消息协议处理器

    提供消息创建和处理的便捷接口。
    """

    def __init__(self, node_id: str = ""):
        self._node_id = node_id
        self._handlers: Dict[MessageType, list] = {}

    def register_handler(self, msg_type: MessageType, handler) -> None:
        """注册消息处理器"""
        if msg_type not in self._handlers:
            self._handlers[msg_type] = []
        self._handlers[msg_type].append(handler)

    def create_ping(self, destination: str = "") -> Message:
        """创建 PING 消息"""
        return Message(
            msg_type=MessageType.PING,
            payload=b"",
            source=self._node_id,
            destination=destination,
        )

    def create_pong(self, ping_msg: Message) -> Message:
        """创建 PONG 响应"""
        return Message(
            msg_type=MessageType.PONG,
            payload=ping_msg.msg_id.encode(),
            source=self._node_id,
            destination=ping_msg.source,
        )

    def create_hello(self, info: Dict[str, Any]) -> Message:
        """创建 HELLO 消息"""
        payload = json.dumps(info).encode()
        return Message(
            msg_type=MessageType.HELLO,
            payload=payload,
            source=self._node_id,
        )

    def create_data(self, data: bytes, destination: str = "") -> Message:
        """创建 DATA 消息"""
        return Message(
            msg_type=MessageType.DATA,
            payload=data,
            source=self._node_id,
            destination=destination,
        )

    def create_onion(self, wrapped_data: bytes, destination: str = "") -> Message:
        """创建洋葱消息"""
        return Message(
            msg_type=MessageType.ONION_WRAP,
            payload=wrapped_data,
            source=self._node_id,
            destination=destination,
        )

    async def handle_message(self, message: Message) -> None:
        """处理接收到的消息"""
        handlers = self._handlers.get(message.msg_type, [])
        for handler in handlers:
            try:
                result = handler(message)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                logger.error(f"消息处理错误 [{message.msg_type.name}]: {e}")

    def sign_message(self, message: Message, signing_key: bytes) -> Message:
        """
        使用后量子签名签署消息

        签名附加到 payload 中。
        回退时使用 HMAC-SHA512，并在签名前添加 1 字节标志位:
        0x00 = PQC 签名, 0x01 = HMAC 签名
        """
        try:
            from cryptography.hazmat.primitives.asymmetric.ml_dsa import (
                MLDSA65PrivateKey,
            )
            private_key = MLDSA65PrivateKey.from_private_bytes(signing_key)
            signature = private_key.sign(message.serialize())
            # PQC 签名: 标志位 0x00 + 签名
            signed_payload = struct.pack("!B", 0x00) + struct.pack("!I", len(signature)) + signature + message.payload
            message.payload = signed_payload
            return message
        except ImportError:
            import hmac as hmac_mod
            mac = hmac_mod.new(signing_key, message.serialize(), hashlib.sha512).digest()
            # HMAC 签名: 标志位 0x01 + 签名
            signed_payload = struct.pack("!B", 0x01) + struct.pack("!I", len(mac)) + mac + message.payload
            message.payload = signed_payload
            return message

    def verify_message_signature(self, message: Message, verify_key: bytes) -> bool:
        """
        验证消息的后量子签名

        支持两种签名格式:
        - 标志位 0x00: PQC 签名 (ML-DSA)
        - 标志位 0x01: HMAC-SHA512 签名 (回退)
        """
        try:
            # 解析标志位
            flag = message.payload[0]
            sig_len = struct.unpack("!I", message.payload[1:5])[0]
            signature = message.payload[5:5+sig_len]
            original_payload = message.payload[5+sig_len:]
            original_msg = Message(
                msg_type=message.msg_type,
                payload=original_payload,
                msg_id=message.msg_id,
                source=message.source,
                destination=message.destination,
                timestamp=message.timestamp,
                ttl=message.ttl,
                version=message.version,
            )

            if flag == 0x00:
                # PQC 签名验证
                from cryptography.hazmat.primitives.asymmetric.ml_dsa import (
                    MLDSA65PublicKey,
                )
                public_key = MLDSA65PublicKey.from_public_bytes(verify_key)
                public_key.verify(signature, original_msg.serialize())
                return True
            elif flag == 0x01:
                # HMAC-SHA512 回退验证
                import hmac as hmac_mod
                expected_mac = hmac_mod.new(verify_key, original_msg.serialize(), hashlib.sha512).digest()
                return hmac.compare_digest(signature, expected_mac)
            else:
                logger.warning(f"未知的签名标志位: 0x{flag:02x}")
                return False
        except Exception as e:
            logger.debug(f"签名验证失败: {e}")
            return False
