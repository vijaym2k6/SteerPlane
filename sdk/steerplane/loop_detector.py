"""
SteerPlane SDK — Loop Detection Engine

Sliding window pattern detector that identifies repeating action sequences.
Detects patterns like [A, B, A, B, A, B] or [A, A, A, A, A].
"""

from dataclasses import dataclass, field


@dataclass
class LoopDetectionResult:
    """Result of a loop detection check."""
    loop_detected: bool
    pattern: list[str] = field(default_factory=list)
    repetitions: int = 0
    window_size: int = 0


class LoopDetector:
    """
    Sliding window loop detector.
    
    Monitors action history and detects repeating sequences.
    When a loop is detected, the run should be terminated.
    """

    def __init__(self, window_size: int = 8, min_repetitions: int = 2):
        """
        Args:
            window_size: Number of recent actions to analyze.
            min_repetitions: Minimum repetitions to confirm a loop.
        """
        self.window_size = window_size
        self.min_repetitions = min_repetitions
        self.action_history: list[str] = []

    def record_action(self, action: str) -> LoopDetectionResult:
        """
        Record an action and check for loops.
        
        Args:
            action: The action name (e.g., 'search_web', 'call_api').
            
        Returns:
            LoopDetectionResult with detection status and pattern info.
        """
        self.action_history.append(action)
        return self.check()

    def check(self) -> LoopDetectionResult:
        """Check the current action history for loops."""
        if len(self.action_history) < self.window_size:
            return LoopDetectionResult(loop_detected=False)

        return detect_loop(
            self.action_history,
            window_size=self.window_size,
            min_repetitions=self.min_repetitions
        )

    def reset(self):
        """Clear the action history."""
        self.action_history.clear()


def detect_loop(
    history: list[str],
    window_size: int = 8,
    min_repetitions: int = 2
) -> LoopDetectionResult:
    """
    Detect repeating action sequences using a sliding window.
    
    Algorithm:
    1. Take the last `window_size` actions
    2. For each possible pattern length (1 to window/2):
       - Extract the candidate pattern
       - Count how many times it repeats consecutively
       - If repetitions >= min_repetitions, it's a loop
    
    Examples:
        ['search', 'search', 'search', 'search']  → Loop (pattern: ['search'])
        ['A', 'B', 'A', 'B', 'A', 'B']            → Loop (pattern: ['A', 'B'])
        ['A', 'B', 'C', 'D', 'E', 'F']            → No loop
    
    Args:
        history: List of action names.
        window_size: Size of the sliding window to analyze.
        min_repetitions: Minimum consecutive repetitions to flag as loop.
        
    Returns:
        LoopDetectionResult with detection status.
    """
    if len(history) < window_size:
        return LoopDetectionResult(loop_detected=False)

    window = history[-window_size:]
    half = len(window) // 2

    for pattern_len in range(1, half + 1):
        pattern = window[:pattern_len]

        # Count consecutive repetitions of the pattern
        reps = 0
        for i in range(0, len(window), pattern_len):
            chunk = window[i:i + pattern_len]
            if chunk == pattern:
                reps += 1
            else:
                break

        if reps >= min_repetitions:
            return LoopDetectionResult(
                loop_detected=True,
                pattern=pattern,
                repetitions=reps,
                window_size=window_size,
            )

    return LoopDetectionResult(
        loop_detected=False,
        window_size=window_size,
    )
