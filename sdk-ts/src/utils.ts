/**
 * SteerPlane SDK — Utility Functions
 */

import { randomUUID } from "node:crypto";

/** Generate a unique run ID. */
export function generateRunId(): string {
  return randomUUID();
}

/** Format a cost value as a human-readable USD string. */
export function formatCost(cost: number): string {
  if (cost < 0.01) {
    return `$${cost.toFixed(4)}`;
  }
  return `$${cost.toFixed(2)}`;
}

/** Format a duration in seconds as a human-readable string. */
export function formatDuration(seconds: number): string {
  if (seconds < 1) {
    return `${(seconds * 1000).toFixed(0)}ms`;
  }
  if (seconds < 60) {
    return `${seconds.toFixed(1)}s`;
  }
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}m ${secs.toFixed(0)}s`;
}
