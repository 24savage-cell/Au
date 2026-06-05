"""
行为生物识别模块

提供击键动力学和鼠标行为分析功能
"""

import logging
import statistics
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from src.common.base_component import BaseComponent

logger = logging.getLogger(__name__)


@dataclass
class KeystrokeEvent:
    """击键事件"""
    key: str
    press_time: float
    release_time: float

    @property
    def hold_time(self) -> float:
        """按键保持时间"""
        return self.release_time - self.press_time


@dataclass
class KeystrokeProfile:
    """击键特征档案"""
    user_id: str
    avg_hold_time: float
    std_hold_time: float
    avg_flight_time: float
    std_flight_time: float
    typing_rhythm: list[float]
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "avg_hold_time": self.avg_hold_time,
            "std_hold_time": self.std_hold_time,
            "avg_flight_time": self.avg_flight_time,
            "std_flight_time": self.std_flight_time,
            "created_at": self.created_at.isoformat()
        }


@dataclass
class MouseEvent:
    """鼠标事件"""
    x: int
    y: int
    timestamp: float
    event_type: str  # move, click, scroll


@dataclass
class MouseProfile:
    """鼠标行为档案"""
    user_id: str
    avg_speed: float
    click_pattern: str
    movement_smoothness: float


class BehaviorBiometrics(BaseComponent):
    """
    行为生物识别管理器

    分析用户的行为模式用于身份验证
    """

    @property
    def component_name(self) -> str:
        return "行为生物识别管理器"

    def __init__(self, config: Optional[dict] = None):
        super().__init__(config)
        self.threshold = self.config.get("threshold", 0.8)
        self._keystroke_profiles: dict[str, KeystrokeProfile] = {}
        self._mouse_profiles: dict[str, MouseProfile] = {}

    def create_keystroke_profile(
        self,
        user_id: str,
        events: list[KeystrokeEvent]
    ) -> KeystrokeProfile:
        """
        创建击键特征档案

        Args:
            user_id: 用户ID
            events: 击键事件列表

        Returns:
            击键档案
        """
        if len(events) < 2:
            raise ValueError("需要至少2个击键事件")

        hold_times = [e.hold_time for e in events]
        avg_hold = statistics.mean(hold_times)
        std_hold = statistics.stdev(hold_times) if len(hold_times) > 1 else 0

        flight_times = []
        for i in range(1, len(events)):
            flight = events[i].press_time - events[i-1].release_time
            flight_times.append(flight)

        avg_flight = statistics.mean(flight_times) if flight_times else 0
        std_flight = statistics.stdev(flight_times) if len(flight_times) > 1 else 0

        profile = KeystrokeProfile(
            user_id=user_id,
            avg_hold_time=avg_hold,
            std_hold_time=std_hold,
            avg_flight_time=avg_flight,
            std_flight_time=std_flight,
            typing_rhythm=hold_times[:10]
        )

        self._keystroke_profiles[user_id] = profile
        return profile

    def verify_keystroke(
        self,
        user_id: str,
        events: list[KeystrokeEvent]
    ) -> tuple[bool, float]:
        """
        验证击键行为

        Args:
            user_id: 用户ID
            events: 击键事件列表

        Returns:
            (是否匹配, 相似度分数)
        """
        profile = self._keystroke_profiles.get(user_id)
        if not profile:
            return False, 0.0

        if len(events) < 2:
            return False, 0.0

        hold_times = [e.hold_time for e in events]
        current_avg_hold = statistics.mean(hold_times)

        flight_times = []
        for i in range(1, len(events)):
            flight = events[i].press_time - events[i-1].release_time
            flight_times.append(flight)
        current_avg_flight = statistics.mean(flight_times) if flight_times else 0

        hold_diff = abs(current_avg_hold - profile.avg_hold_time)
        flight_diff = abs(current_avg_flight - profile.avg_flight_time)

        hold_score = max(0, 1 - hold_diff / profile.avg_hold_time) if profile.avg_hold_time > 0 else 0
        flight_score = max(0, 1 - flight_diff / profile.avg_flight_time) if profile.avg_flight_time > 0 else 0

        similarity = (hold_score + flight_score) / 2

        return similarity >= self.threshold, similarity

    def get_stats(self) -> dict[str, Any]:
        return {
            "keystroke_profiles": len(self._keystroke_profiles),
            "mouse_profiles": len(self._mouse_profiles),
            "enabled": self.enabled
        }
