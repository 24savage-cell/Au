"""Tests for src/ztna/identity/mfa_manager.py"""

import time

import pytest

from src.ztna.identity.mfa_manager import (
    MFACredential,
    MFAManager,
    MFAMethod,
    MFAProvider,
    TOTPProvider,
    WebAuthnProvider,
)


# ---------------------------------------------------------------------------
# MFAMethod enum
# ---------------------------------------------------------------------------

class TestMFAMethod:
    def test_values(self):
        assert MFAMethod.TOTP.value == "totp"
        assert MFAMethod.WEBAUTHN.value == "webauthn"
        assert MFAMethod.SMS.value == "sms"
        assert MFAMethod.PUSH.value == "push"
        assert MFAMethod.EMAIL.value == "email"
        assert MFAMethod.BACKUP_CODES.value == "backup_codes"


# ---------------------------------------------------------------------------
# TOTPProvider
# ---------------------------------------------------------------------------

class TestTOTPProvider:
    def setup_method(self):
        self.provider = TOTPProvider({"issuer": "TestApp", "digits": 6, "interval": 30})

    async def test_setup_returns_secret_and_uri(self):
        result = await self.provider.setup("user-1")
        assert "secret" in result
        assert "qr_uri" in result
        assert "backup_codes" in result
        assert "otpauth://totp/TestApp:user-1" in result["qr_uri"]
        assert len(result["backup_codes"]) == 10

    async def test_verify_correct_code(self):
        await self.provider.setup("user-1")
        code = self.provider._generate_totp(
            self.provider._credentials["user-1"].secret
        )
        assert await self.provider.verify("user-1", code) is True

    async def test_verify_wrong_code(self):
        await self.provider.setup("user-1")
        assert await self.provider.verify("user-1", "000000") is False

    async def test_verify_unknown_user(self):
        assert await self.provider.verify("no-such-user", "123456") is False

    def test_generate_totp_format(self):
        # Use a known secret
        import base64
        secret = base64.b32encode(b"12345678901234567890").decode()
        code = self.provider._generate_totp(secret)
        assert len(code) == 6
        assert code.isdigit()

    def test_generate_totp_offset(self):
        import base64
        secret = base64.b32encode(b"12345678901234567890").decode()
        code_prev = self.provider._generate_totp(secret, offset=-1)
        code_curr = self.provider._generate_totp(secret, offset=0)
        code_next = self.provider._generate_totp(secret, offset=1)
        # All should be 6-digit strings
        for c in [code_prev, code_curr, code_next]:
            assert len(c) == 6
            assert c.isdigit()

    def test_generate_backup_codes(self):
        codes = self.provider._generate_backup_codes(count=5)
        assert len(codes) == 5
        for code in codes:
            assert len(code) == 8  # token_hex(4) = 8 hex chars

    async def test_verify_updates_last_used(self):
        result = await self.provider.setup("user-1")
        cred = self.provider._credentials["user-1"]
        assert cred.last_used is None
        code = self.provider._generate_totp(cred.secret)
        await self.provider.verify("user-1", code)
        assert cred.last_used is not None


# ---------------------------------------------------------------------------
# WebAuthnProvider
# ---------------------------------------------------------------------------

class TestWebAuthnProvider:
    def setup_method(self):
        self.provider = WebAuthnProvider({"rp_id": "example.com", "rp_name": "Example"})

    async def test_setup_returns_challenge(self):
        result = await self.provider.setup("user-1")
        assert "challenge" in result
        assert result["rp"]["id"] == "example.com"
        assert result["rp"]["name"] == "Example"
        assert result["user"]["id"] == "user-1"

    async def test_verify_returns_true(self):
        assert await self.provider.verify("user-1", "assertion") is True


# ---------------------------------------------------------------------------
# MFAManager
# ---------------------------------------------------------------------------

class TestMFAManager:
    def test_default_config_enables_totp(self):
        mgr = MFAManager()
        assert MFAMethod.TOTP in mgr._providers

    def test_webauthn_disabled_by_default(self):
        mgr = MFAManager()
        assert MFAMethod.WEBAUTHN not in mgr._providers

    def test_webauthn_enabled(self):
        mgr = MFAManager(config={"webauthn": {"enabled": True}})
        assert MFAMethod.WEBAUTHN in mgr._providers

    def test_totp_disabled(self):
        mgr = MFAManager(config={"totp": {"enabled": False}})
        assert MFAMethod.TOTP not in mgr._providers

    async def test_setup_mfa(self):
        mgr = MFAManager()
        result = await mgr.setup_mfa("user-1", MFAMethod.TOTP)
        assert "secret" in result

    async def test_setup_mfa_unsupported_method(self):
        mgr = MFAManager()
        with pytest.raises(ValueError, match="不支持"):
            await mgr.setup_mfa("user-1", MFAMethod.SMS)

    async def test_verify_mfa(self):
        mgr = MFAManager()
        await mgr.setup_mfa("user-1", MFAMethod.TOTP)
        totp_provider = mgr._providers[MFAMethod.TOTP]
        code = totp_provider._generate_totp(
            totp_provider._credentials["user-1"].secret
        )
        result = await mgr.verify_mfa("user-1", MFAMethod.TOTP, code)
        assert result is True

    async def test_verify_mfa_unsupported_returns_false(self):
        mgr = MFAManager()
        result = await mgr.verify_mfa("user-1", MFAMethod.SMS, "123456")
        assert result is False

    async def test_initialize_and_shutdown(self):
        mgr = MFAManager()
        await mgr.initialize()
        assert mgr._initialized is True
        await mgr.shutdown()
        assert mgr._initialized is False

    def test_get_stats(self):
        mgr = MFAManager()
        stats = mgr.get_stats()
        assert stats["enabled"] is True
        assert "enabled_methods" in stats
