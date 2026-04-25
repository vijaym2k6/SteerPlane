from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.app.db.base import Base
from api.app.models.api_key import APIKey
from api.app.models.run import Run
from api.app.services.approval_service import ApprovalService
from api.app.services.gateway_service import (
    GatewayService,
    _loop_detector,
    _session_tracker,
)


def _make_db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return session_local()


def _make_api_key() -> APIKey:
    return APIKey(
        name="prod-key",
        key_hash="a" * 64,
        key_prefix="sk_sp_test...",
        max_cost_usd=5.0,
        max_cost_monthly=100.0,
        max_requests_per_min=60,
        created_at=datetime.now(timezone.utc),
    )


def setup_function():
    _session_tracker._sessions.clear()
    _session_tracker._default_session_ids.clear()
    _loop_detector._histories.clear()


def test_explicit_session_reuses_same_run_id_and_cost():
    db = _make_db()
    api_key = _make_api_key()
    db.add(api_key)
    db.commit()
    db.refresh(api_key)

    svc = GatewayService(db)
    session = svc.resolve_session(api_key, "ticket-1042")
    svc.log_request(api_key, session, "gpt-4o", 100, 50, 0.25, 120.0)

    same_session = svc.resolve_session(api_key, "ticket-1042")

    assert same_session.session_id == session.session_id
    assert same_session.run_id == session.run_id
    assert svc.get_session_cost(session) == 0.25


def test_monthly_budget_is_calendar_month_scoped():
    db = _make_db()
    api_key = _make_api_key()
    api_key.max_cost_usd = 10.0
    api_key.max_cost_monthly = 0.30
    db.add(api_key)
    db.commit()
    db.refresh(api_key)

    svc = GatewayService(db)
    session = svc.resolve_session(api_key, "billing-bot")
    svc.log_request(api_key, session, "gpt-4o", 100, 50, 0.20, 100.0)
    svc.log_request(api_key, session, "gpt-4o", 100, 50, 0.20, 100.0)

    allowed, reason, _ = svc.check_cost_limit(api_key, session)

    assert allowed is False
    assert "Monthly budget exceeded" in reason


def test_auto_session_rotation_closes_expired_run():
    db = _make_db()
    api_key = _make_api_key()
    db.add(api_key)
    db.commit()
    db.refresh(api_key)

    svc = GatewayService(db)
    first_session = svc.resolve_session(api_key)
    svc.log_request(api_key, first_session, "gpt-4o", 10, 5, 0.01, 50.0)

    tracked_session = _session_tracker._sessions[api_key.key_hash][first_session.session_id]
    tracked_session.last_seen_at -= _session_tracker._idle_timeout_sec + 1

    second_session = svc.resolve_session(api_key)
    expired_run = db.query(Run).filter(Run.id == first_session.run_id).first()

    assert second_session.run_id != first_session.run_id
    assert expired_run is not None
    assert expired_run.status == "completed"


def test_gateway_alert_mode_creates_pending_approval_after_threshold_cross():
    db = _make_db()
    api_key = _make_api_key()
    api_key.max_cost_usd = 10.0
    db.add(api_key)
    db.commit()
    db.refresh(api_key)

    approval_service = ApprovalService(db)
    enforcement = approval_service.get_or_create_api_key_enforcement(api_key.id)
    enforcement.enforcement_mode = "alert"
    enforcement.alert_threshold = 0.8
    enforcement.alert_timeout_sec = 600
    db.commit()

    svc = GatewayService(db)
    session = svc.resolve_session(api_key, "ops-bot")
    svc.log_request(api_key, session, "gpt-4o", 100, 50, 8.2, 120.0)

    approval = svc.maybe_trigger_threshold_alert(api_key, session)

    assert approval is not None
    assert approval.status == "pending"
    assert approval.approval_type == "cost_limit"
    assert approval.scope == "gateway"


def test_gateway_approved_extension_increases_effective_session_limit():
    db = _make_db()
    api_key = _make_api_key()
    api_key.max_cost_usd = 10.0
    db.add(api_key)
    db.commit()
    db.refresh(api_key)

    approval_service = ApprovalService(db)
    enforcement = approval_service.get_or_create_api_key_enforcement(api_key.id)
    enforcement.enforcement_mode = "alert"
    db.commit()

    svc = GatewayService(db)
    session = svc.resolve_session(api_key, "critical-job")
    approval = approval_service.create_approval(
        run_id=session.run_id,
        agent_name="gateway:prod-key",
        approval_type="cost_limit",
        current_value=10.0,
        limit_value=10.0,
        unit="usd",
        message="Need approval",
        timeout_sec=600,
        scope="gateway",
        session_id=session.session_id,
        api_key_id=api_key.id,
    )
    approval_service.approve(approval.id)

    effective_limit = svc.get_session_cost_limit(api_key, session)

    assert effective_limit == 20.0
