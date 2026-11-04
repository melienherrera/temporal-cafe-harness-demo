"""FastAPI backend — serves the frontend and bridges it to real Temporal.

The frontend (../harness-cafe.html) calls these endpoints when it's served from
here; opened as a standalone file it falls back to its built-in simulation.

Endpoints:
  GET  /                        serve the frontend
  GET  /api/health              liveness check (frontend uses this to go "live")
  POST /api/brew                start a real BrewEspressoWorkflow
  GET  /api/brew/{id}/events    SSE stream of the real workflow state as it runs
  POST /api/brew/{id}/approve   send the human-in-the-loop `approve` signal

Run (from this temporal/ folder, with a dev server + worker already up):
  uv run uvicorn app:app --port 8000
"""
import asyncio
import json
import subprocess
import sys
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from temporalio.client import WorkflowExecutionStatus

from connection import get_client
from shared import BrewOrder, TASK_QUEUE

HERE = Path(__file__).resolve().parent
FRONTEND = HERE.parent / "harness-cafe.html"

# ---- Worker process management (so the browser can kill/restart it for real) ----
# The app owns a single worker subprocess. Do NOT also run `uv run worker.py`
# separately in live mode, or the crash demo would have a second worker keeping
# the workflow alive.
_worker_proc: subprocess.Popen | None = None


def worker_alive() -> bool:
    return _worker_proc is not None and _worker_proc.poll() is None


def start_worker() -> None:
    global _worker_proc
    if worker_alive():
        return
    _worker_proc = subprocess.Popen([sys.executable, "worker.py"], cwd=str(HERE))


def kill_worker() -> None:
    """Hard-kill the worker (SIGKILL) to simulate a real crash mid-work."""
    global _worker_proc
    if worker_alive():
        _worker_proc.kill()
        try:
            _worker_proc.wait(timeout=5)
        except Exception:
            pass
    _worker_proc = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_worker()
    try:
        yield
    finally:
        kill_worker()


app = FastAPI(lifespan=lifespan)

_STATUS_NAMES = {
    WorkflowExecutionStatus.RUNNING: "running",
    WorkflowExecutionStatus.COMPLETED: "completed",
    WorkflowExecutionStatus.FAILED: "failed",
    WorkflowExecutionStatus.CANCELED: "canceled",
    WorkflowExecutionStatus.TERMINATED: "terminated",
    WorkflowExecutionStatus.TIMED_OUT: "timed_out",
    WorkflowExecutionStatus.CONTINUED_AS_NEW: "continued_as_new",
}


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(FRONTEND)


@app.get("/api/health")
async def health() -> JSONResponse:
    return JSONResponse({"ok": True})


@app.post("/api/brew")
async def brew() -> JSONResponse:
    client = await get_client()
    wf_id = f"brew-espresso-{uuid.uuid4().hex[:8]}"
    await client.start_workflow(
        "BrewEspressoWorkflow",
        BrewOrder(),
        id=wf_id,
        task_queue=TASK_QUEUE,
    )
    return JSONResponse({"workflow_id": wf_id})


@app.get("/api/worker/status")
async def worker_status() -> JSONResponse:
    return JSONResponse({"alive": worker_alive()})


@app.post("/api/worker/kill")
async def worker_kill() -> JSONResponse:
    kill_worker()
    return JSONResponse({"alive": False})


@app.post("/api/worker/restart")
async def worker_restart() -> JSONResponse:
    start_worker()
    return JSONResponse({"alive": worker_alive()})


@app.post("/api/brew/{wf_id}/approve")
async def approve(wf_id: str) -> JSONResponse:
    client = await get_client()
    handle = client.get_workflow_handle(wf_id)
    await handle.signal("approve")
    return JSONResponse({"ok": True})


@app.get("/api/brew/{wf_id}/events")
async def events(wf_id: str) -> StreamingResponse:
    """Poll the real workflow and stream state snapshots to the browser via SSE."""

    async def gen():
        client = await get_client()
        handle = client.get_workflow_handle(wf_id)
        last = None
        while True:
            desc = await handle.describe()
            status = desc.status

            stage = None
            if status == WorkflowExecutionStatus.RUNNING:
                try:
                    stage = await handle.query("stage")
                except Exception:
                    stage = None

            # Retry visibility: a pending activity on attempt > 1 is mid-retry.
            retry = {}
            try:
                for pa in desc.raw_description.pending_activities:
                    if pa.attempt and pa.attempt > 1:
                        retry[pa.activity_type.name] = pa.attempt
            except Exception:
                pass

            snap = {
                "workflow_id": wf_id,
                "status": _STATUS_NAMES.get(status, "unknown"),
                "stage": stage,
                "retry": retry,
                "approvalNeeded": stage == "awaiting approval",
            }

            done = status != WorkflowExecutionStatus.RUNNING
            if status == WorkflowExecutionStatus.COMPLETED:
                try:
                    snap["result"] = await handle.result()
                except Exception as exc:  # pragma: no cover
                    snap["error"] = str(exc)

            payload = json.dumps(snap)
            if payload != last:
                yield f"data: {payload}\n\n"
                last = payload

            if done:
                break
            await asyncio.sleep(0.3)

    return StreamingResponse(gen(), media_type="text/event-stream")
