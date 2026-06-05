"""Tests for src/tunnel/traffic_disguise.py"""

import struct

import pytest

from src.tunnel.traffic_disguise import DisguiseProtocol, TrafficDisguise


class TestDisguiseProtocol:
    def test_values(self):
        assert DisguiseProtocol.DOH.value == "doh"
        assert DisguiseProtocol.QUIC.value == "quic"
        assert DisguiseProtocol.TLS.value == "tls"
        assert DisguiseProtocol.HTTP.value == "http"


class TestTrafficDisguiseTLS:
    def setup_method(self):
        self.disguiser = TrafficDisguise(protocol=DisguiseProtocol.TLS)

    def test_protocol_property(self):
        assert self.disguiser.protocol == DisguiseProtocol.TLS

    def test_round_trip(self):
        original = b"Hello, TLS tunnel!"
        disguised = self.disguiser.disguise(original)
        extracted = self.disguiser.undress(disguised)
        assert extracted == original

    def test_disguise_has_tls_header(self):
        data = b"test"
        disguised = self.disguiser.disguise(data)
        content_type = disguised[0]
        assert content_type in (0x16, 0x17)  # Handshake or Application Data
        version = disguised[1:3]
        assert version == b"\x03\x03"  # TLS 1.2 compat
        length = struct.unpack("!H", disguised[3:5])[0]
        assert length == len(data)

    def test_undress_too_short(self):
        assert self.disguiser.undress(b"\x17\x03\x03") is None

    def test_undress_truncated_payload(self):
        disguised = b"\x17\x03\x03\x00\x10" + b"short"
        assert self.disguiser.undress(disguised) is None

    def test_empty_payload(self):
        disguised = self.disguiser.disguise(b"")
        extracted = self.disguiser.undress(disguised)
        assert extracted == b""

    def test_large_payload(self):
        data = b"X" * 10000
        disguised = self.disguiser.disguise(data)
        extracted = self.disguiser.undress(disguised)
        assert extracted == data


class TestTrafficDisguiseDoH:
    def setup_method(self):
        self.disguiser = TrafficDisguise(protocol=DisguiseProtocol.DOH)

    def test_round_trip(self):
        original = b"DNS query payload"
        disguised = self.disguiser.disguise(original)
        extracted = self.disguiser.undress(disguised)
        assert extracted == original

    def test_disguise_looks_like_http(self):
        disguised = self.disguiser.disguise(b"data")
        text = disguised.decode("utf-8")
        assert "dns=" in text
        assert "HTTP" in text
        assert "application/dns-message" in text

    def test_undress_bad_data_returns_none(self):
        assert self.disguiser.undress(b"not an HTTP request") is None


class TestTrafficDisguiseHTTP:
    def setup_method(self):
        self.disguiser = TrafficDisguise(protocol=DisguiseProtocol.HTTP)

    def test_round_trip(self):
        original = b"HTTP tunnel payload"
        disguised = self.disguiser.disguise(original)
        extracted = self.disguiser.undress(disguised)
        assert extracted == original

    def test_disguise_has_http_structure(self):
        disguised = self.disguiser.disguise(b"data")
        text = disguised.decode("utf-8")
        assert "POST" in text
        assert "HTTP/1.1" in text
        assert "Content-Length" in text
        assert "\r\n\r\n" in text

    def test_undress_bad_data_returns_none(self):
        assert self.disguiser.undress(b"no-double-crlf") is None


class TestTrafficDisguiseQUIC:
    def setup_method(self):
        self.disguiser = TrafficDisguise(protocol=DisguiseProtocol.QUIC)

    def test_round_trip(self):
        original = b"QUIC tunnel data"
        disguised = self.disguiser.disguise(original)
        extracted = self.disguiser.undress(disguised)
        assert extracted == original

    def test_disguise_starts_with_long_header(self):
        disguised = self.disguiser.disguise(b"test")
        assert disguised[0] == 0xC3  # Long Header, Initial

    def test_undress_too_short(self):
        assert self.disguiser.undress(b"\xC3\x00") is None


class TestPaddingAndNoise:
    def setup_method(self):
        self.disguiser = TrafficDisguise()

    def test_generate_padding_size_range(self):
        for _ in range(20):
            pad = self.disguiser.generate_padding(min_size=10, max_size=50)
            assert 10 <= len(pad) <= 50

    def test_inject_noise_empty_data(self):
        result = self.disguiser.inject_adversarial_noise(b"", noise_level=0.5)
        assert result == b""

    def test_inject_noise_zero_level(self):
        data = b"unchanged"
        result = self.disguiser.inject_adversarial_noise(data, noise_level=0.0)
        assert result == data

    def test_inject_noise_modifies_data(self):
        data = b"\x00" * 200
        result = self.disguiser.inject_adversarial_noise(data, noise_level=0.5)
        assert len(result) == len(data)
        assert result != data
