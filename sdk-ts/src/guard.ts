/**
 * Primary TypeScript SDK entrypoints.
 */

import { AsyncLocalStorage } from "node:async_hooks";

import { RunManager } from "./run-manager.js";
import type { PolicyEngineOptions } from "./policy-engine.js";

const activeRunStorage = new AsyncLocalStorage<RunManager>();

/** Get the currently active RunManager (if inside a guarded function). */
export function getActiveRun(): RunManager | null {
  return activeRunStorage.getStore() ?? null;
}

export interface GuardOptions {
  agentName?: string;
  maxCostUsd?: number;
  maxSteps?: number;
  maxRuntimeSec?: number;
  model?: string;
  loopWindowSize?: number;
  logToConsole?: boolean;
  apiUrl?: string;
  apiKey?: string;
  policy?: PolicyEngineOptions;
  enforcement?: "kill" | "alert";
  alertThreshold?: number;
  alertTimeoutSec?: number;
  alertChannels?: string[];
  alertEmail?: string;
  alertWebhookUrl?: string;
}

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
      policy: opts.policy,
      enforcement: opts.enforcement,
      alertThreshold: opts.alertThreshold,
      alertTimeoutSec: opts.alertTimeoutSec,
      alertChannels: opts.alertChannels,
      alertEmail: opts.alertEmail,
      alertWebhookUrl: opts.alertWebhookUrl,
    });

    return activeRunStorage.run(run, async () => {
      try {
        await run.start();
        const result = await fn(...args);
        await run.end("completed");
        return result;
      } catch (err) {
        await run.end("failed", err instanceof Error ? err.message : String(err));
        throw err;
      }
    });
  };
}

export interface SteerPlaneOptions {
  agentId?: string;
  apiUrl?: string;
  apiKey?: string;
  model?: string;
}

export interface RunOptions {
  runId?: string;
  maxCostUsd?: number;
  maxSteps?: number;
  maxRuntimeSec?: number;
  loopWindowSize?: number;
  logToConsole?: boolean;
  policy?: PolicyEngineOptions;
  enforcement?: "kill" | "alert";
  alertThreshold?: number;
  alertTimeoutSec?: number;
  alertChannels?: string[];
  alertEmail?: string;
  alertWebhookUrl?: string;
}

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

  async run<T>(
    fn: (run: RunManager) => Promise<T>,
    opts: RunOptions = {}
  ): Promise<T> {
    const run = this.createRun(opts);

    return activeRunStorage.run(run, async () => {
      await run.start();

      try {
        const result = await fn(run);
        await run.end("completed");
        return result;
      } catch (err) {
        await run.end("failed", err instanceof Error ? err.message : String(err));
        throw err;
      }
    });
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
      policy: opts.policy,
      enforcement: opts.enforcement,
      alertThreshold: opts.alertThreshold,
      alertTimeoutSec: opts.alertTimeoutSec,
      alertChannels: opts.alertChannels,
      alertEmail: opts.alertEmail,
      alertWebhookUrl: opts.alertWebhookUrl,
    });
  }
}
