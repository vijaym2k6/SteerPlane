/**
 * SteerPlane SDK — Custom Error Classes
 *
 * All errors raised by the SteerPlane guard system.
 */

export class SteerPlaneError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "SteerPlaneError";
  }
}

export class LoopDetectedError extends SteerPlaneError {
  public readonly pattern: string[];
  public readonly windowSize: number;

  constructor(pattern: string[], windowSize: number) {
    super(
      `🔄 Loop detected! Repeating pattern [${pattern.join(", ")}] ` +
        `found in last ${windowSize} actions. Run terminated.`
    );
    this.name = "LoopDetectedError";
    this.pattern = pattern;
    this.windowSize = windowSize;
  }
}

export class CostLimitExceeded extends SteerPlaneError {
  public readonly currentCost: number;
  public readonly maxCost: number;

  constructor(currentCost: number, maxCost: number) {
    super(
      `💰 Cost limit exceeded! Current: $${currentCost.toFixed(4)}, ` +
        `Limit: $${maxCost.toFixed(2)}. Run terminated.`
    );
    this.name = "CostLimitExceeded";
    this.currentCost = currentCost;
    this.maxCost = maxCost;
  }
}

export class StepLimitExceeded extends SteerPlaneError {
  public readonly currentSteps: number;
  public readonly maxSteps: number;

  constructor(currentSteps: number, maxSteps: number) {
    super(
      `🚫 Step limit exceeded! Steps: ${currentSteps}, ` +
        `Limit: ${maxSteps}. Run terminated.`
    );
    this.name = "StepLimitExceeded";
    this.currentSteps = currentSteps;
    this.maxSteps = maxSteps;
  }
}

export class RunTerminatedError extends SteerPlaneError {
  public readonly runId: string;
  public readonly reason: string;

  constructor(runId: string, reason: string = "Manual termination") {
    super(`⛔ Run ${runId} terminated. Reason: ${reason}`);
    this.name = "RunTerminatedError";
    this.runId = runId;
    this.reason = reason;
  }
}

export class APIConnectionError extends SteerPlaneError {
  public readonly url: string;
  public readonly detail: string;

  constructor(url: string, detail: string = "") {
    super(`🔌 Cannot connect to SteerPlane API at ${url}. ${detail}`);
    this.name = "APIConnectionError";
    this.url = url;
    this.detail = detail;
  }
}
