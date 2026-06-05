"""Tests for src/network/message.py"""

import asyncio
import hashlib
import hmac
import os
import struct

import pytest

from src.network.message import (
    HMAC_SIZE,
    MAX_PAYLOAD_SIZE,
    Message,
    MessageProtocol,
    MessageType,
)


# ---------------------------------------------------------------------------
# MessageType enum
# ---------------------------------------------------------------------------

class TestMessageType:
    def test_control_messages(self):
        assert MessageType.PING == 0x01
        assert MessageType.PONG == 0x02
        assert MessageType.HELLO == 0x03
        assert MessageType.DISCONNECT == 0x04

    def test_data_messages(self):
        assert MessageType.DATA == 0x10

    def test_invalid_type_raises(self):
        with pytest.raises(ValueError):
            MessageType(0xFF)


# ---------------------------------------------------------------------------
# Message dataclass
# ---------------------------------------------------------------------------

class TestMessage:
    def test_auto_msg_id(self):
        msg = Message(msg_type=MessageType.PING, payload=b"")
        assert len(msg.msg_id) == 32  # os.urandom(16).hex()

    def test_long_msg_id_truncated(self):
        msg = Message(msg_type=MessageType.PING, payload=b"", msg_id="A" * 64)
        assert len(msg.msg_id) == 32

    def test_custom_fields(self):
        msg = Message(
            msg_type=MessageType.DATA,
            payload=b"hello",
            source="node-a",
            destination="node-b",
            ttl=10,
        )
        assert msg.source == "node-a"
        assert msg.destination == "node-b"
        assert msg.ttl == 10
        assert msg.payload == b"hello"

    def test_to_dict(self):
        msg = Message(msg_type=MessageType.PING, payload=b"abc")
        d = msg.to_dict()
        assert d["msg_type"] == "PING"
        assert d["payload_size"] == 3
        assert "timestamp" in d


# ---------------------------------------------------------------------------
# Serialize / Deserialize round-trip
# ---------------------------------------------------------------------------

class TestSerialization:
    def test_round_trip_no_hmac(self):
        original = Message(
            msg_type=MessageType.DATA,
            payload=b"test-payload",
            source="src",
            destination="dst",
            ttl=32,
            msg_id="abcdef1234567890abcdef1234567890",
        )
        data = original.serialize()
        restored = Message.deserialize(data, verify=False)

        assert restored.msg_type == MessageType.DATA
        assert restored.payload == b"test-payload"
        assert restored.source == "src"
        assert restored.destination == "dst"
        assert restored.ttl == 32
        assert restored.msg_id == original.msg_id

    def test_round_trip_with_hmac(self):
        key = os.urandom(32)
        original = Message(
            msg_type=MessageType.PING,
            payload=b"ping-data",
        )
        data = original.serialize(hmac_key=key)
        restored = Message.deserialize(data, hmac_key=key)
        assert restored.msg_type == MessageType.PING
        assert restored.payload == b"ping-data"

    def test_hmac_tamper_detected(self):
        key = os.urandom(32)
        msg = Message(msg_type=MessageType.PING, payload=b"x")
        data = bytearray(msg.serialize(hmac_key=key))
        # Flip a byte in the payload region
        data[50] ^= 0xFF
        with pytest.raises(ValueError, match="HMAC"):
            Message.deserialize(bytes(data), hmac_key=key)

    def test_wrong_hmac_key_rejected(self):
        key1 = os.urandom(32)
        key2 = os.urandom(32)
        msg = Message(msg_type=MessageType.DATA, payload=b"secret")
        data = msg.serialize(hmac_key=key1)
        with pytest.raises(ValueError, match="HMAC"):
            Message.deserialize(data, hmac_key=key2)

    def test_deserialize_too_short(self):
        with pytest.raises(ValueError, match="太短"):
            Message.deserialize(b"short")

    def test_deserialize_invalid_type(self):
        # Build a minimal buffer with an invalid message type byte
        buf = bytearray(113 + HMAC_SIZE)
        buf[0] = 1  # version
        buf[1] = 0xFF  # invalid msg type
        with pytest.raises(ValueError, match="无效"):
            Message.deserialize(bytes(buf))

    def test_empty_payload(self):
        msg = Message(msg_type=MessageType.PING, payload=b"")
        data = msg.serialize()
        restored = Message.deserialize(data, verify=False)
        assert restored.payload == b""

    def test_serialize_without_key_pads_zero_hmac(self):
        msg = Message(msg_type=MessageType.PING, payload=b"a")
        data = msg.serialize()
        assert data[-HMAC_SIZE:] == b"\x00" * HMAC_SIZE


# ---------------------------------------------------------------------------
# MessageProtocol
# ---------------------------------------------------------------------------

class TestMessageProtocol:
    def test_create_ping(self):
        proto = MessageProtocol(node_id="node-1")
        msg = proto.create_ping(destination="node-2")
        assert msg.msg_type == MessageType.PING
        assert msg.source == "node-1"
        assert msg.destination == "node-2"
        assert msg.payload == b""

    def test_create_pong(self):
        proto = MessageProtocol(node_id="node-1")
        ping = proto.create_ping(destination="node-2")
        pong = proto.create_pong(ping)
        assert pong.msg_type == MessageType.PONG
        assert pong.destination == "node-1"
        assert pong.payload == ping.msg_id.encode()

    def test_create_hello(self):
        proto = MessageProtocol(node_id="node-1")
        msg = proto.create_hello({"version": "2.1.0"})
        assert msg.msg_type == MessageType.HELLO
        import json
        assert json.loads(msg.payload) == {"version": "2.1.0"}

    def test_create_data(self):
        proto = MessageProtocol(node_id="node-1")
        msg = proto.create_data(b"raw-bytes", destination="node-2")
        assert msg.msg_type == MessageType.DATA
        assert msg.payload == b"raw-bytes"

    def test_create_onion(self):
        proto = MessageProtocol(node_id="node-1")
        msg = proto.create_onion(b"wrapped", destination="node-2")
        assert msg.msg_type == MessageType.ONION_WRAP
        assert msg.payload == b"wrapped"

    async def test_register_and_handle_sync_handler(self):
        proto = MessageProtocol(node_id="node-1")
        received = []

        def handler(msg):
            received.append(msg)

        proto.register_handler(MessageType.PING, handler)
        ping = proto.create_ping()
        await proto.handle_message(ping)
        assert len(received) == 1
        assert received[0].msg_type == MessageType.PING

    async def test_handler_exception_does_not_propagate(self):
        proto = MessageProtocol(node_id="node-1")

        def bad_handler(msg):
            raise ValueError("boom")

        proto.register_handler(MessageType.PING, bad_handler)
        ping = proto.create_ping()
        # Should not raise
        await proto.handle_message(ping)

    def test_sign_and_verify_hmac_fallback(self):
        proto = MessageProtocol(node_id="node-1")
        key = os.urandom(32)
        msg = proto.create_data(b"secret-data")
        signed = proto.sign_message(msg, key)
        assert signed.payload[0] == 0x01  # HMAC fallback flag
        assert proto.verify_message_signature(signed, key) is True

    def test_verify_wrong_key_fails(self):
        proto = MessageProtocol(node_id="node-1")
        key1 = os.urandom(32)
        key2 = os.urandom(32)
        msg = proto.create_data(b"data")
        signed = proto.sign_message(msg, key1)
        assert proto.verify_message_signature(signed, key2) is False
