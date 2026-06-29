/**
 * Demo mode — serves realistic seeded data so the dashboard can be shown as a
 * live, read-only preview (e.g. on app.steerplane.com) with no backend.
 *
 * Enabled by setting NEXT_PUBLIC_STEERPLANE_DEMO=true at build time. When off
 * (the default, and how self-hosters run it), every API call hits the real
 * SteerPlane API exactly as before.
 */
import type {
    Run,
    RunDetail,
    RunListResponse,
    Step,
    PolicyConfig,
    APIKeyConfig,
    CreateKeyRequest,
    ApprovalRequest,
} from "./api";

export const DEMO_MODE = process.env.NEXT_PUBLIC_STEERPLANE_DEMO === "true";

const now = Date.now();
const iso = (minsAgo: number) => new Date(now - minsAgo * 60_000).toISOString();
const delay = <T>(value: T): Promise<T> =>
    new Promise((resolve) => setTimeout(() => resolve(value), 120));

// ─── Seeded runs ───────────────────────────────────────────────────────────
let runs: Run[] = [
    {
        id: "run_8f3a21", agent_name: "support_bot", status: "completed",
        start_time: iso(12), end_time: iso(11), total_cost: 2.34, total_steps: 18,
        total_tokens: 45210, max_cost_usd: 10, max_steps_limit: 50, error: null, error_details: null,
    },
    {
        id: "run_8f3a1d", agent_name: "research_agent", status: "running",
        start_time: iso(3), end_time: null, total_cost: 1.12, total_steps: 7,
        total_tokens: 21800, max_cost_usd: 15, max_steps_limit: 60, error: null, error_details: null,
    },
    {
        id: "run_8f39c4", agent_name: "data_pipeline_agent", status: "terminated",
        start_time: iso(28), end_time: iso(27), total_cost: 0.91, total_steps: 24,
        total_tokens: 18900, max_cost_usd: 10, max_steps_limit: 80,
        error: "Loop detected: pattern ['search_web', 'parse_results'] repeated 3×",
        error_details: {
            error_type: "loop_detected",
            pattern_detected: ["search_web", "parse_results"],
            window_size: 8,
            recent_actions: ["search_web", "parse_results", "search_web", "parse_results", "search_web", "parse_results"],
            step_number: 24,
        },
    },
    {
        id: "run_8f3987", agent_name: "invoice_agent", status: "terminated",
        start_time: iso(46), end_time: iso(45), total_cost: 5.02, total_steps: 41,
        total_tokens: 98400, max_cost_usd: 5, max_steps_limit: 100,
        error: "Cost ceiling $5.00 exceeded",
        error_details: {
            error_type: "cost_limit_exceeded",
            current_cost: 5.02, max_cost: 5.0, step_number: 41,
            total_cost_at_termination: 5.02,
        },
    },
    {
        id: "run_8f3955", agent_name: "finance_bot", status: "awaiting_approval",
        start_time: iso(2), end_time: null, total_cost: 7.8, total_steps: 33,
        total_tokens: 71200, max_cost_usd: 8, max_steps_limit: 60, error: null, error_details: null,
    },
    {
        id: "run_8f3902", agent_name: "code_assistant", status: "completed",
        start_time: iso(74), end_time: iso(72), total_cost: 0.87, total_steps: 12,
        total_tokens: 16500, max_cost_usd: 5, max_steps_limit: 40, error: null, error_details: null,
    },
    {
        id: "run_8f38ab", agent_name: "scraper_agent", status: "failed",
        start_time: iso(95), end_time: iso(94), total_cost: 0.21, total_steps: 4,
        total_tokens: 5200, max_cost_usd: 5, max_steps_limit: 40,
        error: "Upstream provider returned 500",
        error_details: { error_type: "provider_error", message: "Upstream provider returned 500" },
    },
    {
        id: "run_8f3840", agent_name: "email_triage", status: "completed",
        start_time: iso(140), end_time: iso(139), total_cost: 0.34, total_steps: 6,
        total_tokens: 8800, max_cost_usd: 3, max_steps_limit: 30, error: null, error_details: null,
    },
];

const stepsFor = (runId: string, names: string[]): Step[] =>
    names.map((action, i) => ({
        id: `${runId}_s${i + 1}`, run_id: runId, step_number: i + 1, action,
        tokens: 1800 + i * 320, cost_usd: Number((0.05 + i * 0.012).toFixed(4)),
        latency_ms: 420 + i * 60, status: "completed", error: null,
        metadata_json: null, timestamp: iso(12 - i * 0.4),
    }));

const runDetails: Record<string, Step[]> = {
    run_8f3a21: stepsFor("run_8f3a21", ["load_ticket", "search_kb", "summarize", "draft_reply", "send_email_response"]),
    run_8f39c4: stepsFor("run_8f39c4", ["search_web", "parse_results", "search_web", "parse_results", "search_web", "parse_results"]),
};

// ─── Seeded policies ─────────────────────────────────────────────────────────
let policies: PolicyConfig[] = [
    {
        id: "pol_prod", name: "Production Safety", description: "Blocks destructive ops, gates refunds.",
        allowed_actions: ["search_*", "read_*", "summarize", "draft_*"],
        denied_actions: ["delete_*", "drop_*", "sudo_*"],
        rate_limits: [{ pattern: "send_email", max_count: 5, window_seconds: 60 }],
        require_approval: ["refund_*"], is_active: true, created_at: iso(4000), updated_at: iso(200),
    },
    {
        id: "pol_research", name: "Read-Only Research", description: "Lets agents read, never write.",
        allowed_actions: ["search_*", "read_*", "fetch_*", "summarize"],
        denied_actions: ["write_*", "delete_*", "post_*"],
        rate_limits: [], require_approval: [], is_active: true, created_at: iso(5200), updated_at: iso(900),
    },
    {
        id: "pol_finance", name: "Finance Guardrails", description: "Human approval for money movement.",
        allowed_actions: [], denied_actions: ["delete_*"],
        rate_limits: [{ pattern: "create_invoice", max_count: 20, window_seconds: 300 }],
        require_approval: ["wire_*", "refund_*", "payout_*"], is_active: false, created_at: iso(2600), updated_at: iso(120),
    },
];

// ─── Seeded API keys ──────────────────────────────────────────────────────────
let apiKeys: APIKeyConfig[] = [
    {
        id: "key_prod", name: "prod-support-bot", key_prefix: "sk_sp_live_a31f", max_cost_usd: 10,
        max_cost_monthly: 500, max_requests_per_min: 60, allowed_models: null, denied_models: null,
        enforcement_mode: "kill", alert_threshold: 0.8, alert_timeout_sec: 1800, alert_channels: [],
        alert_email: null, alert_webhook_url: null, is_active: true, total_requests: 12840,
        total_cost: 218.42, total_tokens: 5_120_000, last_used_at: iso(11), created_at: iso(8000),
    },
    {
        id: "key_research", name: "research-sandbox", key_prefix: "sk_sp_live_77be", max_cost_usd: 15,
        max_cost_monthly: 100, max_requests_per_min: 30, allowed_models: null, denied_models: null,
        enforcement_mode: "alert", alert_threshold: 0.75, alert_timeout_sec: 900, alert_channels: ["email"],
        alert_email: "ops@steerplane.com", alert_webhook_url: null, is_active: true, total_requests: 3420,
        total_cost: 41.07, total_tokens: 980_000, last_used_at: iso(3), created_at: iso(6000),
    },
    {
        id: "key_finance", name: "finance-bot", key_prefix: "sk_sp_live_0c9d", max_cost_usd: 8,
        max_cost_monthly: 200, max_requests_per_min: 20, allowed_models: null, denied_models: null,
        enforcement_mode: "alert", alert_threshold: 0.9, alert_timeout_sec: 1800,
        alert_channels: ["email", "webhook"], alert_email: "finance@steerplane.com",
        alert_webhook_url: "https://hooks.slack.com/services/…", is_active: true, total_requests: 980,
        total_cost: 63.5, total_tokens: 1_240_000, last_used_at: iso(2), created_at: iso(3000),
    },
];

// ─── Seeded approvals ──────────────────────────────────────────────────────────
let approvals: ApprovalRequest[] = [
    {
        id: "apr_5521", run_id: "run_8f3955", agent_name: "finance_bot", scope: "run",
        approval_type: "cost_limit", status: "pending",
        message: "finance_bot reached 97% of its $8.00 cost ceiling. Approve to extend the budget and continue.",
        current_value: 7.8, limit_value: 8.0, unit: "usd", timeout_sec: 1800,
        session_id: "sess_77a2", api_key_id: "key_finance", channels_json: ["email", "webhook"],
        alert_email: "finance@steerplane.com", alert_webhook_url: "https://hooks.slack.com/services/…",
        metadata_json: null, resolution_json: null, created_at: iso(2), expires_at: iso(-28),
        resolved_at: null, resolved_by: null, resolution_note: null,
    },
    {
        id: "apr_5519", run_id: "run_8f3a1d", agent_name: "research_agent", scope: "run",
        approval_type: "step_limit", status: "pending",
        message: "research_agent is approaching its 60-step limit. Approve to grant 20 more steps.",
        current_value: 54, limit_value: 60, unit: "steps", timeout_sec: 900,
        session_id: "sess_19b0", api_key_id: "key_research", channels_json: ["email"],
        alert_email: "ops@steerplane.com", alert_webhook_url: null,
        metadata_json: null, resolution_json: null, created_at: iso(1), expires_at: iso(-14),
        resolved_at: null, resolved_by: null, resolution_note: null,
    },
];

// ─── Demo API surface (mirrors api.ts) ──────────────────────────────────────
export const demo = {
    fetchRuns: (limit = 50, offset = 0): Promise<RunListResponse> =>
        delay({ runs: runs.slice(offset, offset + limit), total: runs.length, limit, offset }),

    fetchRun: (runId: string): Promise<RunDetail> => {
        const run = runs.find((r) => r.id === runId) ?? runs[0];
        return delay({ ...run, steps: runDetails[run.id] ?? stepsFor(run.id, ["start", "think", "act", "finish"]) });
    },

    fetchPolicies: (): Promise<PolicyConfig[]> => delay([...policies]),
    fetchPolicy: (id: string): Promise<PolicyConfig> => delay(policies.find((p) => p.id === id) ?? policies[0]),
    createPolicy: (p: PolicyConfig): Promise<PolicyConfig> => {
        const created = { ...p, id: `pol_${Math.random().toString(36).slice(2, 8)}`, created_at: iso(0), updated_at: iso(0) };
        policies = [created, ...policies];
        return delay(created);
    },
    updatePolicy: (id: string, p: Partial<PolicyConfig>): Promise<PolicyConfig> => {
        policies = policies.map((x) => (x.id === id ? { ...x, ...p, updated_at: iso(0) } : x));
        return delay(policies.find((x) => x.id === id)!);
    },
    deletePolicy: (id: string): Promise<void> => {
        policies = policies.filter((x) => x.id !== id);
        return delay(undefined);
    },

    fetchAPIKeys: (): Promise<APIKeyConfig[]> => delay([...apiKeys]),
    createAPIKey: (req: CreateKeyRequest): Promise<APIKeyConfig> => {
        const id = `key_${Math.random().toString(36).slice(2, 8)}`;
        const created: APIKeyConfig = {
            id, name: req.name, key_prefix: "sk_sp_live_demo", raw_key: `sk_sp_live_${Math.random().toString(36).slice(2, 18)}`,
            max_cost_usd: req.max_cost_usd ?? 10, max_cost_monthly: req.max_cost_monthly ?? 100,
            max_requests_per_min: req.max_requests_per_min ?? 60, allowed_models: req.allowed_models ?? null,
            denied_models: req.denied_models ?? null, enforcement_mode: req.enforcement_mode ?? "kill",
            alert_threshold: req.alert_threshold ?? 0.8, alert_timeout_sec: req.alert_timeout_sec ?? 1800,
            alert_channels: req.alert_channels ?? [], alert_email: req.alert_email ?? null,
            alert_webhook_url: req.alert_webhook_url ?? null, is_active: true, total_requests: 0,
            total_cost: 0, total_tokens: 0, last_used_at: null, created_at: iso(0),
        };
        apiKeys = [created, ...apiKeys];
        return delay(created);
    },
    updateAPIKey: (id: string, u: Partial<CreateKeyRequest & { is_active: boolean }>): Promise<APIKeyConfig> => {
        apiKeys = apiKeys.map((k) => (k.id === id ? { ...k, ...u } : k));
        return delay(apiKeys.find((k) => k.id === id)!);
    },
    deleteAPIKey: (id: string): Promise<void> => {
        apiKeys = apiKeys.filter((k) => k.id !== id);
        return delay(undefined);
    },

    fetchApprovals: (status?: string, limit = 100): Promise<ApprovalRequest[]> =>
        delay(approvals.filter((a) => !status || a.status === status).slice(0, limit)),
    approveRequest: (id: string, body: { note?: string; extension_value?: number } = {}): Promise<ApprovalRequest> => {
        approvals = approvals.map((a) =>
            a.id === id
                ? { ...a, status: "approved", resolved_at: iso(0), resolved_by: "demo-operator", resolution_note: body.note ?? null }
                : a,
        );
        return delay(approvals.find((a) => a.id === id)!);
    },
    denyRequest: (id: string, body: { note?: string } = {}): Promise<ApprovalRequest> => {
        approvals = approvals.map((a) =>
            a.id === id
                ? { ...a, status: "denied", resolved_at: iso(0), resolved_by: "demo-operator", resolution_note: body.note ?? null }
                : a,
        );
        return delay(approvals.find((a) => a.id === id)!);
    },
};
