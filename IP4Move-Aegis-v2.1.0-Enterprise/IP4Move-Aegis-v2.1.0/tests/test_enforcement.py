"""Tests for src/ztna/enforcement/pdp.py and pep.py"""

import pytest

from src.ztna.enforcement.pdp import (
    DecisionRequest,
    DecisionResponse,
    DecisionResult,
    PolicyDecisionPoint,
)
from src.ztna.enforcement.pep import (
    EnforcementAction,
    EnforcementDecision,
    PolicyEnforcementPoint,
)


# ---------------------------------------------------------------------------
# PDP
# ---------------------------------------------------------------------------

class TestDecisionResult:
    def test_values(self):
        assert DecisionResult.PERMIT.value == "permit"
        assert DecisionResult.DENY.value == "deny"
        assert DecisionResult.NOT_APPLICABLE.value == "not_applicable"
        assert DecisionResult.INDETERMINATE.value == "indeterminate"


class TestDecisionRequest:
    def test_fields(self):
        req = DecisionRequest(
            subject_id="user-1",
            resource_id="res-1",
            action="read",
            environment={"ip": "10.0.0.1"},
        )
        assert req.subject_id == "user-1"
        assert req.resource_id == "res-1"
        assert req.action == "read"
        assert req.environment["ip"] == "10.0.0.1"


class TestPolicyDecisionPoint:
    async def test_evaluate_returns_permit(self):
        pdp = PolicyDecisionPoint()
        req = DecisionRequest(
            subject_id="user-1",
            resource_id="res-1",
            action="read",
            environment={},
        )
        resp = await pdp.evaluate(req)
        assert isinstance(resp, DecisionResponse)
        assert resp.result == DecisionResult.PERMIT
        assert isinstance(resp.obligations, list)
        assert isinstance(resp.advice, list)

    async def test_initialize_idempotent(self):
        pdp = PolicyDecisionPoint()
        await pdp.initialize()
        assert pdp._initialized is True
        await pdp.initialize()
        assert pdp._initialized is True

    async def test_shutdown(self):
        pdp = PolicyDecisionPoint()
        await pdp.initialize()
        await pdp.shutdown()
        assert pdp._initialized is False

    def test_get_stats(self):
        pdp = PolicyDecisionPoint()
        assert pdp.get_stats() == {"enabled": True}

    def test_disabled(self):
        pdp = PolicyDecisionPoint(config={"enabled": False})
        assert pdp.get_stats() == {"enabled": False}


# ---------------------------------------------------------------------------
# PEP
# ---------------------------------------------------------------------------

class TestEnforcementAction:
    def test_values(self):
        assert EnforcementAction.ALLOW.value == "allow"
        assert EnforcementAction.DENY.value == "deny"
        assert EnforcementAction.REDIRECT.value == "redirect"
        assert EnforcementAction.CHALLENGE.value == "challenge"
        assert EnforcementAction.LOG.value == "log"


class TestPolicyEnforcementPoint:
    async def test_enforce_allow(self):
        pep = PolicyEnforcementPoint()
        decision = EnforcementDecision(
            action=EnforcementAction.ALLOW,
            reason="authorized",
            metadata={},
        )
        result = await pep.enforce(decision)
        assert result is True

    async def test_enforce_deny(self):
        pep = PolicyEnforcementPoint()
        decision = EnforcementDecision(
            action=EnforcementAction.DENY,
            reason="unauthorized",
            metadata={},
        )
        result = await pep.enforce(decision)
        assert result is False

    async def test_enforce_challenge(self):
        pep = PolicyEnforcementPoint()
        decision = EnforcementDecision(
            action=EnforcementAction.CHALLENGE,
            reason="need MFA",
            metadata={},
        )
        result = await pep.enforce(decision)
        assert result is True  # _handle_challenge returns True

    async def test_enforce_log_returns_false(self):
        pep = PolicyEnforcementPoint()
        decision = EnforcementDecision(
            action=EnforcementAction.LOG,
            reason="audit",
            metadata={},
        )
        result = await pep.enforce(decision)
        assert result is False

    async def test_initialize_and_shutdown(self):
        pep = PolicyEnforcementPoint()
        await pep.initialize()
        assert pep._initialized is True
        await pep.shutdown()
        assert pep._initialized is False

    def test_get_stats(self):
        pep = PolicyEnforcementPoint()
        assert pep.get_stats() == {"enabled": True}
