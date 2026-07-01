"""Tests for the loop detection engine."""

from steerplane.loop_detector import detect_loop, LoopDetector


class TestDetectLoop:
    """Tests for the detect_loop function."""

    def test_simple_repeat_detected(self):
        """A,A,A,A,A,A should be detected as a loop."""
        history = ["search", "search", "search", "search", "search", "search"]
        result = detect_loop(history, window_size=6)
        assert result.loop_detected is True
        assert result.pattern == ["search"]

    def test_alternating_pattern_detected(self):
        """A,B,A,B,A,B should be detected as a loop."""
        history = ["A", "B", "A", "B", "A", "B"]
        result = detect_loop(history, window_size=6)
        assert result.loop_detected is True
        assert result.pattern == ["A", "B"]

    def test_triple_pattern_detected(self):
        """A,B,C,A,B,C should be detected as a loop."""
        history = ["A", "B", "C", "A", "B", "C"]
        result = detect_loop(history, window_size=6)
        assert result.loop_detected is True
        assert result.pattern == ["A", "B", "C"]

    def test_no_loop_unique_actions(self):
        """All unique actions should not be a loop."""
        history = ["A", "B", "C", "D", "E", "F"]
        result = detect_loop(history, window_size=6)
        assert result.loop_detected is False

    def test_no_loop_short_history(self):
        """History shorter than window should not trigger."""
        history = ["A", "B"]
        result = detect_loop(history, window_size=6)
        assert result.loop_detected is False

    def test_window_only_checks_recent(self):
        """Only the last window_size actions should be checked."""
        history = ["X", "Y", "Z", "A", "A", "A", "A", "A", "A"]
        result = detect_loop(history, window_size=6)
        assert result.loop_detected is True
        assert result.pattern == ["A"]

    def test_empty_history(self):
        """Empty history should not crash."""
        result = detect_loop([], window_size=6)
        assert result.loop_detected is False

    def test_real_world_search_loop(self):
        """Simulate a real search loop scenario."""
        history = [
            "query_db",
            "call_llm",
            "search_web",
            "search_web",
            "search_web",
            "search_web",
            "search_web",
            "search_web",
        ]
        result = detect_loop(history, window_size=6)
        assert result.loop_detected is True

    def test_phase_shifted_loop_detected(self):
        """A loop that starts partway through the window is still detected.

        ['X', 'A', 'B', 'A', 'B', 'A', 'B', 'A'] — the A/B cycle is offset by the
        leading 'X', so anchoring at the window start would miss it.
        """
        history = ["X", "A", "B", "A", "B", "A", "B", "A"]
        result = detect_loop(history, window_size=8)
        assert result.loop_detected is True
        assert result.repetitions >= 2

    def test_no_loop_with_trailing_noise(self):
        """A repeating prefix followed by fresh distinct actions is NOT a loop.

        The agent has moved on, so the tail is not repeating.
        """
        history = ["A", "B", "A", "B", "A", "B", "C", "D"]
        result = detect_loop(history, window_size=8)
        assert result.loop_detected is False

    def test_single_action_two_reps_not_a_loop(self):
        """Two identical actions in a row (a benign double-call) is NOT a loop."""
        history = ["a", "b", "c", "d", "e", "f", "g", "g"]
        result = detect_loop(history, window_size=8)
        assert result.loop_detected is False

    def test_single_action_three_reps_is_a_loop(self):
        """Three identical actions in a row crosses the single-action floor."""
        history = ["a", "b", "c", "d", "e", "g", "g", "g"]
        result = detect_loop(history, window_size=8)
        assert result.loop_detected is True
        assert result.pattern == ["g"]
        assert result.repetitions == 3

    def test_multi_step_two_reps_still_triggers(self):
        """The >=3 floor is single-action only; a 2-step cycle still trips at 2."""
        history = ["x", "y", "z", "w", "A", "B", "A", "B"]
        result = detect_loop(history, window_size=8)
        assert result.loop_detected is True
        assert result.pattern == ["A", "B"]


class TestLoopDetector:
    """Tests for the LoopDetector class."""

    def test_incremental_detection(self):
        """Should detect loop as actions are added one by one."""
        detector = LoopDetector(window_size=4, min_repetitions=2)

        # Not enough data yet
        assert detector.record_action("A").loop_detected is False
        assert detector.record_action("B").loop_detected is False
        assert detector.record_action("A").loop_detected is False

        # Now we have 4 actions: A, B, A, B - should detect
        result = detector.record_action("B")
        assert result.loop_detected is True

    def test_reset_clears_history(self):
        """Reset should clear all recorded actions."""
        detector = LoopDetector(window_size=4)
        detector.record_action("A")
        detector.record_action("A")
        detector.reset()
        assert len(detector.action_history) == 0

    def test_action_history_preserved(self):
        """All recorded actions should be accessible."""
        detector = LoopDetector(window_size=6)
        detector.record_action("search")
        detector.record_action("query")
        assert detector.action_history == ["search", "query"]
