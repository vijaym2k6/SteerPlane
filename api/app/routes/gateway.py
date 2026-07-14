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

    llm_api_key = svc.resolve_provider_key(api_key, request.headers.get("X-LLM-API-Key", ""))
    if not llm_api_key:
        raise HTTPException(
            status_code=400,
            detail="No provider key available: send the X-LLM-API-Key header",
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
            if is_streaming:
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
                    provider=provider,
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
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": content_text},
                    "finish_reason": response_data.get("stop_reason", "stop"),
                }
            ],
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

    session_cost = svc.get_session_cost(session)
    response_data["steerplane"] = {
        "cost_usd": cost,
        "session_cost_usd": session_cost,
        "cost_limit_usd": svc.get_session_cost_limit(api_key, session),
        "monthly_cost_usd": svc.get_monthly_cost(api_key),
        "monthly_cost_limit_usd": api_key.max_cost_monthly,
        "request_number": api_key.total_requests,
        "session_id": session.session_id,
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
    provider: str = "openai",
):
    """
    Handle streaming LLM responses with real-time chunk forwarding.

    Key behaviors:
    - Every SSE chunk is forwarded to the client immediately as it arrives
    - Token counts are accumulated during the stream
    - If cost ceiling is exceeded mid-stream, the stream is killed and a
      termination event is injected
    - Works with both OpenAI (data: {...}) and Anthropic (content_block_delta) formats
    """
    import json as _json

    if provider != "anthropic":
        body.setdefault("stream_options", {})
        body["stream_options"]["include_usage"] = True
    else:
        body["stream"] = True

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

    # Mutable accumulator shared between generator and finally block
    stream_state = {
        "input_tokens": 0,
        "output_tokens": 0,
        "terminated_mid_stream": False,
        "chunks_forwarded": 0,
    }

    # Pre-compute cost ceiling for mid-stream check
    cost_limit = svc.get_session_cost_limit(api_key, session)
    session_cost_before = svc.get_session_cost(session)

    async def stream_generator():
        try:
            async for line in resp.aiter_lines():
                if not line.strip():
                    continue

                # --- Parse usage, branching on provider FIRST ---
                # Both OpenAI and Anthropic emit `data: ` lines, so the provider
                # check must come before the `data:` check — otherwise Anthropic
                # chunks fall into the OpenAI parser, usage is never extracted,
                # and the mid-stream cost kill (below) can never fire for Claude.
                if provider == "anthropic":
                    if line.startswith("data: "):
                        try:
                            chunk = _json.loads(line[6:])
                            msg_type = chunk.get("type", "")
                            if msg_type == "message_start":
                                usage = chunk.get("message", {}).get("usage", {})
                                stream_state["input_tokens"] = usage.get(
                                    "input_tokens", stream_state["input_tokens"]
                                )
                                stream_state["output_tokens"] = usage.get(
                                    "output_tokens", stream_state["output_tokens"]
                                )
                            elif msg_type == "message_delta":
                                # Anthropic reports cumulative output_tokens here.
                                usage = chunk.get("usage", {})
                                stream_state["output_tokens"] = usage.get(
                                    "output_tokens", stream_state["output_tokens"]
                                )
                        except (ValueError, KeyError):
                            pass
                    # `event:` lines carry no usable usage payload; forward as-is.
                else:
                    # --- OpenAI SSE format ---
                    if line.startswith("data: "):
                        data = line[6:]
                        if data.strip() == "[DONE]":
                            yield "data: [DONE]\n\n"
                            break

                        try:
                            chunk = _json.loads(data)

                            # Authoritative usage from the final chunk (stream_options)
                            if "usage" in chunk and chunk["usage"]:
                                stream_state["input_tokens"] = chunk["usage"].get(
                                    "prompt_tokens", stream_state["input_tokens"]
                                )
                                stream_state["output_tokens"] = chunk["usage"].get(
                                    "completion_tokens", stream_state["output_tokens"]
                                )

                            # Estimate output tokens from delta content length
                            choices = chunk.get("choices", [])
                            if choices:
                                delta = choices[0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    # Rough estimate: ~4 chars per token
                                    stream_state["output_tokens"] += max(1, len(content) // 4)

                        except (ValueError, KeyError):
                            pass

                # --- Mid-stream cost enforcement ---
                normalized = normalize_model_name(model)
                running_cost = calculate_cost(
                    normalized,
                    stream_state["input_tokens"],
                    stream_state["output_tokens"],
                )
                total_session_cost = session_cost_before + running_cost

                if cost_limit and total_session_cost >= cost_limit:
                    # Kill the stream — inject termination event
                    termination_event = {
                        "error": {
                            "type": "steerplane_enforcement",
                            "message": (
                                f"Stream terminated: session cost ${total_session_cost:.4f} "
                                f"exceeded ceiling ${cost_limit:.2f}"
                            ),
                            "code": "cost_limit_exceeded",
                            "session_id": session.session_id,
                        }
                    }
                    yield f"data: {_json.dumps(termination_event)}\n\n"
                    yield "data: [DONE]\n\n"
                    stream_state["terminated_mid_stream"] = True
                    break

                # Forward the chunk immediately
                stream_state["chunks_forwarded"] += 1
                yield f"{line}\n\n"

        finally:
            await resp.aclose()

            # Log the completed (or terminated) stream
            latency_ms = (time.time() - start_time) * 1000
            normalized = normalize_model_name(model)
            cost = calculate_cost(
                normalized,
                stream_state["input_tokens"],
                stream_state["output_tokens"],
            )
            status = "terminated" if stream_state["terminated_mid_stream"] else None
            error_msg = (
                "Mid-stream cost ceiling exceeded"
                if stream_state["terminated_mid_stream"]
                else None
            )

            svc.log_request(
                api_key,
                session,
                model,
                stream_state["input_tokens"],
                stream_state["output_tokens"],
                cost,
                latency_ms,
                status,
                error_msg,
            )

    return StreamingResponse(
        stream_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "X-SteerPlane-Session-ID": session.session_id,
            "X-SteerPlane-Session-Cost": str(session_cost_before),
        },
    )


@router.get("/models")
async def list_models(request: Request, db: Session = Depends(get_db)):
    """List available models and pricing."""
    svc = GatewayService(db)

    auth_header = request.headers.get("Authorization", "")
    sp_key = auth_header.replace("Bearer ", "").strip() if auth_header.startswith("Bearer ") else ""

    if sp_key.startswith("sk_sp_"):
        api_key = svc.validate_api_key(sp_key)
        if not api_key:
            raise HTTPException(status_code=401, detail="Invalid API key")

    models = []
    for model_id, pricing in MODEL_PRICING.items():
        if model_id == "default":
            continue
        models.append(
            {
                "id": model_id,
                "object": "model",
                "pricing": {
                    "input_per_1m": pricing["input"],
                    "output_per_1m": pricing["output"],
                },
            }
        )

    return {"object": "list", "data": models}
