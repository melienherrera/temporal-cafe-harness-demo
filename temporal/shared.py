"""Shared data types and constants — safe to import inside the workflow sandbox."""
from dataclasses import dataclass

TASK_QUEUE = "brew-espresso"


@dataclass
class BrewOrder:
    """Input to BrewEspressoWorkflow."""
    drink: str = "espresso"
    dose: int = 18          # grams of beans to grind
    water_c: int = 93       # target brew temperature (°C)
    bars: int = 9           # extraction pressure guardrail
    require_approval: bool = True  # human-in-the-loop gate before pulling the shot


@dataclass
class Shot:
    """Result of a pulled shot."""
    volume_ml: int
    seconds: float
