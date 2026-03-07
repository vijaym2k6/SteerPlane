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
