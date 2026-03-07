/**
 * SteerPlane SDK — Run Manager
 *
 * Orchestrates the full run lifecycle:
 * start → logStep → detectLoop → checkCost → end
 */

import { SteerPlaneClient } from "./client.js";
import { LoopDetector } from "./loop-detector.js";
import { CostTracker, type StepCost } from "./cost-tracker.js";
import { generateRunId, formatCost, formatDuration } from "./utils.js";
import {
  LoopDetectedError,
  CostLimitExceeded,
  StepLimitExceeded,
  RunTerminatedError,
} from "./errors.js";

export interface LogStepOptions {
  /** Action name (e.g., 'search_web', 'call_llm'). */
  action: string;
  /** Total tokens (if not split into input/output). */
  tokens?: number;
  /** Input/prompt tokens. */
  inputTokens?: number;
  /** Output/completion tokens. */
  outputTokens?: number;
  /** Explicit cost override in USD (skips calculation). */
  cost?: number;
  /** Step latency in milliseconds. */
  latencyMs?: number;
  /** Step status. */
  status?: string;
  /** Error message if step failed. */
  error?: string;
  /** Additional metadata. */
  metadata?: Record<string, unknown>;
  /** Model name for cost calculation. */
  model?: string;
}

export interface RunManagerOptions {
  agentName?: string;
  runId?: string;
  maxCostUsd?: number;
  maxSteps?: number;
  maxRuntimeSec?: number;
  loopWindowSize?: number;
  model?: string;
  apiUrl?: string;
  apiKey?: string;
  logToConsole?: boolean;
}

export class RunManager {
  public readonly agentName: string;
  public readonly runId: string;
  public readonly maxSteps: number;
  public readonly maxRuntimeSec: number;
  public readonly logToConsole: boolean;

  public readonly client: SteerPlaneClient;
  public readonly loopDetector: LoopDetector;
  public readonly costTracker: CostTracker;

  public status: string = "pending";
  public startTime: number = 0;
  public endTime: number = 0;
  public stepCount: number = 0;

  private terminated: boolean = false;
  private terminationReason: string | null = null;

  constructor(opts: RunManagerOptions = {}) {
    this.agentName = opts.agentName ?? "default_agent";
    this.runId = opts.runId ?? generateRunId();
    this.maxSteps = opts.maxSteps ?? 200;
    this.maxRuntimeSec = opts.maxRuntimeSec ?? 3600;
    this.logToConsole = opts.logToConsole ?? true;

    this.client = new SteerPlaneClient(opts.apiUrl, opts.apiKey);
    this.loopDetector = new LoopDetector(opts.loopWindowSize ?? 8);
    this.costTracker = new CostTracker(opts.maxCostUsd ?? 50.0, opts.model ?? "default");
  }

  /** Start the run. Call this before logging any steps. */
  async start(): Promise<void> {
    this.status = "running";
    this.startTime = Date.now() / 1000;

    if (this.logToConsole) {
      console.log(`\n🚀 SteerPlane | Run Started`);
      console.log(`   Run ID:  ${this.runId}`);
      console.log(`   Agent:   ${this.agentName}`);
      console.log(
        `   Limits:  $${this.costTracker.maxCostUsd} cost / ${this.maxSteps} steps`
      );
      console.log(`   ${"─".repeat(45)}`);
    }

    await this.client.startRun(
      this.runId,
      this.agentName,
      this.costTracker.maxCostUsd,
      this.maxSteps
    );
  }

  /**
   * Log a step and run all guard checks.
   *
   * @throws {LoopDetectedError} If a loop pattern is detected.
   * @throws {CostLimitExceeded} If cost exceeds the limit.
   * @throws {StepLimitExceeded} If steps exceed the limit.
   * @throws {RunTerminatedError} If the run was already terminated.
   */
  async logStep(opts: LogStepOptions): Promise<StepCost> {
    if (this.terminated) {
      throw new RunTerminatedError(
        this.runId,
        this.terminationReason ?? "Run terminated"
      );
    }

    // Check step limit
    this.stepCount++;
    if (this.stepCount > this.maxSteps) {
      await this.terminate("step_limit_exceeded");
      throw new StepLimitExceeded(this.stepCount, this.maxSteps);
    }

    // Check runtime limit
    const elapsed = Date.now() / 1000 - this.startTime;
    if (elapsed > this.maxRuntimeSec) {
      await this.terminate("runtime_limit_exceeded");
      throw new RunTerminatedError(
        this.runId,
        `Runtime exceeded: ${formatDuration(elapsed)} > ${formatDuration(this.maxRuntimeSec)}`
      );
    }

    // Calculate cost
    const totalTokens =
      opts.tokens ?? (opts.inputTokens ?? 0) + (opts.outputTokens ?? 0);
    const stepCost = this.costTracker.calculateStepCost({
      inputTokens: opts.inputTokens ?? 0,
      outputTokens: opts.outputTokens ?? 0,
      totalTokens,
      model: opts.model,
      costOverride: opts.cost,
    });

    // Console output
    if (this.logToConsole) {
      const icon = (opts.status ?? "completed") === "completed" ? "✅" : "❌";
      console.log(
        `   ${icon} Step ${this.stepCount}: ${opts.action} ` +
          `| ${totalTokens} tokens | ${formatCost(stepCost.costUsd)} ` +
          `| ${(opts.latencyMs ?? 0).toFixed(0)}ms`
      );
    }

    // Report to API (don't await — fire and forget for performance)
    this.client.logStep({
      runId: this.runId,
      stepNumber: this.stepCount,
      action: opts.action,
      tokens: totalTokens,
      costUsd: stepCost.costUsd,
      latencyMs: opts.latencyMs ?? 0,
      status: opts.status ?? "completed",
      error: opts.error,
      metadata: opts.metadata,
    });

    // === GUARD CHECKS ===

    // 1. Cost limit check
    try {
      this.costTracker.addStep(stepCost);
    } catch (err) {
      if (err instanceof CostLimitExceeded) {
        await this.terminate("cost_limit_exceeded");
      }
      throw err;
    }

    // 2. Loop detection
    const result = this.loopDetector.recordAction(opts.action);
    if (result.loopDetected) {
      await this.terminate("loop_detected");
      throw new LoopDetectedError(result.pattern, result.windowSize);
    }

    return stepCost;
  }

  /** End the run and report final status. */
  async end(status?: string, error?: string): Promise<void> {
    if (["completed", "failed", "terminated"].includes(this.status)) {
      return; // Already ended
    }

    this.endTime = Date.now() / 1000;
    this.status = status ?? (this.terminated ? "terminated" : "completed");
    const duration = this.endTime - this.startTime;

    if (this.logToConsole) {
      console.log(`   ${"─".repeat(45)}`);
      const icons: Record<string, string> = {
        completed: "✅",
        failed: "❌",
        terminated: "⛔",
      };
      const icon = icons[this.status] ?? "⬜";
      console.log(`\n${icon} SteerPlane | Run ${this.status.toUpperCase()}`);
      console.log(`   Run ID:     ${this.runId}`);
      console.log(`   Steps:      ${this.stepCount}`);
      console.log(`   Cost:       ${formatCost(this.costTracker.totalCost)}`);
      console.log(`   Tokens:     ${this.costTracker.totalTokens.toLocaleString()}`);
      console.log(`   Duration:   ${formatDuration(duration)}`);
      if (error) console.log(`   Error:      ${error}`);
      console.log();
    }

    await this.client.endRun(
      this.runId,
      this.status,
      this.costTracker.totalCost,
      this.stepCount,
      error
    );
  }

  /** Get a short summary string. */
  summary(): string {
    const duration = ((this.endTime || Date.now() / 1000) - this.startTime);
    return (
      `${this.stepCount} steps | ` +
      `${formatCost(this.costTracker.totalCost)} | ` +
      `${formatDuration(duration)} | ` +
      `${this.status}`
    );
  }

  private async terminate(reason: string): Promise<void> {
    this.terminated = true;
    this.terminationReason = reason;
    await this.end("terminated", reason);
  }
}
