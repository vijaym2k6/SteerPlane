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
 * Algorithm:
 * 1. Take the last `windowSize` actions
 * 2. For each possible pattern length (1 to window/2):
 *    - Extract the candidate pattern
 *    - Count consecutive repetitions
 *    - If repetitions >= minRepetitions, it's a loop
 *
 * @example
 * detectLoop(['search', 'search', 'search', 'search'], 4) → loop (pattern: ['search'])
 * detectLoop(['A', 'B', 'A', 'B', 'A', 'B'], 6)          → loop (pattern: ['A', 'B'])
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
  const half = Math.floor(window.length / 2);

  for (let patternLen = 1; patternLen <= half; patternLen++) {
    const pattern = window.slice(0, patternLen);

    let reps = 0;
    for (let i = 0; i < window.length; i += patternLen) {
      const chunk = window.slice(i, i + patternLen);
      if (
        chunk.length === pattern.length &&
        chunk.every((v, idx) => v === pattern[idx])
      ) {
        reps++;
      } else {
        break;
      }
    }

    if (reps >= minRepetitions) {
      return {
        loopDetected: true,
        pattern,
        repetitions: reps,
        windowSize,
      };
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
