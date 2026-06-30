import { getAdminToken } from "./admin-auth";
import { DEMO_MODE, demo } from "./demo-data";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const ADMIN_TOKEN_HEADER = "X-SteerPlane-Admin-Token";

function withAdminHeaders(headers: HeadersInit = {}): HeadersInit {
    const token = getAdminToken();
    if (!token) return headers;
    return {
        ...headers,
        [ADMIN_TOKEN_HEADER]: token,
    };
}

async function readError(res: Response, fallback: string): Promise<Error> {
    const clone = res.clone();
    try {
        const data = await res.json();
        const detail = data?.detail ?? data?.message ?? data?.error;
        if (typeof detail === "string" && detail.trim()) {
            return new Error(detail);
        }
        if (detail && typeof detail.message === "string") {
            return new Error(detail.message);
        }
    } catch {
        try {
            const text = await clone.text();
            if (text.trim()) return new Error(text);
        } catch {
            // Ignore body parsing failures and fall back to the default message.
        }
    }
    return new Error(fallback);
}

// ─── Data Types ────────────────────────────────────────

export interface Step {
    id: string;
    run_id: string;
    step_number: number;
    action: string;
    tokens: number;
    cost_usd: number;
    latency_ms: number;
    status: string;
    error: string | null;
    metadata_json: Record<string, unknown> | null;
    timestamp: string;
}

export interface ErrorDetails {
    error_type: string;
    blocked_action?: string;
    rule_matched?: string;
    reason?: string;
    message?: string;
    step_number?: number;
    total_cost_at_termination?: number;
    current_cost?: number;
    max_cost?: number;
    current_steps?: number;
    max_steps?: number;
    pattern_detected?: string[];
    window_size?: number;
    recent_actions?: string[];
    elapsed_seconds?: number;
    max_runtime_seconds?: number;
    approval_id?: string;
    approval_type?: string;
    current_value?: number;
    limit_value?: number;
    unit?: string;
    expires_at?: string;
}

export interface Run {
    id: string;
    agent_name: string;
    status: string;
    start_time: string;
    end_time: string | null;
    total_cost: number;
    total_steps: number;
    total_tokens: number;
    max_cost_usd: number;
    max_steps_limit: number;
    error: string | null;
    error_details: ErrorDetails | null;
}

export interface RunDetail extends Run {
    steps: Step[];
}

export interface RunListResponse {
    runs: Run[];
    total: number;
    limit: number;
    offset: number;
}

// ─── Runs API ────────────────────────────────────────

export async function fetchRuns(limit = 50, offset = 0): Promise<RunListResponse> {
    if (DEMO_MODE) return demo.fetchRuns(limit, offset);
    // Admin header is sent when configured so reads still work if the operator
    // turns on STEERPLANE_REQUIRE_RUN_AUTH; it is ignored when auth is off.
    const res = await fetch(`${API_BASE}/runs?limit=${limit}&offset=${offset}`, {
        cache: "no-store",
        headers: withAdminHeaders(),
    });
    if (!res.ok) throw new Error("Failed to fetch runs");
    return res.json();
}

export async function fetchRun(runId: string): Promise<RunDetail> {
    if (DEMO_MODE) return demo.fetchRun(runId);
    const res = await fetch(`${API_BASE}/runs/${runId}`, {
        cache: "no-store",
        headers: withAdminHeaders(),
    });
    if (!res.ok) throw new Error(`Failed to fetch run ${runId}`);
    return res.json();
}

// ─── Policy API ────────────────────────────────────────

export interface RateLimitSpec {
    pattern: string;
    max_count: number;
    window_seconds: number;
}

export interface PolicyConfig {
    id?: string;
    name: string;
    description?: string;
    allowed_actions: string[];
    denied_actions: string[];
    rate_limits: RateLimitSpec[];
    require_approval: string[];
    is_active: boolean;
    created_at?: string;
    updated_at?: string;
}

export interface PolicyListResponse {
    policies: PolicyConfig[];
    total: number;
    limit: number;
    offset: number;
}

export async function fetchPolicies(): Promise<PolicyConfig[]> {
    if (DEMO_MODE) return demo.fetchPolicies();
    const res = await fetch(`${API_BASE}/policies`, {
        cache: "no-store",
        headers: withAdminHeaders(),
    });
    if (!res.ok) throw await readError(res, "Failed to fetch policies");
    const data: PolicyListResponse = await res.json();
    return data.policies;
}

export async function fetchPolicy(policyId: string): Promise<PolicyConfig> {
    if (DEMO_MODE) return demo.fetchPolicy(policyId);
    const res = await fetch(`${API_BASE}/policies/${policyId}`, {
        cache: "no-store",
        headers: withAdminHeaders(),
    });
    if (!res.ok) throw await readError(res, `Failed to fetch policy ${policyId}`);
    return res.json();
}

export async function createPolicy(policy: PolicyConfig): Promise<PolicyConfig> {
    if (DEMO_MODE) return demo.createPolicy(policy);
    const res = await fetch(`${API_BASE}/policies`, {
        method: "POST",
        headers: withAdminHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify(policy),
    });
    if (!res.ok) throw await readError(res, "Failed to create policy");
    return res.json();
}

export async function updatePolicy(
    policyId: string,
    policy: Partial<PolicyConfig>
): Promise<PolicyConfig> {
    if (DEMO_MODE) return demo.updatePolicy(policyId, policy);
    const res = await fetch(`${API_BASE}/policies/${policyId}`, {
        method: "PUT",
        headers: withAdminHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify(policy),
    });
    if (!res.ok) throw await readError(res, `Failed to update policy ${policyId}`);
    return res.json();
}

export async function deletePolicy(policyId: string): Promise<void> {
    if (DEMO_MODE) return demo.deletePolicy(policyId);
    const res = await fetch(`${API_BASE}/policies/${policyId}`, {
        method: "DELETE",
        headers: withAdminHeaders(),
    });
    if (!res.ok) throw await readError(res, `Failed to delete policy ${policyId}`);
}

// ─── API Keys ────────────────────────────────────────────

export interface APIKeyConfig {
    id: string;
    name: string;
    key_prefix: string;
    raw_key?: string;
    max_cost_usd: number;
    max_cost_monthly: number;
    max_requests_per_min: number;
    allowed_models: string | null;
    denied_models: string | null;
    enforcement_mode: string;
    alert_threshold: number;
    alert_timeout_sec: number;
    alert_channels: string[];
    alert_email: string | null;
    alert_webhook_url: string | null;
    is_active: boolean;
    total_requests: number;
    total_cost: number;
    total_tokens: number;
    last_used_at: string | null;
    created_at: string;
}

export interface APIKeyListResponse {
    keys: APIKeyConfig[];
    total: number;
}

export interface CreateKeyRequest {
    name: string;
    max_cost_usd?: number;
    max_cost_monthly?: number;
    max_requests_per_min?: number;
    allowed_models?: string | null;
    denied_models?: string | null;
    enforcement_mode?: string;
    alert_threshold?: number;
    alert_timeout_sec?: number;
    alert_channels?: string[];
    alert_email?: string | null;
    alert_webhook_url?: string | null;
}

export async function fetchAPIKeys(): Promise<APIKeyConfig[]> {
    if (DEMO_MODE) return demo.fetchAPIKeys();
    const res = await fetch(`${API_BASE}/api-keys`, {
        cache: "no-store",
        headers: withAdminHeaders(),
    });
    if (!res.ok) throw await readError(res, "Failed to fetch API keys");
    const data: APIKeyListResponse = await res.json();
    return data.keys;
}

export async function createAPIKey(req: CreateKeyRequest): Promise<APIKeyConfig> {
    if (DEMO_MODE) return demo.createAPIKey(req);
    const res = await fetch(`${API_BASE}/api-keys`, {
        method: "POST",
        headers: withAdminHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify(req),
    });
    if (!res.ok) throw await readError(res, "Failed to create API key");
    return res.json();
}

export async function updateAPIKey(
    keyId: string,
    updates: Partial<CreateKeyRequest & { is_active: boolean }>
): Promise<APIKeyConfig> {
    if (DEMO_MODE) return demo.updateAPIKey(keyId, updates);
    const res = await fetch(`${API_BASE}/api-keys/${keyId}`, {
        method: "PUT",
        headers: withAdminHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify(updates),
    });
    if (!res.ok) throw await readError(res, `Failed to update API key ${keyId}`);
    return res.json();
}

export async function deleteAPIKey(keyId: string): Promise<void> {
    if (DEMO_MODE) return demo.deleteAPIKey(keyId);
    const res = await fetch(`${API_BASE}/api-keys/${keyId}`, {
        method: "DELETE",
        headers: withAdminHeaders(),
    });
    if (!res.ok) throw await readError(res, `Failed to delete API key ${keyId}`);
}

// ─── Approvals ───────────────────────────────────────────

export interface ApprovalResolution {
    decision?: string;
    extension_value?: number;
    new_limit?: number;
    note?: string | null;
    reason?: string | null;
}

export interface ApprovalRequest {
    id: string;
    run_id: string;
    agent_name: string;
    scope: string;
    approval_type: string;
    status: string;
    message: string;
    current_value: number;
    limit_value: number;
    unit: string;
    timeout_sec: number;
    session_id: string | null;
    api_key_id: string | null;
    channels_json: string[];
    alert_email: string | null;
    alert_webhook_url: string | null;
    metadata_json: Record<string, unknown> | null;
    resolution_json: ApprovalResolution | null;
    created_at: string;
    expires_at: string;
    resolved_at: string | null;
    resolved_by: string | null;
    resolution_note: string | null;
}

export interface ApprovalListResponse {
    approvals: ApprovalRequest[];
    total: number;
}

export async function fetchApprovals(status?: string, limit = 100): Promise<ApprovalRequest[]> {
    const params = new URLSearchParams();
    params.set("limit", String(limit));
    if (status && status.trim()) {
        params.set("status", status);
    }

    if (DEMO_MODE) return demo.fetchApprovals(status, limit);
    const res = await fetch(`${API_BASE}/approvals?${params.toString()}`, {
        cache: "no-store",
        headers: withAdminHeaders(),
    });
    if (!res.ok) throw await readError(res, "Failed to fetch approvals");
    const data: ApprovalListResponse = await res.json();
    return data.approvals;
}

export async function approveRequest(
    approvalId: string,
    body: { note?: string; extension_value?: number } = {}
): Promise<ApprovalRequest> {
    if (DEMO_MODE) return demo.approveRequest(approvalId, body);
    const res = await fetch(`${API_BASE}/approvals/${approvalId}/approve`, {
        method: "POST",
        headers: withAdminHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify(body),
    });
    if (!res.ok) throw await readError(res, `Failed to approve request ${approvalId}`);
    return res.json();
}

export async function denyRequest(
    approvalId: string,
    body: { note?: string } = {}
): Promise<ApprovalRequest> {
    if (DEMO_MODE) return demo.denyRequest(approvalId, body);
    const res = await fetch(`${API_BASE}/approvals/${approvalId}/deny`, {
        method: "POST",
        headers: withAdminHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify(body),
    });
    if (!res.ok) throw await readError(res, `Failed to deny request ${approvalId}`);
    return res.json();
}
