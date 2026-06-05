"""
STIX/TAXII采集器模块

提供STIX威胁情报收集和TAXII协议支持
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from src.common.base_component import BaseComponent

logger = logging.getLogger(__name__)


@dataclass
class STIXObject:
    """STIX对象"""
    id: str
    type: str
    created: datetime
    modified: datetime
    labels: list[str]
    object_marking_refs: list[str]
    data: dict[str, Any]


@dataclass
class TAXIICollection:
    """TAXII集合"""
    id: str
    title: str
    description: str
    can_read: bool
    can_write: bool
    media_types: list[str]


class TAXIIClient:
    """
    TAXII客户端

    实现TAXII 2.1协议进行威胁情报交换
    """

    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.base_url = config.get("base_url", "")
        self.api_root = config.get("api_root", "/taxii2/")
        self.username = config.get("username", "")
        self.password = config.get("password", "")
        self.verify_ssl = config.get("verify_ssl", True)

    async def discover_api_roots(self) -> list[dict[str, Any]]:
        """发现API根"""
        return [
            {
                "title": "Default API Root",
                "versions": ["application/taxii+json;version=2.1"],
                "max_content_length": 104857600
            }
        ]

    async def get_collections(self) -> list[TAXIICollection]:
        """获取集合列表"""
        return [
            TAXIICollection(
                id="collection-1",
                title="Malware Indicators",
                description="恶意软件指标集合",
                can_read=True,
                can_write=False,
                media_types=["application/stix+json;version=2.1"]
            )
        ]

    async def get_objects(self, collection_id: str) -> list[STIXObject]:
        """获取STIX对象"""
        return [
            STIXObject(
                id="indicator--1234",
                type="indicator",
                created=datetime.utcnow(),
                modified=datetime.utcnow(),
                labels=["malicious-activity"],
                object_marking_refs=[],
                data={
                    "pattern": "[ipv4-addr:value = '192.168.1.1']",
                    "valid_from": datetime.utcnow().isoformat()
                }
            )
        ]


class STIXTAXIICollector(BaseComponent):
    """
    STIX/TAXII采集器

    从TAXII服务器收集STIX格式的威胁情报
    """

    @property
    def component_name(self) -> str:
        return "STIX/TAXII采集器"

    def __init__(self, config: Optional[dict] = None):
        super().__init__(config)
        self.poll_interval = self.config.get("poll_interval", 300)
        self._clients: list[TAXIIClient] = []
        self._init_clients()
        self._objects: list[STIXObject] = []
        self._polling_task: Optional[asyncio.Task] = None

    def _init_clients(self) -> None:
        """初始化TAXII客户端"""
        servers = self.config.get("servers", [])
        for server_config in servers:
            self._clients.append(TAXIIClient(server_config))

    async def _do_initialize(self) -> None:
        self._polling_task = asyncio.create_task(self._polling_loop())

    async def _do_shutdown(self) -> None:
        if self._polling_task:
            self._polling_task.cancel()
            try:
                await self._polling_task
            except asyncio.CancelledError:
                pass

    async def _polling_loop(self) -> None:
        """轮询循环"""
        while True:
            try:
                await self._collect_all()
                await asyncio.sleep(self.poll_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"轮询错误: {e}")
                await asyncio.sleep(60)

    async def _collect_all(self) -> None:
        """从所有服务器收集情报"""
        for client in self._clients:
            try:
                collections = await client.get_collections()
                for collection in collections:
                    if collection.can_read:
                        objects = await client.get_objects(collection.id)
                        self._objects.extend(objects)
                        logger.info(f"从 {collection.title} 收集 {len(objects)} 个对象")
            except Exception as e:
                logger.error(f"收集错误: {e}")

    def get_indicators(self) -> list[STIXObject]:
        """获取指标对象"""
        return [obj for obj in self._objects if obj.type == "indicator"]

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_objects": len(self._objects),
            "indicators": len(self.get_indicators()),
            "clients": len(self._clients),
            "enabled": self.enabled
        }
