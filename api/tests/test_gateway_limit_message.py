"""The gateway must show a small dollar limit, not round it to $0.00."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.app.db.base import Base
from api.app.models.api_key import APIKey
from api.app.services.gateway_service import GatewayService, format_usd_limit, reset_gateway_state


def setup_function():
    reset_gateway_state()


def _service_with_key(max_cost_usd: float, max_cost_monthly: float):
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    db = sessionmaker(autocommit=False, autoflush=False, bind=engine)()
    api_key = APIKey(
        name="small-limits",
        key_hash="b" * 64,
        key_prefix="sk_sp_test...",
        max_cost_usd=max_cost_usd,
        max_cost_monthly=max_cost_monthly,
        max_requests_per_min=60,
        created_at=datetime.now(timezone.utc),
    )
    db.add(api_key)
    db.commit()
    db.refresh(api_key)
    return GatewayService(db), api_key


@pytest.mark.parametrize(
    "limit, expected",
    [
        (100.0, "$100.00"),
        (1.0, "$1.00"),
        (0.5, "$0.5000"),
        (0.001, "$0.0010"),
        (0.00005, "$0.000050"),
        (1e-9, "$1.0e-09"),
        (0.0, "$0.00"),
    ],
)
def test_format_usd_limit(limit, expected):
    assert format_usd_limit(limit) == expected


def test_small_session_limit_is_shown():
    svc, api_key = _service_with_key(max_cost_usd=0.001, max_cost_monthly=100.0)
    session = svc.resolve_session(api_key, "s1")
    svc.log_request(api_key, session, "gpt-4o-mini", 100, 50, 0.0012, 50.0)

    allowed, reason, _ = svc.check_cost_limit(api_key, session)

    assert allowed is False
    assert reason == "Session cost limit exceeded: $0.0012 >= $0.0010"


def test_small_monthly_limit_is_shown():
    svc, api_key = _service_with_key(max_cost_usd=10.0, max_cost_monthly=0.0005)
    session = svc.resolve_session(api_key, "s1")
    svc.log_request(api_key, session, "gpt-4o-mini", 100, 50, 0.0006, 50.0)

    allowed, reason, _ = svc.check_cost_limit(api_key, session)

    assert allowed is False
    assert reason == "Monthly budget exceeded: $0.0006 >= $0.0005"


def test_large_session_limit_message_is_unchanged():
    svc, api_key = _service_with_key(max_cost_usd=5.0, max_cost_monthly=100.0)
    session = svc.resolve_session(api_key, "s1")
    svc.log_request(api_key, session, "gpt-4o", 100, 50, 5.25, 50.0)

    allowed, reason, _ = svc.check_cost_limit(api_key, session)

    assert allowed is False
    assert reason == "Session cost limit exceeded: $5.2500 >= $5.00"
