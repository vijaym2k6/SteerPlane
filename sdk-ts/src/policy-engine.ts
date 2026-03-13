/**
 * SteerPlane SDK — Policy Engine (TypeScript)
 *
 * Rule-based action control for agent runs.
 * Supports allow/deny lists (with glob patterns), per-action rate limiting,
 * and human-in-the-loop approval workflows.
 */

import { PolicyViolationError } from "./errors.js";

/** Result of a policy check. */
export interface PolicyDecision {
  allowed: boolean;
  action: string;
  /** Which rule matched (e.g. "deny:delete_*"). */
  rule: string;
  /** Human-readable explanation. */
  reason: string;
}

/** Rate limit specification for an action pattern. */
export interface RateLimitSpec {
  /** Glob pattern to match against action names. */
  pattern: string;
  /** Maximum number of calls allowed within the window. */
  maxCount: number;
  /** Sliding window duration in seconds. */
  windowSeconds: number;
}

/** Approval callback type. Return true to allow, false to deny. */
export type ApprovalCallback = (
  action: string,
  metadata?: Record<string, unknown>
) => boolean | Promise<boolean>;

/** Options to construct a PolicyEngine. */
export interface PolicyEngineOptions {
  /** Glob patterns for permitted actions. If empty, all are permitted (unless denied). */
  allowedActions?: string[];
  /** Glob patterns for forbidden actions. */
  deniedActions?: string[];
  /** Per-action rate limits. */
  rateLimits?: RateLimitSpec[];
  /** Glob patterns requiring human approval before execution. */
  requireApproval?: string[];
  /** Callback invoked when an action requires approval. */
  approvalCallback?: ApprovalCallback;
}

/**
 * Evaluates incoming actions against a set of policy rules.
 *
 * Rules are checked in order:
 *   1. Deny list (block immediately)
 *   2. Allow list (if non-empty, action must match at least one pattern)
 *   3. Rate limits (sliding-window counters per action pattern)
 *   4. Approval workflow (calls callback; block if denied or no callback)
 */
export class PolicyEngine {
  public readonly allowedActions: string[];
  public readonly deniedActions: string[];
  public readonly rateLimits: RateLimitSpec[];
  public readonly requireApproval: string[];
  public approvalCallback?: ApprovalCallback;

  private readonly _rateWindows: Map<string, number[]> = new Map();

  constructor(opts: PolicyEngineOptions = {}) {
    this.allowedActions = opts.allowedActions ?? [];
    this.deniedActions = opts.deniedActions ?? [];
    this.rateLimits = opts.rateLimits ?? [];
    this.requireApproval = opts.requireApproval ?? [];
    this.approvalCallback = opts.approvalCallback;

    // Initialise sliding-window arrays
    for (const rl of this.rateLimits) {
      this._rateWindows.set(rl.pattern, []);
    }
  }

  /**
   * Evaluate *action* against all policy rules.
   *
   * Returns a `PolicyDecision` on success.
   * Throws `PolicyViolationError` if the action is denied.
   */
  async check(
    action: string,
    metadata?: Record<string, unknown>
  ): Promise<PolicyDecision> {
    // 1. Deny list — checked first, always wins
    for (const pattern of this.deniedActions) {
      if (globMatch(action, pattern)) {
        PolicyEngine._deny(
          action,
          `deny:${pattern}`,
          `Action '${action}' matches deny pattern '${pattern}'`
        );
      }
    }

    // 2. Allow list — if non-empty, action MUST match at least one entry
    if (this.allowedActions.length > 0) {
      if (!this.allowedActions.some((p) => globMatch(action, p))) {
        PolicyEngine._deny(
          action,
          "allow_list",
          `Action '${action}' is not in the allow list`
        );
      }
    }

    // 3. Rate limits
    const now = performance.now() / 1000; // seconds (monotonic-like)
    for (const rl of this.rateLimits) {
      if (globMatch(action, rl.pattern)) {
        const window = this._rateWindows.get(rl.pattern)!;
        // Prune expired timestamps
        const cutoff = now - rl.windowSeconds;
        const pruned = window.filter((t) => t > cutoff);
        this._rateWindows.set(rl.pattern, pruned);

        if (pruned.length >= rl.maxCount) {
          PolicyEngine._deny(
            action,
            `rate_limit:${rl.pattern}`,
            `Rate limit exceeded for '${action}': ` +
              `${rl.maxCount} calls per ${rl.windowSeconds}s`
          );
        }
        // Record this call
        pruned.push(now);
      }
    }

    // 4. Approval workflow
    for (const pattern of this.requireApproval) {
      if (globMatch(action, pattern)) {
        if (!this.approvalCallback) {
          PolicyEngine._deny(
            action,
            `approval:${pattern}`,
            `Action '${action}' requires approval but no callback is set`
          );
        } else {
          const approved = await this.approvalCallback(action, metadata);
          if (!approved) {
            PolicyEngine._deny(
              action,
              `approval:${pattern}`,
              `Action '${action}' was denied by the approval callback`
            );
          }
        }
      }
    }

    return { allowed: true, action, rule: "", reason: "" };
  }

  /** True if at least one rule is configured. */
  get hasRules(): boolean {
    return (
      this.allowedActions.length > 0 ||
      this.deniedActions.length > 0 ||
      this.rateLimits.length > 0 ||
      this.requireApproval.length > 0
    );
  }

  /** Throw PolicyViolationError. */
  private static _deny(action: string, rule: string, reason: string): never {
    throw new PolicyViolationError(action, rule, reason);
  }
}

// ────────────────── Glob matching (minimal fnmatch) ──────────────────

/**
 * Simple glob match implementation supporting `*` and `?` wildcards.
 * Mirrors Python's `fnmatch.fnmatch` behaviour.
 */
export function globMatch(text: string, pattern: string): boolean {
  // Convert glob pattern to regex
  let regex = "^";
  for (const ch of pattern) {
    switch (ch) {
      case "*":
        regex += ".*";
        break;
      case "?":
        regex += ".";
        break;
      case ".":
      case "+":
      case "^":
      case "$":
      case "(":
      case ")":
      case "{":
      case "}":
      case "[":
      case "]":
      case "|":
      case "\\":
        regex += `\\${ch}`;
        break;
      default:
        regex += ch;
    }
  }
  regex += "$";
  return new RegExp(regex, "i").test(text);
}
