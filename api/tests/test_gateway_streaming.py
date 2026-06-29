"""Streaming gateway tests.

Cover token accumulation and mid-stream cost enforcement for both OpenAI and
Anthropic SSE shapes. The Anthropic case is a regression test: its `data:` lines
used to fall into the OpenAI parser, so usage was never read and the mid-stream
cost kill could never fire for Claude.
"""

from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone

import httpx
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.app.db.base import Base
from api.app.models.api_key import APIKey
from api.app.models.step import Step
from api.app.routes.gateway import _handle_streaming
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


def _make_api_key(max_cost_usd: float = 5.0) -> APIKey:
    return APIKey(
        name="prod-key",
        key_hash="b" * 64,
        key_prefix="sk_sp_test...",
        max_cost_usd=max_cost_usd,
        max_cost_monthly=100.0,
        max_requests_per_min=60,
        created_at=datetime.now(timezone.utc),
    )


def setup_function():
    _session_tracker._sessions.clear()
    _session_tracker._default_session_ids.clear()
    _loop_detector._histories.clear()


def _drive_stream(svc, api_key, session, model, provider, sse_text):
    """Run _handle_streaming against a mocked upstream and return the forwarded body."""

    async def run():
        def handler(_request):
            return httpx.Response(200, content=sse_text.encode())

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            resp = await _handle_streaming(
                client=client,
                target_url="https://upstream.test/v1/messages",
                headers={},
                body={},
                svc=svc,
                api_key=api_key,
                session=session,
                model=model,
                start_time=time.time(),
                provider=provider,
            )
            chunks = []
            async for chunk in resp.body_iterator:
                chunks.append(chunk if isinstance(chunk, str) else chunk.decode())
            return "".join(chunks)

    return asyncio.run(run())


def _logged_llm_step(db, run_id) -> Step:
    return (
        db.query(Step)
        .filter(Step.run_id == run_id, Step.action.like("llm:%"))
        .order_by(Step.step_number.desc())
        .first()
    )


def test_openai_streaming_accumulates_usage_and_logs_cost():
    db = _make_db()
    api_key = _make_api_key()
    db.add(api_key)
    db.commit()
    db.refresh(api_key)

    svc = GatewayService(db)
    session = svc.resolve_session(api_key, "stream-openai")

    sse = "\n".join(
        [
            'data: {"choices":[{"delta":{"content":"Hello"}}]}',
            "",
            'data: {"choices":[{"delta":{"content":" world"}}]}',
            "",
            'data: {"choices":[{"delta":{}}],"usage":{"prompt_tokens":10,"completion_tokens":5}}',
            "",
            "data: [DONE]",
            "",
        ]
    )

    body = _drive_stream(svc, api_key, session, "gpt-4o", "openai", sse)

    assert "Hello" in body
    assert "[DONE]" in body

    step = _logged_llm_step(db, session.run_id)
    assert step is not None
    assert step.metadata_json["input_tokens"] == 10
    assert step.metadata_json["output_tokens"] == 5
    assert step.tokens == 15
    assert step.cost_usd > 0
    assert step.status != "terminated"


def test_anthropic_streaming_accumulates_usage_and_logs_cost():
    # Regression for the dead-code branch: Anthropic usage must be read so cost
    # is non-zero and the mid-stream kill is reachable.
    db = _make_db()
    api_key = _make_api_key()
    db.add(api_key)
    db.commit()
    db.refresh(api_key)

    svc = GatewayService(db)
    session = svc.resolve_session(api_key, "stream-anthropic")

    sse = "\n".join(
        [
            "event: message_start",
            'data: {"type":"message_start","message":{"usage":{"input_tokens":20,"output_tokens":1}}}',
            "",
            "event: content_block_delta",
            'data: {"type":"content_block_delta","delta":{"type":"text_delta","text":"Hi there"}}',
            "",
            "event: message_delta",
            'data: {"type":"message_delta","usage":{"output_tokens":7}}',
            "",
            "event: message_stop",
            'data: {"type":"message_stop"}',
            "",
        ]
    )

    _drive_stream(svc, api_key, session, "claude-3-sonnet", "anthropic", sse)

    step = _logged_llm_step(db, session.run_id)
    assert step is not None
    assert step.metadata_json["input_tokens"] == 20
    assert step.metadata_json["output_tokens"] == 7
    assert step.tokens == 27
    assert step.cost_usd > 0


def test_streaming_mid_stream_cost_kill_injects_termination_event():
    db = _make_db()
    api_key = _make_api_key(max_cost_usd=1e-9)  # ceiling so low the first chunk trips it
    db.add(api_key)
    db.commit()
    db.refresh(api_key)

    svc = GatewayService(db)
    session = svc.resolve_session(api_key, "stream-kill")

    sse = "\n".join(
        [
            'data: {"choices":[{"delta":{"content":"This is a long answer that keeps going"}}]}',
            "",
            'data: {"choices":[{"delta":{"content":"and going and going"}}]}',
            "",
            "data: [DONE]",
            "",
        ]
    )

    body = _drive_stream(svc, api_key, session, "gpt-4o", "openai", sse)

    assert "steerplane_enforcement" in body
    assert "cost_limit_exceeded" in body

    step = _logged_llm_step(db, session.run_id)
    assert step is not None
    assert step.status == "terminated"
