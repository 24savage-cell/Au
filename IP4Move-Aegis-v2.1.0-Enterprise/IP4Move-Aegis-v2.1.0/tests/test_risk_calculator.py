"""Tests for src/ztna/policy/risk_calculator.py"""

import pytest

from src.ztna.policy.risk_calculator import RiskCalculator, RiskFactors, RiskScore


class TestRiskFactors:
    def test_defaults(self):
        f = RiskFactors()
        assert f.authentication_risk == 0.0
        assert f.device_risk == 0.0
        assert f.behavior_risk == 0.0
        assert f.location_risk == 0.0
        assert f.time_risk == 0.0
        assert f.threat_intel_risk == 0.0


class TestRiskCalculator:
    def test_default_config(self):
        calc = RiskCalculator()
        assert calc.enabled is True
        assert calc.thresholds == {"low": 30, "medium": 60, "high": 80}

    def test_custom_thresholds(self):
        calc = RiskCalculator(config={"thresholds": {"low": 20, "medium": 50, "high": 70}})
        assert calc.thresholds["low"] == 20

    def test_calculate_all_zero_is_low(self):
        calc = RiskCalculator()
        score = calc.calculate(RiskFactors())
        assert score.score == 0.0
        assert score.level == "low"

    def test_calculate_all_max_is_critical(self):
        calc = RiskCalculator()
        factors = RiskFactors(
            authentication_risk=1.0,
            device_risk=1.0,
            behavior_risk=1.0,
            location_risk=1.0,
            time_risk=1.0,
            threat_intel_risk=1.0,
        )
        score = calc.calculate(factors)
        assert score.score == 100.0
        assert score.level == "critical"

    def test_calculate_medium_range(self):
        calc = RiskCalculator()
        factors = RiskFactors(
            authentication_risk=0.5,
            device_risk=0.5,
            behavior_risk=0.5,
            location_risk=0.5,
            time_risk=0.5,
            threat_intel_risk=0.5,
        )
        score = calc.calculate(factors)
        assert score.score == 50.0
        assert score.level == "medium"

    def test_calculate_high_range(self):
        calc = RiskCalculator()
        factors = RiskFactors(
            authentication_risk=0.8,
            device_risk=0.7,
            behavior_risk=0.7,
            location_risk=0.7,
            time_risk=0.7,
            threat_intel_risk=0.7,
        )
        score = calc.calculate(factors)
        assert score.level == "high"

    def test_weighted_calculation(self):
        calc = RiskCalculator()
        # Only authentication_risk set, weight = 0.25
        factors = RiskFactors(authentication_risk=1.0)
        score = calc.calculate(factors)
        assert score.score == pytest.approx(25.0)

    def test_score_to_dict(self):
        calc = RiskCalculator()
        score = calc.calculate(RiskFactors())
        d = score.to_dict()
        assert "score" in d
        assert "level" in d
        assert "factors" in d
        assert "timestamp" in d
        assert d["factors"]["authentication_risk"] == 0.0

    def test_get_stats(self):
        calc = RiskCalculator()
        stats = calc.get_stats()
        assert stats["enabled"] is True
        assert "thresholds" in stats

    async def test_initialize_idempotent(self):
        calc = RiskCalculator()
        await calc.initialize()
        assert calc._initialized is True
        await calc.initialize()  # second call is no-op
        assert calc._initialized is True

    async def test_shutdown(self):
        calc = RiskCalculator()
        await calc.initialize()
        await calc.shutdown()
        assert calc._initialized is False
