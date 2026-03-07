/**
 * SteerPlane SDK — API Client
 *
 * HTTP client that communicates with the SteerPlane API server.
 * Uses native fetch (Node 18+). Gracefully degrades if API is unreachable.
 */

export class SteerPlaneClient {
  private readonly apiUrl: string;
  private readonly apiKey: string | undefined;
  private apiAvailable: boolean = true;

  constructor(apiUrl?: string, apiKey?: string) {
    this.apiUrl = (
      apiUrl ?? process.env.STEERPLANE_API_URL ?? "http://localhost:8000"
    ).replace(/\/+$/, "");
    this.apiKey = apiKey;
  }

  private async request<T = Record<string, unknown>>(
    method: string,
    path: string,
    body?: Record<string, unknown>
  ): Promise<T | null> {
    if (!this.apiAvailable) return null;

    const url = `${this.apiUrl}${path}`;
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      "User-Agent": "SteerPlane-SDK-TS/0.1.0",
    };
    if (this.apiKey) {
      headers["Authorization"] = `Bearer ${this.apiKey}`;
    }

    try {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 5000);

      const response = await fetch(url, {
        method,
        headers,
        body: body ? JSON.stringify(body) : undefined,
        signal: controller.signal,
      });

      clearTimeout(timeout);

      if (!response.ok) {
        console.warn(`⚠️  SteerPlane API returned ${response.status}: ${url}`);
        return null;
      }

      return (await response.json()) as T;
    } catch (err: unknown) {
      const isAbort =
        err instanceof Error && err.name === "AbortError";
      if (isAbort) {
        console.warn(`⚠️  SteerPlane API timeout: ${url}`);
      } else {
        this.apiAvailable = false;
        console.warn(
          `⚠️  SteerPlane API not reachable at ${this.apiUrl}. ` +
            `Running in offline mode (guards still active, no dashboard data).`
        );
      }
      return null;
    }
  }

  /** Register a new run with the API. */
  async startRun(
    runId: string,
    agentName: string,
    maxCostUsd: number = 0,
    maxSteps: number = 0
  ) {
    return this.request("POST", "/runs/start", {
      run_id: runId,
      agent_name: agentName,
      max_cost_usd: maxCostUsd,
      max_steps: maxSteps,
    });
  }

  /** Log a step event to the API. */
  async logStep(opts: {
    runId: string;
    stepNumber: number;
    action: string;
    tokens?: number;
    costUsd?: number;
    latencyMs?: number;
    status?: string;
    error?: string;
    metadata?: Record<string, unknown>;
  }) {
    return this.request("POST", "/runs/step", {
      run_id: opts.runId,
      step_number: opts.stepNumber,
      action: opts.action,
      tokens: opts.tokens ?? 0,
      cost_usd: opts.costUsd ?? 0,
      latency_ms: opts.latencyMs ?? 0,
      status: opts.status ?? "completed",
      error: opts.error ?? null,
      metadata: opts.metadata ?? {},
    });
  }

  /** Finalize a run. */
  async endRun(
    runId: string,
    status: string = "completed",
    totalCost: number = 0,
    totalSteps: number = 0,
    error?: string
  ) {
    return this.request("POST", "/runs/end", {
      run_id: runId,
      status,
      total_cost: totalCost,
      total_steps: totalSteps,
      error: error ?? null,
    });
  }

  /** Fetch run details. */
  async getRun(runId: string) {
    return this.request("GET", `/runs/${runId}`);
  }

  /** List recent runs. */
  async listRuns(limit: number = 50, offset: number = 0) {
    return this.request("GET", `/runs?limit=${limit}&offset=${offset}`);
  }

  /** Check if API is reachable. */
  get isConnected(): boolean {
    return this.apiAvailable;
  }
}
