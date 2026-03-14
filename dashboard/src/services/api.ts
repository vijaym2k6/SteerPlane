const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

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

export async function fetchRuns(limit = 50, offset = 0): Promise<RunListResponse> {
    const res = await fetch(`${API_BASE}/runs?limit=${limit}&offset=${offset}`, {
        cache: "no-store",
    });
    if (!res.ok) throw new Error("Failed to fetch runs");
    return res.json();
}

export async function fetchRun(runId: string): Promise<RunDetail> {
    const res = await fetch(`${API_BASE}/runs/${runId}`, {
        cache: "no-store",
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
    const res = await fetch(`${API_BASE}/policies`, { cache: "no-store" });
    if (!res.ok) throw new Error("Failed to fetch policies");
    const data: PolicyListResponse = await res.json();
    return data.policies;
}

export async function fetchPolicy(policyId: string): Promise<PolicyConfig> {
    const res = await fetch(`${API_BASE}/policies/${policyId}`, {
        cache: "no-store",
    });
    if (!res.ok) throw new Error(`Failed to fetch policy ${policyId}`);
    return res.json();
}

export async function createPolicy(policy: PolicyConfig): Promise<PolicyConfig> {
    const res = await fetch(`${API_BASE}/policies`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(policy),
    });
    if (!res.ok) throw new Error("Failed to create policy");
    return res.json();
}

export async function updatePolicy(
    policyId: string,
    policy: Partial<PolicyConfig>
): Promise<PolicyConfig> {
    const res = await fetch(`${API_BASE}/policies/${policyId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(policy),
    });
    if (!res.ok) throw new Error(`Failed to update policy ${policyId}`);
    return res.json();
}

export async function deletePolicy(policyId: string): Promise<void> {
    const res = await fetch(`${API_BASE}/policies/${policyId}`, {
        method: "DELETE",
    });
    if (!res.ok) throw new Error(`Failed to delete policy ${policyId}`);
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
}

export async function fetchAPIKeys(): Promise<APIKeyConfig[]> {
    const res = await fetch(`${API_BASE}/api-keys`, { cache: "no-store" });
    if (!res.ok) throw new Error("Failed to fetch API keys");
    const data: APIKeyListResponse = await res.json();
    return data.keys;
}

export async function createAPIKey(req: CreateKeyRequest): Promise<APIKeyConfig> {
    const res = await fetch(`${API_BASE}/api-keys`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(req),
    });
    if (!res.ok) throw new Error("Failed to create API key");
    return res.json();
}

export async function updateAPIKey(
    keyId: string,
    updates: Partial<CreateKeyRequest & { is_active: boolean }>
): Promise<APIKeyConfig> {
    const res = await fetch(`${API_BASE}/api-keys/${keyId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(updates),
    });
    if (!res.ok) throw new Error(`Failed to update API key ${keyId}`);
    return res.json();
}

export async function deleteAPIKey(keyId: string): Promise<void> {
    const res = await fetch(`${API_BASE}/api-keys/${keyId}`, {
        method: "DELETE",
    });
    if (!res.ok) throw new Error(`Failed to delete API key ${keyId}`);
}
