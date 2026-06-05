"""Tests for src/ztna/policy/policy_engine.py"""

import pytest

from src.ztna.policy.policy_engine import ABACPolicy, PolicyDecision, PolicyEngine


def _make_policy(
    policy_id="p1",
    name="test",
    effect=PolicyDecision.PERMIT,
    subject=None,
    resource=None,
    action=None,
    environment=None,
    priority=1,
    enabled=True,
):
    return ABACPolicy(
        policy_id=policy_id,
        name=name,
        description="",
        subject_attributes=subject or {},
        resource_attributes=resource or {},
        action_attributes=action or {},
        environment_attributes=environment or {},
        effect=effect,
        priority=priority,
        enabled=enabled,
    )


class TestPolicyDecision:
    def test_values(self):
        assert PolicyDecision.PERMIT.value == "permit"
        assert PolicyDecision.DENY.value == "deny"
        assert PolicyDecision.NOT_APPLICABLE.value == "not_applicable"
        assert PolicyDecision.INDETERMINATE.value == "indeterminate"


class TestPolicyEngine:
    def test_disabled_engine_always_permits(self):
        engine = PolicyEngine(config={"enabled": False})
        result = engine.evaluate({}, {}, {}, {})
        assert result == PolicyDecision.PERMIT

    def test_no_policies_returns_not_applicable(self):
        engine = PolicyEngine()
        result = engine.evaluate({"role": "admin"}, {}, {}, {})
        assert result == PolicyDecision.NOT_APPLICABLE

    def test_matching_permit_policy(self):
        engine = PolicyEngine()
        engine.add_policy(_make_policy(
            subject={"role": "admin"},
            effect=PolicyDecision.PERMIT,
        ))
        result = engine.evaluate({"role": "admin"}, {}, {}, {})
        assert result == PolicyDecision.PERMIT

    def test_matching_deny_policy(self):
        engine = PolicyEngine()
        engine.add_policy(_make_policy(
            subject={"role": "guest"},
            effect=PolicyDecision.DENY,
        ))
        result = engine.evaluate({"role": "guest"}, {}, {}, {})
        assert result == PolicyDecision.DENY

    def test_non_matching_policy_skipped(self):
        engine = PolicyEngine()
        engine.add_policy(_make_policy(
            subject={"role": "admin"},
            effect=PolicyDecision.PERMIT,
        ))
        result = engine.evaluate({"role": "user"}, {}, {}, {})
        assert result == PolicyDecision.NOT_APPLICABLE

    def test_priority_ordering(self):
        engine = PolicyEngine()
        engine.add_policy(_make_policy(
            policy_id="low",
            subject={"role": "admin"},
            effect=PolicyDecision.PERMIT,
            priority=1,
        ))
        engine.add_policy(_make_policy(
            policy_id="high",
            subject={"role": "admin"},
            effect=PolicyDecision.DENY,
            priority=10,
        ))
        # Higher priority evaluated first
        result = engine.evaluate({"role": "admin"}, {}, {}, {})
        assert result == PolicyDecision.DENY

    def test_disabled_policy_skipped(self):
        engine = PolicyEngine()
        engine.add_policy(_make_policy(
            subject={"role": "admin"},
            effect=PolicyDecision.DENY,
            enabled=False,
        ))
        result = engine.evaluate({"role": "admin"}, {}, {}, {})
        assert result == PolicyDecision.NOT_APPLICABLE

    def test_multi_attribute_match(self):
        engine = PolicyEngine()
        engine.add_policy(_make_policy(
            subject={"role": "admin", "dept": "eng"},
            resource={"type": "db"},
            action={"op": "read"},
            effect=PolicyDecision.PERMIT,
        ))
        result = engine.evaluate(
            {"role": "admin", "dept": "eng"},
            {"type": "db"},
            {"op": "read"},
            {},
        )
        assert result == PolicyDecision.PERMIT

    def test_partial_attribute_mismatch(self):
        engine = PolicyEngine()
        engine.add_policy(_make_policy(
            subject={"role": "admin", "dept": "eng"},
            effect=PolicyDecision.PERMIT,
        ))
        result = engine.evaluate({"role": "admin", "dept": "sales"}, {}, {}, {})
        assert result == PolicyDecision.NOT_APPLICABLE

    def test_get_stats(self):
        engine = PolicyEngine()
        engine.add_policy(_make_policy())
        engine.add_policy(_make_policy(policy_id="p2"))
        stats = engine.get_stats()
        assert stats["policies"] == 2
        assert stats["enabled"] is True

    async def test_initialize_and_shutdown(self):
        engine = PolicyEngine()
        await engine.initialize()
        assert engine._initialized is True
        await engine.shutdown()
        assert engine._initialized is False
