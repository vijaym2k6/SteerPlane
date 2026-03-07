/**
 * SteerPlane SDK — Guard & SteerPlane Class
 *
 * The primary developer-facing API.
 *
 * Usage (HOF):
 *   import { guard } from 'steerplane';
 *   const runAgent = guard(async () => { ... }, { maxCostUsd: 10 });
 *   await runAgent();
 *
 * Usage (Class):
 *   import { SteerPlane } from 'steerplane';
 *   const sp = new SteerPlane({ agentId: 'my_bot' });
 *   await sp.run(async (run) => { ... }, { maxCostUsd: 10 });
 */

import { RunManager, type RunManagerOptions } from "./run-manager.js";

// Global active run reference
let _activeRun: RunManager | null = null;

/** Get the currently active RunManager (if inside a guarded function). */
export function getActiveRun(): RunManager | null {
  return _activeRun;
}

/** Options for the guard() higher-order function. */
export interface GuardOptions {
  /** Agent name shown in dashboard. */
  agentName?: string;
  /** Maximum cost per run in USD. */
  maxCostUsd?: number;
  /** Maximum number of steps per run. */
  maxSteps?: number;
  /** Maximum runtime in seconds. */
  maxRuntimeSec?: number;
  /** Default model for cost calculation. */
  model?: string;
  /** Window size for loop detection. */
  loopWindowSize?: number;
  /** Whether to print step logs to console. */
  logToConsole?: boolean;
  /** SteerPlane API URL. */
  apiUrl?: string;
  /** API key. */
  apiKey?: string;
}

/**
 * Guard higher-order function.
 *
 * Wraps an async agent function with SteerPlane's guard system:
 * - Loop detection (sliding window)
 * - Cost limit enforcement
 * - Step limit enforcement
 * - Runtime limit enforcement
 * - Full telemetry logging
 *
 * @param fn - The async function to guard.
 * @param opts - Guard configuration options.
 * @returns A new async function that runs `fn` inside a SteerPlane guard.
 *
 * @example
 * ```typescript
 * const runAgent = guard(
 *   async () => { await agent.run(); },
 *   { agentName: 'my_bot', maxCostUsd: 10, maxSteps: 50 }
 * );
 * await runAgent();
 * ```
 */
export function guard<TArgs extends unknown[], TResult>(
  fn: (...args: TArgs) => Promise<TResult>,
  opts: GuardOptions = {}
): (...args: TArgs) => Promise<TResult> {
  return async (...args: TArgs): Promise<TResult> => {
    const run = new RunManager({
      agentName: opts.agentName ?? fn.name ?? "guarded_agent",
      maxCostUsd: opts.maxCostUsd,
      maxSteps: opts.maxSteps,
      maxRuntimeSec: opts.maxRuntimeSec,
      loopWindowSize: opts.loopWindowSize,
      model: opts.model,
      apiUrl: opts.apiUrl,
      apiKey: opts.apiKey,
      logToConsole: opts.logToConsole,
    });

    _activeRun = run;

    try {
      await run.start();
      const result = await fn(...args);
      await run.end("completed");
      return result;
    } catch (err) {
      await run.end("failed", err instanceof Error ? err.message : String(err));
      throw err;
    } finally {
      _activeRun = null;
    }
  };
}

/** Options for SteerPlane constructor. */
export interface SteerPlaneOptions {
  /** Agent identifier. */
  agentId?: string;
  /** SteerPlane API URL. */
  apiUrl?: string;
  /** API key. */
  apiKey?: string;
  /** Default model for cost calculation. */
  model?: string;
}

/** Options for SteerPlane.run(). */
export interface RunOptions {
  runId?: string;
  maxCostUsd?: number;
  maxSteps?: number;
  maxRuntimeSec?: number;
  loopWindowSize?: number;
  logToConsole?: boolean;
}

/**
 * Main SDK entry point for programmatic usage.
 *
 * @example
 * ```typescript
 * const sp = new SteerPlane({ agentId: 'my_bot' });
 *
 * // Callback style
 * await sp.run(async (run) => {
 *   await run.logStep({ action: 'query_db', tokens: 380, cost: 0.002 });
 * }, { maxCostUsd: 10 });
 *
 * // Manual style
 * const run = sp.createRun({ maxCostUsd: 10 });
 * await run.start();
 * await run.logStep({ action: 'search', tokens: 100 });
 * await run.end();
 * ```
 */
export class SteerPlane {
  private readonly agentId: string;
  private readonly apiUrl?: string;
  private readonly apiKey?: string;
  private readonly model: string;

  constructor(opts: SteerPlaneOptions = {}) {
    this.agentId = opts.agentId ?? "default_agent";
    this.apiUrl = opts.apiUrl;
    this.apiKey = opts.apiKey;
    this.model = opts.model ?? "default";
  }

  /**
   * Run an agent function inside a SteerPlane guard.
   *
   * The RunManager is automatically started and ended.
   * If the callback throws, the run is marked as failed.
   */
  async run<T>(
    fn: (run: RunManager) => Promise<T>,
    opts: RunOptions = {}
  ): Promise<T> {
    const run = this.createRun(opts);
    await run.start();

    try {
      const result = await fn(run);
      await run.end("completed");
      return result;
    } catch (err) {
      await run.end("failed", err instanceof Error ? err.message : String(err));
      throw err;
    }
  }

  /** Create a RunManager without starting it (for manual lifecycle management). */
  createRun(opts: RunOptions = {}): RunManager {
    return new RunManager({
      agentName: this.agentId,
      runId: opts.runId,
      maxCostUsd: opts.maxCostUsd,
      maxSteps: opts.maxSteps,
      maxRuntimeSec: opts.maxRuntimeSec,
      loopWindowSize: opts.loopWindowSize,
      model: this.model,
      apiUrl: this.apiUrl,
      apiKey: this.apiKey,
      logToConsole: opts.logToConsole,
    });
  }
}
