/**
 * SteerPlane SDK — Loop Detection Engine
 *
 * Sliding window pattern detector that identifies repeating action sequences.
 * Detects patterns like [A, B, A, B, A, B] or [A, A, A, A, A].
 */

export interface LoopDetectionResult {
  loopDetected: boolean;
  pattern: string[];
  repetitions: number;
  windowSize: number;
}

/**
 * Detect repeating action sequences using a sliding window.
 *
 * The check is anchored at the *end* of the window (matching the Python SDK), so
 * a loop that starts partway through the window (e.g. [X, A, B, A, B, A, B]) is
 * still detected.
 *
 * Algorithm:
 * 1. Take the last `windowSize` actions.
 * 2. For each candidate pattern length (1 .. window / minRepetitions):
 *    - Take the trailing `patternLen` actions as the candidate pattern.
 *    - Walk backwards counting consecutive repetitions from the end.
 *    - If repetitions >= the required count, it's a loop (smallest unit wins).
 *
 * Single-action loops (pattern length 1) require >= 3 consecutive repetitions —
 * a benign double-call should not terminate a run. Multi-step patterns use
 * `minRepetitions`.
 *
 * @example
 * detectLoop(['search', 'search', 'search'], 3)  → loop (pattern: ['search'])
 * detectLoop(['A', 'B', 'A', 'B', 'A', 'B'], 6)  → loop (pattern: ['A', 'B'])
 */
export function detectLoop(
  history: string[],
  windowSize: number = 8,
  minRepetitions: number = 2
): LoopDetectionResult {
  if (history.length < windowSize) {
    return { loopDetected: false, pattern: [], repetitions: 0, windowSize };
  }

  const window = history.slice(-windowSize);
  const n = window.length;
  const maxPatternLen = Math.max(1, Math.floor(n / minRepetitions));

  const equal = (a: string[], b: string[]): boolean =>
    a.length === b.length && a.every((v, idx) => v === b[idx]);

  for (let patternLen = 1; patternLen <= maxPatternLen; patternLen++) {
    const pattern = window.slice(n - patternLen, n);

    let reps = 0;
    let idx = n;
    while (idx - patternLen >= 0 && equal(window.slice(idx - patternLen, idx), pattern)) {
      reps++;
      idx -= patternLen;
    }

    // Single-action loops need a higher floor (>=3); multi-step use minRepetitions.
    const required = patternLen > 1 ? minRepetitions : Math.max(minRepetitions, 3);
    if (reps >= required) {
      return { loopDetected: true, pattern, repetitions: reps, windowSize };
    }
  }

  return { loopDetected: false, pattern: [], repetitions: 0, windowSize };
}

export class LoopDetector {
  private readonly windowSize: number;
  private readonly minRepetitions: number;
  private actionHistory: string[] = [];

  constructor(windowSize: number = 8, minRepetitions: number = 2) {
    this.windowSize = windowSize;
    this.minRepetitions = minRepetitions;
  }

  /** Record an action and check for loops. */
  recordAction(action: string): LoopDetectionResult {
    this.actionHistory.push(action);
    return this.check();
  }

  /** Check the current action history for loops. */
  check(): LoopDetectionResult {
    if (this.actionHistory.length < this.windowSize) {
      return {
        loopDetected: false,
        pattern: [],
        repetitions: 0,
        windowSize: this.windowSize,
      };
    }
    return detectLoop(
      this.actionHistory,
      this.windowSize,
      this.minRepetitions
    );
  }

  /** Clear the action history. */
  reset(): void {
    this.actionHistory = [];
  }
}
