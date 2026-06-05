"""Tests for src/ztna/policy/attribute_store.py"""

import pytest

from src.ztna.policy.attribute_store import (
    AttributeStore,
    DeviceAttributes,
    UserAttributes,
)


class TestUserAttributes:
    def test_defaults(self):
        ua = UserAttributes(user_id="u1")
        assert ua.user_id == "u1"
        assert ua.roles == []
        assert ua.department == ""
        assert ua.clearance_level == 0
        assert ua.attributes == {}

    def test_custom(self):
        ua = UserAttributes(
            user_id="u2",
            roles=["admin", "ops"],
            department="engineering",
            clearance_level=5,
            attributes={"location": "US"},
        )
        assert ua.roles == ["admin", "ops"]
        assert ua.clearance_level == 5


class TestDeviceAttributes:
    def test_defaults(self):
        da = DeviceAttributes(device_id="d1")
        assert da.device_id == "d1"
        assert da.is_compliant is False

    def test_compliant_device(self):
        da = DeviceAttributes(
            device_id="d2",
            device_type="laptop",
            os_version="14.0",
            is_compliant=True,
        )
        assert da.is_compliant is True
        assert da.device_type == "laptop"


class TestAttributeStore:
    def test_set_and_get_user(self):
        store = AttributeStore()
        ua = UserAttributes(user_id="u1", roles=["admin"])
        store.set_user_attributes(ua)
        result = store.get_user_attributes("u1")
        assert result is not None
        assert result.roles == ["admin"]

    def test_get_nonexistent_user(self):
        store = AttributeStore()
        assert store.get_user_attributes("missing") is None

    def test_set_and_get_device(self):
        store = AttributeStore()
        da = DeviceAttributes(device_id="d1", is_compliant=True)
        store.set_device_attributes(da)
        result = store.get_device_attributes("d1")
        assert result is not None
        assert result.is_compliant is True

    def test_get_nonexistent_device(self):
        store = AttributeStore()
        assert store.get_device_attributes("missing") is None

    def test_overwrite_user(self):
        store = AttributeStore()
        store.set_user_attributes(UserAttributes(user_id="u1", roles=["user"]))
        store.set_user_attributes(UserAttributes(user_id="u1", roles=["admin"]))
        result = store.get_user_attributes("u1")
        assert result.roles == ["admin"]

    def test_get_stats(self):
        store = AttributeStore()
        store.set_user_attributes(UserAttributes(user_id="u1"))
        store.set_user_attributes(UserAttributes(user_id="u2"))
        store.set_device_attributes(DeviceAttributes(device_id="d1"))
        stats = store.get_stats()
        assert stats["users"] == 2
        assert stats["devices"] == 1

    async def test_initialize_and_shutdown(self):
        store = AttributeStore()
        await store.initialize()
        assert store._initialized is True
        await store.shutdown()
        assert store._initialized is False
