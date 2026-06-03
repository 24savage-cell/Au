"""
IP.4/Move-Aegis 健康检查

提供企业级健康检查端点:
- 存活探针 (Liveness): 进程是否存活
- 就绪探针 (Readiness): 是否可以接受流量
- 启动探针 (Startup): 是否完成初始化
"""

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class HealthStatus(str, Enum):
    """健康状态"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class ComponentHealth:
    """组件健康状态"""
    name: str
    status: HealthStatus
    message: str = ""
    response_time_ms: float = 0.0
    last_checked: float = field(default_factory=time.time)
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HealthReport:
    """健康报告"""
    status: HealthStatus
    version: str
    uptime_seconds: float
    components: List[ComponentHealth] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "version": self.version,
            "uptime_seconds": round(self.uptime_seconds, 2),
            "timestamp": self.timestamp,
            "components": [
                {
                    "name": c.name,
                    "status": c.status.value,
                    "message": c.message,
                    "response_time_ms": round(c.response_time_ms, 2),
                    "last_checked": c.last_checked,
                    "details": c.details,
                }
                for c in self.components
            ],
        }


class HealthChecker:
    """
    企业级健康检查器

    Usage:
        checker = HealthChecker()
        checker.register("database", check_db_connection)
        checker.register("redis", check_redis)
        report = await checker.run_checks()
    """

    def __init__(self, version: str = "1.0.0") -> None:
        self._version = version
        self._start_time = time.time()
        self._checks: Dict[str, Callable] = {}
        self._component_history: Dict[str, ComponentHealth] = {}

    def register(self, name: str, check_func: Callable) -> None:
        """
        注册健康检查

        Args:
            name: 组件名称
            check_func: 异步检查函数，返回 ComponentHealth
        """
        self._checks[name] = check_func

    async def run_checks(self) -> HealthReport:
        """运行所有健康检查"""
        components: List[ComponentHealth] = []
        overall_status = HealthStatus.HEALTHY

        for name, check_func in self._checks.items():
            try:
                start = time.perf_counter()
                if asyncio.iscoroutinefunction(check_func):
                    result = await check_func()
                else:
                    result = check_func()
                result.response_time_ms = (time.perf_counter() - start) * 1000
                result.last_checked = time.time()
                components.append(result)
                self._component_history[name] = result

                if result.status == HealthStatus.UNHEALTHY:
                    overall_status = HealthStatus.UNHEALTHY
                elif result.status == HealthStatus.DEGRADED and overall_status == HealthStatus.HEALTHY:
                    overall_status = HealthStatus.DEGRADED

            except Exception as e:
                components.append(ComponentHealth(
                    name=name,
                    status=HealthStatus.UNHEALTHY,
                    message=f"Check failed: {str(e)}",
                ))
                overall_status = HealthStatus.UNHEALTHY

        return HealthReport(
            status=overall_status,
            version=self._version,
            uptime_seconds=time.time() - self._start_time,
            components=components,
        )

    def liveness(self) -> Dict[str, str]:
        """存活探针: 进程是否存活"""
        return {"status": "alive"}

    def readiness(self) -> Dict[str, Any]:
        """就绪探针: 是否可以接受流量 (增强版)"""
        unhealthy = sum(
            1 for c in self._component_history.values()
            if c.status == HealthStatus.UNHEALTHY
        )
        degraded = sum(
            1 for c in self._component_history.values()
            if c.status == HealthStatus.DEGRADED
        )
        
        # 计算整体健康度
        total = len(self._component_history)
        health_score = 1.0
        if total > 0:
            health_score = (total - unhealthy - degraded * 0.5) / total
        
        status = "ready"
        if unhealthy > 0:
            status = "not_ready"
        elif degraded > 0:
            status = "degraded"
        
        return {
            "status": status,
            "health_score": round(health_score, 2),
            "unhealthy_components": unhealthy,
            "degraded_components": degraded,
            "total_components": total,
            "uptime_seconds": round(time.time() - self._start_time, 2),
        }
