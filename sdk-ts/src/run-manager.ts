/**
 * SteerPlane SDK — Run Manager
 *
 * Orchestrates the full run lifecycle:
 * start → logStep → detectLoop → checkCost → end
 */

import { SteerPlaneClient } from "./client.js";
import { LoopDetector } from "./loop-detector.js";
import { CostTracker, type StepCost } from "./cost-tracker.js";
import { PolicyEngine, type PolicyEngineOptions } from "./policy-engine.js";
import { generateRunId, formatCost, formatDuration } from "./utils.js";
import {
  LoopDetectedError,
  CostLimitExceeded,
  StepLimitExceeded,
  RunTerminatedError,
  PolicyViolationError,
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
  /** Policy engine configuration for action control. */
  policy?: PolicyEngineOptions;
  enforcement?: "kill" | "alert";
  alertThreshold?: number;
  alertTimeoutSec?: number;
  alertChannels?: string[];
  alertEmail?: string;
  alertWebhookUrl?: string;
}

export class RunManager {
  public readonly agentName: string;
  public readonly runId: string;
  public maxSteps: number;
  public maxRuntimeSec: number;
  public readonly logToConsole: boolean;
  public readonly enforcement: "kill" | "alert";
  public readonly alertThreshold: number;
  public readonly alertTimeoutSec: number;
  public readonly alertChannels: string[];
  public readonly alertEmail?: string;
  public readonly alertWebhookUrl?: string;

  public readonly client: SteerPlaneClient;
  public readonly loopDetector: LoopDetector;
  public readonly costTracker: CostTracker;
  public readonly policyEngine: PolicyEngine;

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
    this.enforcement = opts.enforcement ?? "kill";
    this.alertThreshold = Math.min(Math.max(opts.alertThreshold ?? 0.8, 0), 1);
    this.alertTimeoutSec = Math.max(opts.alertTimeoutSec ?? 1800, 1);
    this.alertChannels = [...(opts.alertChannels ?? [])];
    this.alertEmail = opts.alertEmail;
    this.alertWebhookUrl = opts.alertWebhookUrl;

    this.client = new SteerPlaneClient(opts.apiUrl, opts.apiKey);
    this.loopDetector = new LoopDetector(opts.loopWindowSize ?? 8);
    this.costTracker = new CostTracker(opts.maxCostUsd ?? 50.0, opts.model ?? "default");
    this.policyEngine = new PolicyEngine(opts.policy);
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
      if (this.enforcement === "alert") {
        console.log(
          `   Mode:    alert @ ${Math.round(this.alertThreshold * 100)}% (${this.alertTimeoutSec}s timeout)`
        );
      }
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

    // 0. Policy check (before any counters are updated)
    if (this.policyEngine.hasRules) {
      try {
        await this.policyEngine.check(opts.action, opts.metadata);
      } catch (err) {
        if (err instanceof PolicyViolationError) {
          await this.terminate(`policy:${err.rule}`);
        }
        throw err;
      }
    }

    // Check step limit
    this.stepCount++;
    if (this.stepCount > this.maxSteps) {
      if (this.usesAlertMode()) {
        await this.pauseForLimit({
          approvalType: "step_limit",
          action: opts.action,
          currentValue: this.stepCount,
          limitValue: this.maxSteps,
          unit: "steps",
          message:
            `Run '${this.agentName}' hit its step limit ` +
            `(${this.stepCount}/${this.maxSteps}). Approve to extend and continue.`,
          metadata: {
            blocked_action: opts.action,
            current_steps: this.stepCount,
            max_steps: this.maxSteps,
          },
        });
      } else {
        await this.terminate("step_limit_exceeded");
        throw new StepLimitExceeded(this.stepCount, this.maxSteps);
      }
    }

    // Check runtime limit
    const elapsed = Date.now() / 1000 - this.startTime;
    if (elapsed > this.maxRuntimeSec) {
      if (this.usesAlertMode()) {
        await this.pauseForLimit({
          approvalType: "runtime_limit",
          action: opts.action,
          currentValue: elapsed,
          limitValue: this.maxRuntimeSec,
          unit: "seconds",
          message:
            `Run '${this.agentName}' exceeded its runtime limit ` +
            `(${formatDuration(elapsed)} > ${formatDuration(this.maxRuntimeSec)}). ` +
            `Approve to continue or let it terminate.`,
          metadata: {
            blocked_action: opts.action,
            elapsed_seconds: elapsed,
            max_runtime_seconds: this.maxRuntimeSec,
          },
        });
      } else {
        await this.terminate("runtime_limit_exceeded");
        throw new RunTerminatedError(
          this.runId,
          `Runtime exceeded: ${formatDuration(elapsed)} > ${formatDuration(this.maxRuntimeSec)}`
        );
      }
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
        if (this.usesAlertMode()) {
          await this.pauseForLimit({
            approvalType: "cost_limit",
            action: opts.action,
            currentValue: err.currentCost,
            limitValue: err.maxCost,
            unit: "usd",
            message:
              `Run '${this.agentName}' exceeded its cost limit ` +
              `($${err.currentCost.toFixed(4)} > $${err.maxCost.toFixed(2)}). ` +
              `Approve to extend and continue or let it terminate.`,
            metadata: {
              blocked_action: opts.action,
              current_cost: err.currentCost,
              max_cost: err.maxCost,
              step_number: this.stepCount,
            },
          });
        } else {
          await this.terminate("cost_limit_exceeded");
          throw err;
        }
      }
    }

    // 2. Loop detection
    const result = this.loopDetector.recordAction(opts.action);
    if (result.loopDetected) {
      await this.terminate("loop_detected");
      throw new LoopDetectedError(result.pattern, result.windowSize);
    }

    await this.checkAlertThresholds(opts.action);

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

  private usesAlertMode(): boolean {
    return this.enforcement === "alert";
  }

  private async checkAlertThresholds(action: string): Promise<void> {
    if (!this.usesAlertMode()) {
      return;
    }

    if (
      this.costTracker.maxCostUsd > 0 &&
      this.costTracker.totalCost >= this.costTracker.maxCostUsd * this.alertThreshold
    ) {
      await this.pauseForLimit({
        approvalType: "cost_limit",
        action,
        currentValue: this.costTracker.totalCost,
        limitValue: this.costTracker.maxCostUsd,
        unit: "usd",
        message:
          `Run '${this.agentName}' has crossed ${Math.round(this.alertThreshold * 100)}% ` +
          `of its cost budget ($${this.costTracker.totalCost.toFixed(4)}/$${this.costTracker.maxCostUsd.toFixed(2)}). ` +
          `Approve to continue or let it terminate on timeout.`,
        metadata: {
          blocked_action: action,
          current_cost: this.costTracker.totalCost,
          max_cost: this.costTracker.maxCostUsd,
          step_number: this.stepCount,
          threshold: this.alertThreshold,
        },
      });
      return;
    }

    const elapsed = Date.now() / 1000 - this.startTime;
    if (
      this.maxRuntimeSec > 0 &&
      elapsed >= this.maxRuntimeSec * this.alertThreshold
    ) {
      await this.pauseForLimit({
        approvalType: "runtime_limit",
        action,
        currentValue: elapsed,
        limitValue: this.maxRuntimeSec,
        unit: "seconds",
        message:
          `Run '${this.agentName}' has crossed ${Math.round(this.alertThreshold * 100)}% ` +
          `of its runtime budget (${formatDuration(elapsed)}/${formatDuration(this.maxRuntimeSec)}). ` +
          `Approve to continue or let it terminate on timeout.`,
        metadata: {
          blocked_action: action,
          elapsed_seconds: elapsed,
          max_runtime_seconds: this.maxRuntimeSec,
          step_number: this.stepCount,
          threshold: this.alertThreshold,
        },
      });
      return;
    }

    if (
      this.maxSteps > 0 &&
      this.stepCount >= this.maxSteps * this.alertThreshold
    ) {
      await this.pauseForLimit({
        approvalType: "step_limit",
        action,
        currentValue: this.stepCount,
        limitValue: this.maxSteps,
        unit: "steps",
        message:
          `Run '${this.agentName}' has crossed ${Math.round(this.alertThreshold * 100)}% ` +
          `of its step budget (${this.stepCount}/${this.maxSteps}). ` +
          `Approve to continue or let it terminate on timeout.`,
        metadata: {
          blocked_action: action,
          current_steps: this.stepCount,
          max_steps: this.maxSteps,
          step_number: this.stepCount,
          threshold: this.alertThreshold,
        },
      });
    }
  }

  private async pauseForLimit(opts: {
    approvalType: string;
    action: string;
    currentValue: number;
    limitValue: number;
    unit: string;
    message: string;
    metadata?: Record<string, unknown>;
  }): Promise<void> {
    if (!this.client.isConnected) {
      await this.terminate("alert_mode_unavailable");
      throw new RunTerminatedError(
        this.runId,
        "Alert mode requires a reachable SteerPlane API but the API is offline"
      );
    }

    const approval = await this.client.requestApproval({
      run_id: this.runId,
      agent_name: this.agentName,
      approval_type: opts.approvalType,
      current_value: opts.currentValue,
      limit_value: opts.limitValue,
      unit: opts.unit,
      message: opts.message,
      timeout_sec: this.alertTimeoutSec,
      channels: this.alertChannels,
      alert_email: this.alertEmail ?? null,
      alert_webhook_url: this.alertWebhookUrl ?? null,
      metadata: opts.metadata ?? {},
    });

    if (!approval || typeof approval.id !== "string") {
      await this.terminate("approval_request_failed");
      throw new RunTerminatedError(
        this.runId,
        "Could not create a SteerPlane approval request"
      );
    }

    this.status = "awaiting_approval";

    if (this.logToConsole) {
      console.log(
        `   🔔 Approval requested for ${opts.approvalType.replace(/_/g, " ")} ` +
          `(${opts.currentValue.toFixed(4)} ${opts.unit} / ${opts.limitValue.toFixed(4)} ${opts.unit})`
      );
      console.log(`      Waiting up to ${this.alertTimeoutSec}s for continue/kill...`);
    }

    const deadline = Date.now() + (this.alertTimeoutSec + 1) * 1000;
    while (Date.now() <= deadline) {
      await new Promise((resolve) => setTimeout(resolve, 5000));
      const latest = await this.client.getApproval(approval.id);
      if (!latest || typeof latest.status !== "string") {
        continue;
      }

      const latestStatus = latest.status.toLowerCase();
      if (latestStatus === "pending") {
        continue;
      }

      if (latestStatus === "approved") {
        this.applyApprovalResolution(
          opts.approvalType,
          (latest.resolution_json ?? {}) as Record<string, unknown>
        );
        this.status = "running";
        return;
      }

      const resolution =
        (latest.resolution_json ?? null) as Record<string, unknown> | null;
      const message =
        latest.resolution_note ??
        (typeof resolution?.reason === "string" ? resolution.reason : null) ??
        latest.message ??
        `Approval ${latestStatus}`;
      await this.terminate(latestStatus === "denied" ? "approval_denied" : "alert_timeout");
      throw new RunTerminatedError(this.runId, String(message));
    }

    await this.terminate("alert_timeout");
    throw new RunTerminatedError(
      this.runId,
      `Approval timed out while waiting for ${opts.approvalType.replace(/_/g, " ")} continuation`
    );
  }

  private applyApprovalResolution(
    approvalType: string,
    resolution: Record<string, unknown>
  ): void {
    const nextLimit = typeof resolution.new_limit === "number"
      ? resolution.new_limit
      : null;
    if (nextLimit === null) {
      return;
    }

    if (approvalType === "cost_limit") {
      this.costTracker.maxCostUsd = nextLimit;
    } else if (approvalType === "step_limit") {
      this.maxSteps = Math.trunc(nextLimit);
    } else if (approvalType === "runtime_limit") {
      this.maxRuntimeSec = Math.trunc(nextLimit);
    }
  }
}
