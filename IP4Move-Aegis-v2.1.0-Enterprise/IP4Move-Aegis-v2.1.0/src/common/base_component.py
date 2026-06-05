"""
基础组件模块

提供具有标准生命周期管理的基类:
- initialize/shutdown 模式
- enabled/config 配置
- get_stats 统计接口
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Optional

logger = logging.getLogger(__name__)


class BaseComponent(ABC):
    """
    组件基类

    封装所有组件共享的 initialize/shutdown 生命周期、
    enabled 状态管理和 get_stats 统计接口。

    子类只需提供 component_name 属性和覆盖 _do_initialize/_do_shutdown
    来添加自定义逻辑。
    """

    def __init__(self, config: Optional[dict] = None):
        self.config = config or {}
        self.enabled = self.config.get("enabled", True)
        self._initialized = False

    @property
    @abstractmethod
    def component_name(self) -> str:
        """组件名称，用于日志输出"""
        ...

    async def initialize(self) -> None:
        """初始化组件"""
        if self._initialized:
            return
        logger.info(f"初始化{self.component_name}...")
        await self._do_initialize()
        self._initialized = True
        logger.info(f"{self.component_name}初始化完成")

    async def shutdown(self) -> None:
        """关闭组件"""
        await self._do_shutdown()
        self._initialized = False
        logger.info(f"{self.component_name}已关闭")

    async def _do_initialize(self) -> None:
        """子类可覆盖以添加初始化逻辑"""
        pass

    async def _do_shutdown(self) -> None:
        """子类可覆盖以添加关闭逻辑"""
        pass

    @abstractmethod
    def get_stats(self) -> dict[str, Any]:
        """获取组件统计信息"""
        ...
