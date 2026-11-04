"""BrewEspressoWorkflow — the durable orchestration.

Mirrors the six steps shown in harness-cafe.html, plus a human-in-the-loop
approval signal before the irreversible "pull the shot" step.

Workflow code must be deterministic: it only orchestrates activities and waits
on signals. All I/O lives in activities.py.
"""
from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from activities import (
        grind_beans,
        heat_water,
        set_pressure,
        lock_portafilter,
        extract_shot,
        log_shot_timer,
    )
    from shared import BrewOrder, Shot


@workflow.defn
class BrewEspressoWorkflow:
    def __init__(self) -> None:
        self._approved = False
        self._stage = "starting"

    # --- Human-in-the-loop: a barista/manager approves before the shot is pulled ---
    @workflow.signal
    def approve(self) -> None:
        """Signal that grants approval to pull the shot."""
        self._approved = True

    @workflow.query
    def stage(self) -> str:
        """Query the current stage — read-only visibility into the run."""
        return self._stage

    @workflow.run
    async def run(self, order: BrewOrder) -> Shot:
        # Tools — what the agent can do
        self._stage = "grinding"
        grounds = await workflow.execute_activity(
            grind_beans, order.dose,
            start_to_close_timeout=timedelta(seconds=8),
        )

        # Context engineering — the right water, the right temp (retries automatically)
        self._stage = "heating"
        water = await workflow.execute_activity(
            heat_water, order.water_c,
            start_to_close_timeout=timedelta(seconds=8),
            retry_policy=RetryPolicy(maximum_attempts=10),
        )

        # Guardrails & policy — never exceed the pressure ceiling
        self._stage = "pressurizing"
        await workflow.execute_activity(
            set_pressure, order.bars,
            start_to_close_timeout=timedelta(seconds=8),
        )

        # Sandboxing — contain the mess
        self._stage = "locking portafilter"
        await workflow.execute_activity(
            lock_portafilter, grounds,
            start_to_close_timeout=timedelta(seconds=8),
        )

        # Human-in-the-loop — durably pause until a human approves the shot.
        # The workflow waits here indefinitely, holding no resources, until the
        # `approve` signal arrives — then resumes exactly where it left off.
        if order.require_approval:
            self._stage = "awaiting approval"
            workflow.logger.info("Waiting for barista approval to pull the shot…")
            await workflow.wait_condition(lambda: self._approved)

        # The model does its work — pull the shot
        self._stage = "extracting"
        shot = await workflow.execute_activity(
            extract_shot, args=[grounds, water],
            start_to_close_timeout=timedelta(seconds=8),
        )

        # Observability — record what happened
        self._stage = "logging"
        await workflow.execute_activity(
            log_shot_timer, shot,
            start_to_close_timeout=timedelta(seconds=8),
        )

        self._stage = "done"
        return shot
