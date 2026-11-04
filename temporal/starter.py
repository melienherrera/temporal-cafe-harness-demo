"""Starter — kicks off one BrewEspressoWorkflow and reports the result.

Run:  uv run starter.py

By default it auto-sends the barista approval after a few seconds so the shot
completes end-to-end. To demonstrate the durable human-in-the-loop pause,
set AUTO_APPROVE=false and send the signal yourself:

    AUTO_APPROVE=false uv run starter.py
    temporal workflow signal --workflow-id <id> --name approve
"""
import asyncio
import os
import uuid

from connection import get_client
from shared import BrewOrder, TASK_QUEUE
from workflows import BrewEspressoWorkflow


async def main() -> None:
    client = await get_client()
    wf_id = f"brew-espresso-{uuid.uuid4().hex[:8]}"

    handle = await client.start_workflow(
        BrewEspressoWorkflow.run,
        BrewOrder(),
        id=wf_id,
        task_queue=TASK_QUEUE,
    )
    print(f"Started workflow: {wf_id}")
    print(f"Watch it live:    http://localhost:8233/namespaces/default/workflows/{wf_id}")

    auto_approve = os.environ.get("AUTO_APPROVE", "true").lower() != "false"
    if auto_approve:
        await asyncio.sleep(5)  # let it reach the approval gate
        print("Sending barista approval signal…")
        await handle.signal(BrewEspressoWorkflow.approve)
    else:
        print("\nApproval NOT auto-sent — the workflow is durably paused. Approve with:")
        print(f"  temporal workflow signal --workflow-id {wf_id} --name approve\n")

    shot = await handle.result()
    print(f"☕ Shot pulled: {shot.volume_ml}ml in {shot.seconds}s")


if __name__ == "__main__":
    asyncio.run(main())
