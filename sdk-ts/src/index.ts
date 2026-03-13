/**
 * SteerPlane SDK (TypeScript)
 *
 * Runtime control plane for autonomous AI agents.
 * "Agents don't fail in the dark anymore."
 *
 * @example HOF Style
 * ```typescript
 * import { guard } from 'steerplane';
 *
 * const runAgent = guard(async () => {
 *   await agent.run();
 * }, { maxCostUsd: 10, maxSteps: 50 });
 *
 * await runAgent();
 * ```
 *
 * @example Class Style
 * ```typescript
 * import { SteerPlane } from 'steerplane';
 *
 * const sp = new SteerPlane({ agentId: 'my_bot' });
 * await sp.run(async (run) => {
 *   await run.logStep({ action: 'query_db', tokens: 380, cost: 0.002 });
 * }, { maxCostUsd: 10 });
 * ```
 *
 * @packageDocumentation
 */

export const VERSION = "0.1.0";

// Main APIs
export { guard, SteerPlane, getActiveRun } from "./guard.js";
export type { GuardOptions, SteerPlaneOptions, RunOptions } from "./guard.js";

// Core classes
export { RunManager } from "./run-manager.js";
export type { RunManagerOptions, LogStepOptions } from "./run-manager.js";

export { LoopDetector, detectLoop } from "./loop-detector.js";
export type { LoopDetectionResult } from "./loop-detector.js";

export { CostTracker, DEFAULT_PRICING } from "./cost-tracker.js";
export type { StepCost, CostSummary } from "./cost-tracker.js";

export { PolicyEngine, globMatch } from "./policy-engine.js";
export type {
  PolicyDecision,
  RateLimitSpec,
  ApprovalCallback,
  PolicyEngineOptions,
} from "./policy-engine.js";

export { SteerPlaneClient } from "./client.js";

// Utilities
export { generateRunId, formatCost, formatDuration } from "./utils.js";

// Errors
export {
  SteerPlaneError,
  LoopDetectedError,
  CostLimitExceeded,
  StepLimitExceeded,
  RunTerminatedError,
  APIConnectionError,
  PolicyViolationError,
} from "./errors.js";
