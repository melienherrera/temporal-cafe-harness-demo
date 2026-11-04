"""Worker — polls the task queue and runs the workflow + activities.

Run:  uv run worker.py
Kill it mid-shot (Ctrl+C) and start it again to watch Temporal replay the
event history and resume from the last completed activity.
"""
import asyncio

from temporalio.worker import Worker

import activities
from connection import get_client
from shared import TASK_QUEUE
from workflows import BrewEspressoWorkflow


async def main() -> None:
    client = await get_client()
    worker = Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[BrewEspressoWorkflow],
        activities=[
            activities.grind_beans,
            activities.heat_water,
            activities.set_pressure,
            activities.lock_portafilter,
            activities.extract_shot,
            activities.log_shot_timer,
        ],
    )
    print(f"Worker running on task queue '{TASK_QUEUE}'. Ctrl+C to stop.")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
