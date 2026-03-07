/**
 * SteerPlane SDK — Cost Tracker
 *
 * Tracks cumulative token usage and cost per run.
 * Enforces cost limits and provides cost projection.
 */

import { CostLimitExceeded } from "./errors.js";

/** Default pricing per token (can be overridden per model). */
export const DEFAULT_PRICING: Record<
  string,
  { input: number; output: number }
> = {
  "gpt-4o": { input: 0.0000025, output: 0.00001 },
  "gpt-4o-mini": { input: 0.00000015, output: 0.0000006 },
  "gpt-4": { input: 0.00003, output: 0.00006 },
  "gpt-3.5-turbo": { input: 0.0000005, output: 0.0000015 },
  "claude-3-opus": { input: 0.000015, output: 0.000075 },
  "claude-3-sonnet": { input: 0.000003, output: 0.000015 },
  "claude-3-haiku": { input: 0.00000025, output: 0.00000125 },
  "gemini-pro": { input: 0.00000025, output: 0.0000005 },
  default: { input: 0.000002, output: 0.000002 },
};

/** Cost breakdown for a single step. */
export interface StepCost {
  inputTokens: number;
  outputTokens: number;
  totalTokens: number;
  costUsd: number;
  model: string;
}

/** Cumulative cost summary for an entire run. */
export interface CostSummary {
  totalInputTokens: number;
  totalOutputTokens: number;
  totalTokens: number;
  totalCostUsd: number;
  stepCosts: StepCost[];
}

export class CostTracker {
  public readonly maxCostUsd: number;
  public readonly model: string;
  public totalCost: number = 0;
  public totalTokens: number = 0;
  public totalInputTokens: number = 0;
  public totalOutputTokens: number = 0;
  public stepCosts: StepCost[] = [];

  constructor(maxCostUsd: number = 50.0, model: string = "default") {
    this.maxCostUsd = maxCostUsd;
    this.model = model;
  }

  /**
   * Calculate cost for a single step.
   *
   * If `costOverride` is provided, it skips token-based calculation.
   * If `inputTokens`/`outputTokens` are provided, uses per-model pricing.
   * If only `totalTokens` is provided, assumes 50/50 input/output split.
   */
  calculateStepCost(opts: {
    inputTokens?: number;
    outputTokens?: number;
    totalTokens?: number;
    model?: string;
    costOverride?: number;
  }): StepCost {
    const {
      inputTokens = 0,
      outputTokens = 0,
      model: stepModel,
      costOverride,
    } = opts;
    let { totalTokens = 0 } = opts;
    const useModel = stepModel ?? this.model;
    const pricing = DEFAULT_PRICING[useModel] ?? DEFAULT_PRICING["default"];

    let cost: number;

    if (costOverride !== undefined) {
      cost = costOverride;
    } else if (inputTokens > 0 || outputTokens > 0) {
      cost = inputTokens * pricing.input + outputTokens * pricing.output;
      totalTokens = inputTokens + outputTokens;
    } else if (totalTokens > 0) {
      const avgPrice = (pricing.input + pricing.output) / 2;
      cost = totalTokens * avgPrice;
    } else {
      cost = 0;
    }

    return {
      inputTokens,
      outputTokens,
      totalTokens,
      costUsd: cost,
      model: useModel,
    };
  }

  /**
   * Add a step's cost to the running total and enforce limits.
   * @throws {CostLimitExceeded} If cumulative cost exceeds the limit.
   */
  addStep(stepCost: StepCost): number {
    this.totalCost += stepCost.costUsd;
    this.totalTokens += stepCost.totalTokens;
    this.totalInputTokens += stepCost.inputTokens;
    this.totalOutputTokens += stepCost.outputTokens;
    this.stepCosts.push(stepCost);

    if (this.totalCost > this.maxCostUsd) {
      throw new CostLimitExceeded(this.totalCost, this.maxCostUsd);
    }

    return this.totalCost;
  }

  /** Project the final cost based on current spending rate. */
  projectFinalCost(stepsCompleted: number, expectedTotalSteps: number): number {
    if (stepsCompleted <= 0) return 0;
    return this.totalCost * (expectedTotalSteps / stepsCompleted);
  }

  /** Get the current cost summary. */
  getSummary(): CostSummary {
    return {
      totalInputTokens: this.totalInputTokens,
      totalOutputTokens: this.totalOutputTokens,
      totalTokens: this.totalTokens,
      totalCostUsd: this.totalCost,
      stepCosts: [...this.stepCosts],
    };
  }

  /** Reset all tracking. */
  reset(): void {
    this.totalCost = 0;
    this.totalTokens = 0;
    this.totalInputTokens = 0;
    this.totalOutputTokens = 0;
    this.stepCosts = [];
  }
}
