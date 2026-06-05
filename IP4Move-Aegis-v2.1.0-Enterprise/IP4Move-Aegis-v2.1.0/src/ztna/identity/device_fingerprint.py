"""
设备指纹模块

提供硬件、软件和行为特征的设备识别功能
"""

import asyncio
import hashlib
import json
import logging
import platform
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class HardwareFeatures:
    """硬件特征"""
    cpu_info: str = ""
    memory_size: int = 0
    disk_serial: str = ""
    mac_address: str = ""
    bios_version: str = ""
    motherboard_serial: str = ""
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "cpu_info": self.cpu_info,
            "memory_size": self.memory_size,
            "disk_serial": self.disk_serial,
            "mac_address": self.mac_address,
            "bios_version": self.bios_version,
            "motherboard_serial": self.motherboard_serial
        }


@dataclass
class SoftwareFeatures:
    """软件特征"""
    os_name: str = ""
    os_version: str = ""
    browser_name: str = ""
    browser_version: str = ""
    installed_fonts: list[str] = field(default_factory=list)
    timezone: str = ""
    language: str = ""
    screen_resolution: str = ""
    color_depth: int = 0
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "os_name": self.os_name,
            "os_version": self.os_version,
            "browser_name": self.browser_name,
            "browser_version": self.browser_version,
            "installed_fonts": self.installed_fonts,
            "timezone": self.timezone,
            "language": self.language,
            "screen_resolution": self.screen_resolution,
            "color_depth": self.color_depth
        }


@dataclass
class BehaviorFeatures:
    """行为特征"""
    typing_speed: float = 0.0
    mouse_movement_pattern: str = ""
    scroll_behavior: str = ""
    touch_patterns: list[float] = field(default_factory=list)
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "typing_speed": self.typing_speed,
            "mouse_movement_pattern": self.mouse_movement_pattern,
            "scroll_behavior": self.scroll_behavior,
            "touch_patterns": self.touch_patterns
        }


@dataclass
class DeviceProfile:
    """
    设备档案
    
    包含设备的完整指纹信息
    
    Attributes:
        device_id: 设备唯一标识
        fingerprint_hash: 指纹哈希值
        hardware: 硬件特征
        software: 软件特征
        behavior: 行为特征
        trust_score: 信任分数
        first_seen: 首次出现时间
        last_seen: 最后出现时间
        seen_count: 出现次数
    """
    device_id: str
    fingerprint_hash: str
    hardware: HardwareFeatures = field(default_factory=HardwareFeatures)
    software: SoftwareFeatures = field(default_factory=SoftwareFeatures)
    behavior: BehaviorFeatures = field(default_factory=BehaviorFeatures)
    trust_score: float = 0.5
    first_seen: datetime = field(default_factory=datetime.utcnow)
    last_seen: datetime = field(default_factory=datetime.utcnow)
    seen_count: int = 1
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "device_id": self.device_id,
            "fingerprint_hash": self.fingerprint_hash,
            "hardware": self.hardware.to_dict(),
            "software": self.software.to_dict(),
            "behavior": self.behavior.to_dict(),
            "trust_score": self.trust_score,
            "first_seen": self.first_seen.isoformat(),
            "last_seen": self.last_seen.isoformat(),
            "seen_count": self.seen_count
        }


class DeviceFingerprint:
    """
    设备指纹管理器
    
    收集、存储和验证设备指纹
    """
    
    def __init__(self, config: Optional[dict] = None):
        """
        初始化设备指纹管理器
        
        Args:
            config: 配置字典
        """
        self.config = config or {}
        self.enabled = self.config.get("enabled", True)
        
        # 设备档案存储
        self._profiles: dict[str, DeviceProfile] = {}
        
        self._initialized = False
        
    async def initialize(self) -> None:
        """初始化设备指纹管理器"""
        if self._initialized:
            return
            
        logger.info("初始化设备指纹管理器...")
        self._initialized = True
        logger.info("设备指纹管理器初始化完成")
        
    async def shutdown(self) -> None:
        """关闭设备指纹管理器"""
        self._initialized = False
        logger.info("设备指纹管理器已关闭")
        
    def collect_fingerprint(self, device_info: dict[str, Any]) -> DeviceProfile:
        """
        收集设备指纹
        
        Args:
            device_info: 设备信息字典
            
        Returns:
            设备档案
        """
        # 提取硬件特征
        hardware = HardwareFeatures(
            cpu_info=device_info.get("cpu", ""),
            memory_size=device_info.get("memory", 0),
            mac_address=device_info.get("mac", ""),
            screen_resolution=device_info.get("resolution", "")
        )
        
        # 提取软件特征
        software = SoftwareFeatures(
            os_name=device_info.get("os", platform.system()),
            os_version=device_info.get("os_version", platform.release()),
            browser_name=device_info.get("browser", ""),
            browser_version=device_info.get("browser_version", ""),
            timezone=device_info.get("timezone", ""),
            language=device_info.get("language", ""),
            screen_resolution=device_info.get("resolution", "")
        )
        
        # 提取行为特征
        behavior = BehaviorFeatures(
            typing_speed=device_info.get("typing_speed", 0.0)
        )
        
        # 计算指纹哈希
        fingerprint_data = {
            "hardware": hardware.to_dict(),
            "software": software.to_dict()
        }
        fingerprint_hash = hashlib.sha256(
            json.dumps(fingerprint_data, sort_keys=True).encode()
        ).hexdigest()
        
        # 生成设备ID
        device_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, fingerprint_hash))
        
        return DeviceProfile(
            device_id=device_id,
            fingerprint_hash=fingerprint_hash,
            hardware=hardware,
            software=software,
            behavior=behavior
        )
        
    async def register_device(self, profile: DeviceProfile) -> DeviceProfile:
        """
        注册设备
        
        Args:
            profile: 设备档案
            
        Returns:
            注册后的档案
        """
        existing = self._profiles.get(profile.device_id)
        
        if existing:
            # 更新现有档案
            existing.last_seen = datetime.utcnow()
            existing.seen_count += 1
            # 逐步提高信任分数
            existing.trust_score = min(1.0, existing.trust_score + 0.05)
            return existing
        else:
            # 新设备
            self._profiles[profile.device_id] = profile
            logger.info(f"新设备注册: {profile.device_id}")
            return profile
            
    async def verify_device(self, device_id: str, fingerprint_hash: str) -> tuple[bool, float]:
        """
        验证设备
        
        Args:
            device_id: 设备ID
            fingerprint_hash: 指纹哈希
            
        Returns:
            (是否匹配, 相似度分数)
        """
        profile = self._profiles.get(device_id)
        if not profile:
            return False, 0.0
            
        # 计算相似度
        if profile.fingerprint_hash == fingerprint_hash:
            return True, 1.0
            
        # 部分匹配
        similarity = self._calculate_similarity(profile.fingerprint_hash, fingerprint_hash)
        return similarity > 0.8, similarity
        
    def _calculate_similarity(self, hash1: str, hash2: str) -> float:
        """
        计算哈希相似度
        
        Args:
            hash1: 哈希1
            hash2: 哈希2
            
        Returns:
            相似度分数
        """
        if len(hash1) != len(hash2):
            return 0.0
            
        matches = sum(1 for a, b in zip(hash1, hash2) if a == b)
        return matches / len(hash1)
        
    def get_device_profile(self, device_id: str) -> Optional[DeviceProfile]:
        """
        获取设备档案
        
        Args:
            device_id: 设备ID
            
        Returns:
            设备档案
        """
        return self._profiles.get(device_id)
        
    def get_stats(self) -> dict[str, Any]:
        """
        获取统计信息
        
        Returns:
            统计信息
        """
        return {
            "registered_devices": len(self._profiles),
            "enabled": self.enabled
        }
