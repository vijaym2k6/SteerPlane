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
    agent_name: string;
    allowed_actions: string[];
    denied_actions: string[];
    rate_limits: RateLimitSpec[];
    require_approval: string[];
    is_active: boolean;
    created_at?: string;
    updated_at?: string;
}

export async function fetchPolicies(): Promise<PolicyConfig[]> {
    const res = await fetch(`${API_BASE}/policies`, { cache: "no-store" });
    if (!res.ok) throw new Error("Failed to fetch policies");
    return res.json();
}

export async function fetchPolicy(agentName: string): Promise<PolicyConfig> {
    const res = await fetch(`${API_BASE}/policies/${agentName}`, {
        cache: "no-store",
    });
    if (!res.ok) throw new Error(`Failed to fetch policy for ${agentName}`);
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
    agentName: string,
    policy: Partial<PolicyConfig>
): Promise<PolicyConfig> {
    const res = await fetch(`${API_BASE}/policies/${agentName}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(policy),
    });
    if (!res.ok) throw new Error(`Failed to update policy for ${agentName}`);
    return res.json();
}

export async function deletePolicy(agentName: string): Promise<void> {
    const res = await fetch(`${API_BASE}/policies/${agentName}`, {
        method: "DELETE",
    });
    if (!res.ok) throw new Error(`Failed to delete policy for ${agentName}`);
}

