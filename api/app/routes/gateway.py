"""
OpenAI-compatible gateway routes.
"""

import time

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.orm import Session

from ..config import settings
from ..db.database import get_db
from ..services.gateway_service import (
    GatewayService,
    GatewaySession,
    MODEL_PRICING,
    calculate_cost,
    normalize_model_name,
)


router = APIRouter(prefix="/gateway/v1", tags=["Gateway"])

PROVIDER_URLS = {
    "openai": "https://api.openai.com/v1",
    "anthropic": "https://api.anthropic.com",
}


def _detect_provider(model: str) -> str:
    if model.lower().startswith("claude"):
        return "anthropic"
    return "openai"


def _get_provider_url(provider: str) -> str:
    return PROVIDER_URLS.get(provider, PROVIDER_URLS["openai"])


def _provider_error_payload(resp: httpx.Response) -> dict:
    try:
        payload = resp.json()
    except ValueError:
        payload = {"error": resp.text}
    return payload


@router.post("/chat/completions")
async def chat_completions(request: Request, db: Session = Depends(get_db)):
    """Proxy chat completions through SteerPlane enforcement."""
    svc = GatewayService(db)

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Missing Authorization header with SteerPlane API key",
        )

    sp_key = auth_header.replace("Bearer ", "").strip()
    if not sp_key.startswith("sk_sp_"):
        raise HTTPException(
            status_code=401,
            detail="Invalid SteerPlane API key format. Expected sk_sp_...",
        )

    api_key = svc.validate_api_key(sp_key)
    if not api_key:
        raise HTTPException(status_code=401, detail="Invalid or inactive API key")

    try:
        body = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON body") from exc

    model = body.get("model", "gpt-4o")
    messages = body.get("messages", [])
    is_streaming = body.get("stream", False)
    requested_session_id = request.headers.get("X-SteerPlane-Session-ID", "")

    if not messages:
        raise HTTPException(status_code=400, detail="'messages' field is required")

    decision = svc.pre_request_checks(
        api_key,
        model,
        messages,
        requested_session_id,
    )
    session = decision.session
    if decision.decision == "paused":
        svc.log_paused_request(api_key, session, model, decision.reason, decision.approval_id)
        return JSONResponse(
            status_code=202,
            content={
                "status": "paused",
                "awaiting_approval": True,
                "message": decision.reason,
                "type": "steerplane_approval_required",
                "session_id": session.session_id,
                "approval_id": decision.approval_id,
            },
            headers={"X-SteerPlane-Session-ID": session.session_id},
        )

    if decision.decision != "allow":
        svc.log_blocked_request(api_key, session, model, decision.reason)
        raise HTTPException(
            status_code=429,
            detail={
                "error": "request_blocked",
                "message": decision.reason,
                "type": "steerplane_enforcement",
                "session_id": session.session_id,
            },
        )

    llm_api_key = request.headers.get("X-LLM-API-Key", "")
    if not llm_api_key:
        raise HTTPException(
            status_code=400,
            detail="Missing X-LLM-API-Key header with your LLM provider API key",
        )

    custom_url = request.headers.get("X-Provider-URL", "")
    if custom_url:
        provider_url = custom_url.rstrip("/")
        if provider_url not in settings.ALLOWED_PROVIDER_URLS:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Custom provider URLs are disabled for this deployment. "
                    "Set STEERPLANE_ALLOWED_PROVIDER_URLS to allow specific upstreams."
                ),
            )
        provider = "openai"
    else:
        provider = _detect_provider(model)
        provider_url = _get_provider_url(provider)

    start_time = time.time()

    if provider == "anthropic":
        forward_headers = {
            "x-api-key": llm_api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }

        system_msg = None
        anthropic_messages = []
        for msg in messages:
            if msg.get("role") == "system":
                system_msg = msg.get("content", "")
            else:
                anthropic_messages.append(
                    {
                        "role": msg["role"],
                        "content": msg.get("content", ""),
                    }
                )

        proxy_body = {
            "model": model,
            "messages": anthropic_messages,
            "max_tokens": body.get("max_tokens", 4096),
        }
        if system_msg:
            proxy_body["system"] = system_msg
        if body.get("temperature") is not None:
            proxy_body["temperature"] = body["temperature"]

        target_url = f"{provider_url}/v1/messages"
    else:
        forward_headers = {
            "Authorization": f"Bearer {llm_api_key}",
            "Content-Type": "application/json",
        }
        target_url = f"{provider_url}/chat/completions"
        proxy_body = body

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            if is_streaming and provider != "anthropic":
                return await _handle_streaming(
                    client=client,
                    target_url=target_url,
                    headers=forward_headers,
                    body=proxy_body,
                    svc=svc,
                    api_key=api_key,
                    session=session,
                    model=model,
                    start_time=start_time,
                )
            resp = await client.post(
                target_url,
                headers=forward_headers,
                json=proxy_body,
            )
    except httpx.TimeoutException as exc:
        svc.log_request(
            api_key,
            session,
            model,
            0,
            0,
            0.0,
            (time.time() - start_time) * 1000,
            "timeout",
            "LLM request timed out",
        )
        raise HTTPException(status_code=504, detail="LLM provider request timed out") from exc
    except httpx.ConnectError as exc:
        svc.log_request(
            api_key,
            session,
            model,
            0,
            0,
            0.0,
            (time.time() - start_time) * 1000,
            "error",
            str(exc),
        )
        raise HTTPException(
            status_code=502,
            detail=f"Failed to connect to LLM provider: {exc}",
        ) from exc

    latency_ms = (time.time() - start_time) * 1000

    if resp.status_code != 200:
        svc.log_request(
            api_key,
            session,
            model,
            0,
            0,
            0.0,
            latency_ms,
            "error",
            f"Provider returned {resp.status_code}",
        )
        return JSONResponse(
            status_code=resp.status_code,
            content=_provider_error_payload(resp),
            headers={"X-SteerPlane-Session-ID": session.session_id},
        )

    response_data = resp.json()

    if provider == "anthropic":
        usage = response_data.get("usage", {})
        input_tokens = usage.get("input_tokens", 0)
        output_tokens = usage.get("output_tokens", 0)

        content_text = ""
        for block in response_data.get("content", []):
            if block.get("type") == "text":
                content_text += block.get("text", "")

        response_data = {
            "id": response_data.get("id", ""),
            "object": "chat.completion",
            "model": response_data.get("model", model),
            "choices": [{
                "index": 0,
                "message": {"role": "assistant", "content": content_text},
                "finish_reason": response_data.get("stop_reason", "stop"),
            }],
            "usage": {
                "prompt_tokens": input_tokens,
                "completion_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
            },
        }
    else:
        usage = response_data.get("usage", {})
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)

    normalized_model = normalize_model_name(model)
    cost = calculate_cost(normalized_model, input_tokens, output_tokens)
    svc.log_request(api_key, session, model, input_tokens, output_tokens, cost, latency_ms)
    pending_approval = svc.maybe_trigger_threshold_alert(api_key, session)

    session_cost = svc.get_session_cost(session)
    response_data["steerplane"] = {
        "cost_usd": cost,
        "session_cost_usd": session_cost,
        "cost_limit_usd": svc.get_session_cost_limit(api_key, session),
        "monthly_cost_usd": svc.get_monthly_cost(api_key),
        "monthly_cost_limit_usd": api_key.max_cost_monthly,
        "request_number": api_key.total_requests,
        "session_id": session.session_id,
        "awaiting_approval": pending_approval is not None,
        "approval_id": pending_approval.id if pending_approval else None,
    }

    return JSONResponse(
        content=response_data,
        headers={
            "X-SteerPlane-Session-ID": session.session_id,
            "X-SteerPlane-Session-Cost": str(session_cost),
        },
    )


async def _handle_streaming(
    client: httpx.AsyncClient,
    target_url: str,
    headers: dict,
    body: dict,
    svc: GatewayService,
    api_key,
    session: GatewaySession,
    model: str,
    start_time: float,
):
    """Handle streaming OpenAI-compatible responses."""
    body.setdefault("stream_options", {})
    body["stream_options"]["include_usage"] = True

    req = client.build_request(
        "POST",
        target_url,
        headers=headers,
        json=body,
    )
    resp = await client.send(req, stream=True)

    if resp.status_code != 200:
        content = await resp.aread()
        await resp.aclose()
        return JSONResponse(
            status_code=resp.status_code,
            content={"error": content.decode()},
            headers={"X-SteerPlane-Session-ID": session.session_id},
        )

    collected_usage = {}

    async def stream_generator():
        nonlocal collected_usage
        try:
            async for line in resp.aiter_lines():
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        yield "data: [DONE]\n\n"
                        break
                    try:
                        import json

                        chunk = json.loads(data)
                        if "usage" in chunk and chunk["usage"]:
                            collected_usage = chunk["usage"]
                    except Exception:
                        pass
                    yield f"{line}\n\n"
                elif line.strip():
                    yield f"{line}\n\n"
        finally:
            await resp.aclose()

            latency_ms = (time.time() - start_time) * 1000
            input_tokens = collected_usage.get("prompt_tokens", 0)
            output_tokens = collected_usage.get("completion_tokens", 0)
            normalized = normalize_model_name(model)
            cost = calculate_cost(normalized, input_tokens, output_tokens)
            svc.log_request(
                api_key,
                session,
                model,
                input_tokens,
                output_tokens,
                cost,
                latency_ms,
            )
            svc.maybe_trigger_threshold_alert(api_key, session)

    return StreamingResponse(
        stream_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-SteerPlane-Session-ID": session.session_id,
            "X-SteerPlane-Session-Cost": str(svc.get_session_cost(session)),
        },
    )


@router.get("/models")
async def list_models(request: Request, db: Session = Depends(get_db)):
    """List available models and pricing."""
    svc = GatewayService(db)

    auth_header = request.headers.get("Authorization", "")
    sp_key = (
        auth_header.replace("Bearer ", "").strip()
        if auth_header.startswith("Bearer ")
        else ""
    )

    if sp_key.startswith("sk_sp_"):
        api_key = svc.validate_api_key(sp_key)
        if not api_key:
            raise HTTPException(status_code=401, detail="Invalid API key")

    models = []
    for model_id, pricing in MODEL_PRICING.items():
        if model_id == "default":
            continue
        models.append({
            "id": model_id,
            "object": "model",
            "pricing": {
                "input_per_1m": pricing["input"],
                "output_per_1m": pricing["output"],
            },
        })

    return {"object": "list", "data": models}
