"""Tests for src/health.py"""

import asyncio
import time

import pytest

from src.health import (
    ComponentHealth,
    HealthChecker,
    HealthReport,
    HealthStatus,
)


# ---------------------------------------------------------------------------
# HealthStatus enum
# ---------------------------------------------------------------------------

class TestHealthStatus:
    def test_values(self):
        assert HealthStatus.HEALTHY.value == "healthy"
        assert HealthStatus.DEGRADED.value == "degraded"
        assert HealthStatus.UNHEALTHY.value == "unhealthy"
        assert HealthStatus.UNKNOWN.value == "unknown"

    def test_is_str_subclass(self):
        assert isinstance(HealthStatus.HEALTHY, str)


# ---------------------------------------------------------------------------
# ComponentHealth dataclass
# ---------------------------------------------------------------------------

class TestComponentHealth:
    def test_defaults(self):
        ch = ComponentHealth(name="db", status=HealthStatus.HEALTHY)
        assert ch.name == "db"
        assert ch.status == HealthStatus.HEALTHY
        assert ch.message == ""
        assert ch.response_time_ms == 0.0
        assert ch.details == {}
        assert ch.last_checked > 0

    def test_custom_values(self):
        ch = ComponentHealth(
            name="redis",
            status=HealthStatus.DEGRADED,
            message="high latency",
            response_time_ms=150.5,
            details={"latency": 150},
        )
        assert ch.message == "high latency"
        assert ch.response_time_ms == 150.5
        assert ch.details == {"latency": 150}


# ---------------------------------------------------------------------------
# HealthReport dataclass
# ---------------------------------------------------------------------------

class TestHealthReport:
    def test_to_dict_empty_components(self):
        report = HealthReport(
            status=HealthStatus.HEALTHY,
            version="2.1.0",
            uptime_seconds=123.456,
        )
        d = report.to_dict()
        assert d["status"] == "healthy"
        assert d["version"] == "2.1.0"
        assert d["uptime_seconds"] == 123.46
        assert d["components"] == []
        assert "timestamp" in d

    def test_to_dict_with_components(self):
        comp = ComponentHealth(name="db", status=HealthStatus.UNHEALTHY, message="down")
        report = HealthReport(
            status=HealthStatus.UNHEALTHY,
            version="1.0.0",
            uptime_seconds=0,
            components=[comp],
        )
        d = report.to_dict()
        assert len(d["components"]) == 1
        assert d["components"][0]["name"] == "db"
        assert d["components"][0]["status"] == "unhealthy"
        assert d["components"][0]["message"] == "down"


# ---------------------------------------------------------------------------
# HealthChecker
# ---------------------------------------------------------------------------

class TestHealthChecker:
    def test_liveness(self):
        checker = HealthChecker(version="2.1.0")
        assert checker.liveness() == {"status": "alive"}

    def test_readiness_no_history(self):
        checker = HealthChecker()
        result = checker.readiness()
        assert result["status"] == "ready"
        assert result["health_score"] == 1.0
        assert result["total_components"] == 0

    async def test_run_checks_all_healthy(self):
        checker = HealthChecker(version="2.0.0")

        def check_db():
            return ComponentHealth(name="db", status=HealthStatus.HEALTHY, message="ok")

        checker.register("db", check_db)
        report = await checker.run_checks()

        assert report.status == HealthStatus.HEALTHY
        assert report.version == "2.0.0"
        assert len(report.components) == 1
        assert report.components[0].name == "db"
        assert report.components[0].response_time_ms >= 0

    async def test_run_checks_unhealthy_overrides(self):
        checker = HealthChecker()

        def healthy():
            return ComponentHealth(name="a", status=HealthStatus.HEALTHY)

        def unhealthy():
            return ComponentHealth(name="b", status=HealthStatus.UNHEALTHY, message="fail")

        checker.register("a", healthy)
        checker.register("b", unhealthy)

        report = await checker.run_checks()
        assert report.status == HealthStatus.UNHEALTHY

    async def test_run_checks_degraded_when_no_unhealthy(self):
        checker = HealthChecker()

        def healthy():
            return ComponentHealth(name="a", status=HealthStatus.HEALTHY)

        def degraded():
            return ComponentHealth(name="b", status=HealthStatus.DEGRADED)

        checker.register("a", healthy)
        checker.register("b", degraded)

        report = await checker.run_checks()
        assert report.status == HealthStatus.DEGRADED

    async def test_run_checks_exception_becomes_unhealthy(self):
        checker = HealthChecker()

        def boom():
            raise RuntimeError("oops")

        checker.register("boom", boom)
        report = await checker.run_checks()
        assert report.status == HealthStatus.UNHEALTHY
        assert "oops" in report.components[0].message

    async def test_run_checks_async_check(self):
        checker = HealthChecker()

        async def async_check():
            return ComponentHealth(name="async_svc", status=HealthStatus.HEALTHY)

        checker.register("async_svc", async_check)
        report = await checker.run_checks()
        assert report.status == HealthStatus.HEALTHY
        assert report.components[0].name == "async_svc"

    async def test_readiness_after_checks(self):
        checker = HealthChecker()

        def healthy():
            return ComponentHealth(name="a", status=HealthStatus.HEALTHY)

        def degraded():
            return ComponentHealth(name="b", status=HealthStatus.DEGRADED)

        checker.register("a", healthy)
        checker.register("b", degraded)
        await checker.run_checks()

        result = checker.readiness()
        assert result["status"] == "degraded"
        assert result["degraded_components"] == 1
        assert result["unhealthy_components"] == 0
        assert result["total_components"] == 2
        assert 0 < result["health_score"] < 1.0

    async def test_readiness_not_ready_when_unhealthy(self):
        checker = HealthChecker()

        def unhealthy():
            return ComponentHealth(name="x", status=HealthStatus.UNHEALTHY)

        checker.register("x", unhealthy)
        await checker.run_checks()

        result = checker.readiness()
        assert result["status"] == "not_ready"
        assert result["unhealthy_components"] == 1

    def test_uptime_increases(self):
        checker = HealthChecker()
        r1 = checker.readiness()
        time.sleep(0.05)
        r2 = checker.readiness()
        assert r2["uptime_seconds"] > r1["uptime_seconds"]
