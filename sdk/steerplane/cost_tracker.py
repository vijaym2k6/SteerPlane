"""
SteerPlane SDK — Cost Tracker

Tracks cumulative token usage and cost per run.
Enforces cost limits and projects final cost.
"""

from dataclasses import dataclass, field
from .exceptions import CostLimitExceeded


# Default pricing per token (can be overridden per model)
DEFAULT_PRICING = {
    "gpt-4o": {"input": 0.0000025, "output": 0.000010},
    "gpt-4o-mini": {"input": 0.00000015, "output": 0.0000006},
    "gpt-4": {"input": 0.00003, "output": 0.00006},
    "gpt-3.5-turbo": {"input": 0.0000005, "output": 0.0000015},
    "claude-3-opus": {"input": 0.000015, "output": 0.000075},
    "claude-3-sonnet": {"input": 0.000003, "output": 0.000015},
    "claude-3-haiku": {"input": 0.00000025, "output": 0.00000125},
    "gemini-pro": {"input": 0.00000025, "output": 0.0000005},
    "default": {"input": 0.000002, "output": 0.000002},
}


@dataclass
class StepCost:
    """Cost breakdown for a single step."""
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0
    model: str = "default"


@dataclass
class CostSummary:
    """Cumulative cost summary for an entire run."""
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    step_costs: list[StepCost] = field(default_factory=list)
    projected_final_cost: float = 0.0


class CostTracker:
    """
    Tracks cumulative cost across an agent run.
    
    Enforces cost limits and provides real-time cost projection.
    """

    def __init__(self, max_cost_usd: float = 50.0, model: str = "default"):
        """
        Args:
            max_cost_usd: Maximum allowed cost before termination.
            model: Default model name for pricing lookup.
        """
        self.max_cost_usd = max_cost_usd
        self.model = model
        self.total_cost: float = 0.0
        self.total_tokens: int = 0
        self.total_input_tokens: int = 0
        self.total_output_tokens: int = 0
        self.step_costs: list[StepCost] = []

    def calculate_step_cost(
        self,
        input_tokens: int = 0,
        output_tokens: int = 0,
        total_tokens: int = 0,
        model: str | None = None,
        cost_override: float | None = None,
    ) -> StepCost:
        """
        Calculate cost for a single step.
        
        Args:
            input_tokens: Number of input/prompt tokens.
            output_tokens: Number of output/completion tokens.
            total_tokens: Total tokens (used if input/output not split).
            model: Model name for pricing (overrides default).
            cost_override: Directly specify cost (skips calculation).
            
        Returns:
            StepCost with the calculated cost.
        """
        use_model = model or self.model
        pricing = DEFAULT_PRICING.get(use_model, DEFAULT_PRICING["default"])

        if cost_override is not None:
            cost = cost_override
        elif input_tokens > 0 or output_tokens > 0:
            cost = (input_tokens * pricing["input"]) + (output_tokens * pricing["output"])
            total_tokens = input_tokens + output_tokens
        elif total_tokens > 0:
            # If no split, assume 50/50 input/output
            avg_price = (pricing["input"] + pricing["output"]) / 2
            cost = total_tokens * avg_price
        else:
            cost = 0.0

        step_cost = StepCost(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            cost_usd=cost,
            model=use_model,
        )
        return step_cost

    def add_step(self, step_cost: StepCost) -> float:
        """
        Add a step's cost to the running total and enforce limits.
        
        Args:
            step_cost: The StepCost to add.
            
        Returns:
            The new cumulative cost.
            
        Raises:
            CostLimitExceeded: If cost exceeds the configured limit.
        """
        self.total_cost += step_cost.cost_usd
        self.total_tokens += step_cost.total_tokens
        self.total_input_tokens += step_cost.input_tokens
        self.total_output_tokens += step_cost.output_tokens
        self.step_costs.append(step_cost)

        if self.total_cost > self.max_cost_usd:
            raise CostLimitExceeded(self.total_cost, self.max_cost_usd)

        return self.total_cost

    def project_final_cost(
        self, steps_completed: int, expected_total_steps: int
    ) -> float:
        """
        Project the final cost based on current spending rate.
        
        Args:
            steps_completed: Number of steps completed so far.
            expected_total_steps: Expected total number of steps.
            
        Returns:
            Projected final cost in USD.
        """
        if steps_completed <= 0:
            return 0.0
        projected = self.total_cost * (expected_total_steps / steps_completed)
        return projected

    def get_summary(self) -> CostSummary:
        """Get the current cost summary."""
        return CostSummary(
            total_input_tokens=self.total_input_tokens,
            total_output_tokens=self.total_output_tokens,
            total_tokens=self.total_tokens,
            total_cost_usd=self.total_cost,
            step_costs=list(self.step_costs),
        )

    def reset(self):
        """Reset all tracking."""
        self.total_cost = 0.0
        self.total_tokens = 0
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.step_costs.clear()
