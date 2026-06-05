"""
属性存储模块

存储用户、设备和环境属性
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

from src.common.base_component import BaseComponent

logger = logging.getLogger(__name__)


@dataclass
class UserAttributes:
    """用户属性"""
    user_id: str
    roles: list[str] = field(default_factory=list)
    department: str = ""
    clearance_level: int = 0
    attributes: dict[str, Any] = field(default_factory=dict)


@dataclass
class DeviceAttributes:
    """设备属性"""
    device_id: str
    device_type: str = ""
    os_version: str = ""
    security_patch_level: str = ""
    is_compliant: bool = False
    attributes: dict[str, Any] = field(default_factory=dict)


class AttributeStore(BaseComponent):
    """属性存储"""

    @property
    def component_name(self) -> str:
        return "属性存储"

    def __init__(self, config: Optional[dict] = None):
        super().__init__(config)
        self._users: dict[str, UserAttributes] = {}
        self._devices: dict[str, DeviceAttributes] = {}

    def set_user_attributes(self, attrs: UserAttributes) -> None:
        """设置用户属性"""
        self._users[attrs.user_id] = attrs

    def get_user_attributes(self, user_id: str) -> Optional[UserAttributes]:
        """获取用户属性"""
        return self._users.get(user_id)

    def set_device_attributes(self, attrs: DeviceAttributes) -> None:
        """设置设备属性"""
        self._devices[attrs.device_id] = attrs

    def get_device_attributes(self, device_id: str) -> Optional[DeviceAttributes]:
        """获取设备属性"""
        return self._devices.get(device_id)

    def get_stats(self) -> dict[str, Any]:
        return {
            "users": len(self._users),
            "devices": len(self._devices)
        }
