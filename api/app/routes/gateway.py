"""
SteerPlane API — Gateway Routes

OpenAI-compatible proxy endpoint.
Users point their OpenAI client to this endpoint and SteerPlane
automatically monitors, limits, and logs every LLM call.

Usage:
    client = openai.OpenAI(
        base_url="http://localhost:8000/gateway/v1",
        api_key="sk_sp_...",  # SteerPlane API key
        default_headers={"X-LLM-API-Key": "sk-..."}  # Real OpenAI key
    )
"""

import time
import httpx
from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, Field
from typing import Optional
from sqlalchemy.orm import Session

from ..db.database import get_db
from ..services.gateway_service import GatewayService, calculate_cost, normalize_model_name


router = APIRouter(prefix="/gateway/v1", tags=["Gateway"])


# ─── Supported provider base URLs ────────────────────────

PROVIDER_URLS = {
    "openai": "https://api.openai.com/v1",
    "anthropic": "https://api.anthropic.com",
}


def _detect_provider(model: str) -> str:
    """Detect provider from model name."""
    model_lower = model.lower()
    if model_lower.startswith("claude"):
        return "anthropic"
    return "openai"


def _get_provider_url(provider: str) -> str:
    return PROVIDER_URLS.get(provider, PROVIDER_URLS["openai"])


# ─── Chat Completions Proxy ──────────────────────────────

@router.post("/chat/completions")
async def chat_completions(request: Request, db: Session = Depends(get_db)):
    """
    OpenAI-compatible chat completions proxy.

    Accepts standard OpenAI /v1/chat/completions requests.
    Automatically: validates API key, checks policies, enforces cost limits,
    detects loops, proxies to the real LLM, logs telemetry.

    Headers:
        Authorization: Bearer sk_sp_...  (SteerPlane API key)
        X-LLM-API-Key: sk-...           (Real LLM provider key)
        X-Provider-URL: https://...      (Optional: custom provider URL)
    """
    svc = GatewayService(db)

    # 1. Extract SteerPlane API key
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Authorization header with SteerPlane API key")

    sp_key = auth_header.replace("Bearer ", "").strip()
    if not sp_key.startswith("sk_sp_"):
        raise HTTPException(status_code=401, detail="Invalid SteerPlane API key format. Expected sk_sp_...")

    # 2. Validate API key
    api_key = svc.validate_api_key(sp_key)
    if not api_key:
        raise HTTPException(status_code=401, detail="Invalid or inactive API key")

    # 3. Parse request body
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    model = body.get("model", "gpt-4o")
    messages = body.get("messages", [])
    is_streaming = body.get("stream", False)

    if not messages:
        raise HTTPException(status_code=400, detail="'messages' field is required")

    # 4. Pre-request checks (model policy, cost limit, rate limit, loop detection)
    allowed, reason = svc.pre_request_checks(api_key, model, messages)
    if not allowed:
        svc.log_blocked_request(api_key, model, reason)
        raise HTTPException(
            status_code=429,
            detail={
                "error": "request_blocked",
                "message": reason,
                "type": "steerplane_enforcement",
            },
        )

    # 5. Get the real LLM API key
    llm_api_key = request.headers.get("X-LLM-API-Key", "")
    if not llm_api_key:
        raise HTTPException(
            status_code=400,
            detail="Missing X-LLM-API-Key header with your LLM provider API key",
        )

    # 6. Determine provider URL and provider type
    custom_url = request.headers.get("X-Provider-URL", "")
    if custom_url:
        provider_url = custom_url.rstrip("/")
        provider = "openai"  # assume OpenAI-compatible for custom URLs
    else:
        provider = _detect_provider(model)
        provider_url = _get_provider_url(provider)

    # 7. Build provider-specific request
    start_time = time.time()

    if provider == "anthropic":
        # Anthropic uses x-api-key header, /v1/messages endpoint, and different body format
        forward_headers = {
            "x-api-key": llm_api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }

        # Convert OpenAI messages format to Anthropic format
        system_msg = None
        anthropic_messages = []
        for msg in messages:
            if msg.get("role") == "system":
                system_msg = msg.get("content", "")
            else:
                anthropic_messages.append({"role": msg["role"], "content": msg.get("content", "")})

        anthropic_body = {
            "model": model,
            "messages": anthropic_messages,
            "max_tokens": body.get("max_tokens", 4096),
        }
        if system_msg:
            anthropic_body["system"] = system_msg
        if body.get("temperature") is not None:
            anthropic_body["temperature"] = body["temperature"]

        target_url = f"{provider_url}/v1/messages"
        proxy_body = anthropic_body
    else:
        # OpenAI-compatible providers
        forward_headers = {
            "Authorization": f"Bearer {llm_api_key}",
            "Content-Type": "application/json",
        }
        target_url = f"{provider_url}/chat/completions"
        proxy_body = body

    # 8. Proxy the request to the real provider
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            if is_streaming and provider != "anthropic":
                # Streaming: forward chunks in real-time (OpenAI only for now)
                return await _handle_streaming(
                    client, target_url, forward_headers, proxy_body,
                    svc, api_key, model, start_time,
                )
            else:
                resp = await client.post(
                    target_url,
                    headers=forward_headers,
                    json=proxy_body,
                )
    except httpx.TimeoutException:
        svc.log_request(api_key, model, 0, 0, 0.0, (time.time() - start_time) * 1000, "timeout", "LLM request timed out")
        raise HTTPException(status_code=504, detail="LLM provider request timed out")
    except httpx.ConnectError as e:
        svc.log_request(api_key, model, 0, 0, 0.0, (time.time() - start_time) * 1000, "error", str(e))
        raise HTTPException(status_code=502, detail=f"Failed to connect to LLM provider: {e}")

    latency_ms = (time.time() - start_time) * 1000

    # 9. If provider returned an error, forward it
    if resp.status_code != 200:
        svc.log_request(
            api_key, model, 0, 0, 0.0, latency_ms,
            "error", f"Provider returned {resp.status_code}",
        )
        return JSONResponse(status_code=resp.status_code, content=resp.json())

    # 10. Parse response and extract token usage
    response_data = resp.json()

    if provider == "anthropic":
        # Anthropic response format: usage.input_tokens, usage.output_tokens
        usage = response_data.get("usage", {})
        input_tokens = usage.get("input_tokens", 0)
        output_tokens = usage.get("output_tokens", 0)

        # Convert Anthropic response to OpenAI-compatible format
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

    # 11. Calculate cost
    normalized_model = normalize_model_name(model)
    cost = calculate_cost(normalized_model, input_tokens, output_tokens)

    # 12. Log telemetry
    svc.log_request(api_key, model, input_tokens, output_tokens, cost, latency_ms)

    # 13. Inject SteerPlane metadata into response
    response_data["steerplane"] = {
        "cost_usd": cost,
        "session_cost_usd": _get_session_cost(api_key),
        "cost_limit_usd": api_key.max_cost_usd,
        "request_number": api_key.total_requests,
    }

    return JSONResponse(content=response_data)


async def _handle_streaming(
    client: httpx.AsyncClient,
    target_url: str,
    headers: dict,
    body: dict,
    svc: GatewayService,
    api_key,
    model: str,
    start_time: float,
):
    """Handle streaming responses — forward chunks and log after completion."""
    # Ensure stream_options includes usage for token counting
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
        return JSONResponse(status_code=resp.status_code, content={"error": content.decode()})

    collected_usage = {}

    async def stream_generator():
        nonlocal collected_usage
        try:
            async for line in resp.aiter_lines():
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        yield f"data: [DONE]\n\n"
                        break
                    try:
                        import json
                        chunk = json.loads(data)
                        # Capture usage from the final chunk
                        if "usage" in chunk and chunk["usage"]:
                            collected_usage = chunk["usage"]
                    except Exception:
                        pass
                    yield f"{line}\n\n"
                elif line.strip():
                    yield f"{line}\n\n"
        finally:
            await resp.aclose()

            # Log telemetry after stream completes
            latency_ms = (time.time() - start_time) * 1000
            input_tokens = collected_usage.get("prompt_tokens", 0)
            output_tokens = collected_usage.get("completion_tokens", 0)
            normalized = normalize_model_name(model)
            cost = calculate_cost(normalized, input_tokens, output_tokens)
            svc.log_request(api_key, model, input_tokens, output_tokens, cost, latency_ms)

    return StreamingResponse(
        stream_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-SteerPlane-Session-Cost": str(_get_session_cost(api_key)),
        },
    )


def _get_session_cost(api_key) -> float:
    """Get current session cost for an API key."""
    from ..services.gateway_service import _session_tracker
    session = _session_tracker.get_session(api_key.key_hash)
    return session["total_cost"] if session else 0.0


# ─── Gateway Status ──────────────────────────────────────

@router.get("/models")
async def list_models(request: Request, db: Session = Depends(get_db)):
    """List available models (OpenAI-compatible). Validates API key."""
    svc = GatewayService(db)

    auth_header = request.headers.get("Authorization", "")
    sp_key = auth_header.replace("Bearer ", "").strip() if auth_header.startswith("Bearer ") else ""

    if sp_key.startswith("sk_sp_"):
        api_key = svc.validate_api_key(sp_key)
        if not api_key:
            raise HTTPException(status_code=401, detail="Invalid API key")

    # Return a list of models with pricing
    from ..services.gateway_service import MODEL_PRICING
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
