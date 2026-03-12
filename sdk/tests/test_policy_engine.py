"""
Tests for the PolicyEngine — allow/deny lists, rate limiting, and approval workflow.
"""
import time
import pytest
from steerplane.policy_engine import PolicyEngine, RateLimitSpec
from steerplane.exceptions import PolicyViolationError


# ===========================================================================
# Allow / Deny list tests
# ===========================================================================
class TestAllowDenyLists:
    def test_allow_exact_match(self):
        engine = PolicyEngine(allowed_actions=["file.read"])
        engine.check("file.read")  # should not raise

    def test_allow_glob_match(self):
        engine = PolicyEngine(allowed_actions=["file.*"])
        engine.check("file.read")
        engine.check("file.write")

    def test_deny_exact_blocks(self):
        engine = PolicyEngine(denied_actions=["system.shutdown"])
        with pytest.raises(PolicyViolationError):
            engine.check("system.shutdown")

    def test_deny_glob_blocks(self):
        engine = PolicyEngine(denied_actions=["admin.*"])
        with pytest.raises(PolicyViolationError):
            engine.check("admin.delete_user")

    def test_deny_overrides_allow(self):
        """When an action matches both allow and deny, deny wins."""
        engine = PolicyEngine(
            allowed_actions=["file.*"],
            denied_actions=["file.delete"],
        )
        engine.check("file.read")  # allowed
        with pytest.raises(PolicyViolationError):
            engine.check("file.delete")

    def test_no_rules_allows_everything(self):
        engine = PolicyEngine()
        engine.check("anything.at.all")  # should not raise

    def test_allow_without_match_blocks(self):
        """If allow rules exist but action doesn't match any, block it."""
        engine = PolicyEngine(allowed_actions=["file.read"])
        with pytest.raises(PolicyViolationError):
            engine.check("network.request")


# ===========================================================================
# Rate limiting tests
# ===========================================================================
class TestRateLimiting:
    def test_under_limit_ok(self):
        engine = PolicyEngine(
            rate_limits=[RateLimitSpec(pattern="api.call", max_count=3, window_seconds=60)]
        )
        for _ in range(3):
            engine.check("api.call")

    def test_over_limit_raises(self):
        engine = PolicyEngine(
            rate_limits=[RateLimitSpec(pattern="api.call", max_count=2, window_seconds=60)]
        )
        engine.check("api.call")
        engine.check("api.call")
        with pytest.raises(PolicyViolationError, match="Rate limit"):
            engine.check("api.call")

    def test_window_expires(self):
        engine = PolicyEngine(
            rate_limits=[RateLimitSpec(pattern="api.call", max_count=1, window_seconds=1)]
        )
        engine.check("api.call")
        time.sleep(1.1)
        engine.check("api.call")  # window expired, should succeed

    def test_rate_limit_only_affects_matched_actions(self):
        engine = PolicyEngine(
            rate_limits=[RateLimitSpec(pattern="api.call", max_count=1, window_seconds=60)]
        )
        engine.check("api.call")
        engine.check("other.action")  # different action, not rate limited

    def test_glob_rate_limit(self):
        engine = PolicyEngine(
            rate_limits=[RateLimitSpec(pattern="api.*", max_count=2, window_seconds=60)]
        )
        engine.check("api.call")
        engine.check("api.search")
        with pytest.raises(PolicyViolationError, match="Rate limit"):
            engine.check("api.delete")

    def test_rate_limit_from_dict(self):
        """Rate limits can also be passed as plain dicts."""
        engine = PolicyEngine(
            rate_limits=[{"pattern": "x", "max_count": 1, "window_seconds": 60}]
        )
        engine.check("x")
        with pytest.raises(PolicyViolationError, match="Rate limit"):
            engine.check("x")


# ===========================================================================
# Approval / require_approval tests
# ===========================================================================
class TestApproval:
    def test_require_approval_no_callback_raises(self):
        engine = PolicyEngine(
            require_approval=["deploy.*"],
        )
        with pytest.raises(PolicyViolationError, match="requires approval"):
            engine.check("deploy.production")

    def test_require_approval_callback_approves(self):
        engine = PolicyEngine(
            require_approval=["deploy.*"],
            approval_callback=lambda action, meta: True,
        )
        engine.check("deploy.production")  # callback returns True

    def test_require_approval_callback_denies(self):
        engine = PolicyEngine(
            require_approval=["deploy.*"],
            approval_callback=lambda action, meta: False,
        )
        with pytest.raises(PolicyViolationError, match="denied"):
            engine.check("deploy.production")

    def test_require_approval_does_not_affect_other_actions(self):
        engine = PolicyEngine(require_approval=["deploy.*"])
        engine.check("build.compile")  # should not raise


# ===========================================================================
# Combined rules
# ===========================================================================
class TestCombinedRules:
    def test_allow_plus_rate_limit(self):
        engine = PolicyEngine(
            allowed_actions=["api.*"],
            rate_limits=[RateLimitSpec(pattern="api.expensive", max_count=1, window_seconds=60)],
        )
        engine.check("api.cheap")
        engine.check("api.expensive")
        engine.check("api.cheap")  # still ok, not rate-limited
        with pytest.raises(PolicyViolationError, match="Rate limit"):
            engine.check("api.expensive")  # second call exceeds limit

    def test_deny_plus_rate_limit_deny_wins(self):
        engine = PolicyEngine(
            denied_actions=["danger"],
            rate_limits=[RateLimitSpec(pattern="danger", max_count=100, window_seconds=60)],
        )
        with pytest.raises(PolicyViolationError):
            engine.check("danger")


# ===========================================================================
# has_rules property
# ===========================================================================
class TestHasRules:
    def test_empty_engine_has_no_rules(self):
        assert not PolicyEngine().has_rules

    def test_engine_with_allow_has_rules(self):
        assert PolicyEngine(allowed_actions=["x"]).has_rules

    def test_engine_with_deny_has_rules(self):
        assert PolicyEngine(denied_actions=["x"]).has_rules


# ===========================================================================
# PolicyDecision
# ===========================================================================
class TestPolicyDecision:
    def test_check_returns_decision(self):
        engine = PolicyEngine()
        decision = engine.check("anything")
        assert decision.allowed is True
        assert decision.action == "anything"
