# BrewEspresso — real Temporal implementation

A runnable Temporal version of the `BrewEspressoWorkflow` shown in
`../harness-cafe.html`. Same six steps, but executing for real on a Temporal
server — with automatic retries, a human-in-the-loop approval signal, and
durable replay you can see in the Temporal Web UI.

```
Grinder      → grind_beans        (Tools)
Boiler       → heat_water         (Context engineering)  ← retries automatically
Pressure     → set_pressure       (Guardrails & policy)
Portafilter  → lock_portafilter   (Sandboxing)
[human approves the shot — durable signal wait]
Group head   → extract_shot       (the model does its work)
Shot timer   → log_shot_timer     (Observability)
```

## Prerequisites
- [`temporal` CLI](https://docs.temporal.io/cli)
- [`uv`](https://docs.astral.sh/uv/)

## Run it

Three terminals:

```bash
# 1. Local Temporal dev server (UI at http://localhost:8233)
temporal server start-dev --ui-port 8233

# 2. Worker (from this temporal/ folder)
uv run worker.py

# 3. Start a brew
uv run starter.py
```

Then open the workflow in the UI at `http://localhost:8233` and watch the event
history fill in.

## Run the live frontend (coffee UI wired to real Temporal)

A FastAPI app (`app.py`) serves `../harness-cafe.html` and bridges it to Temporal.
In live mode the **app owns the worker** (it spawns one on startup so the browser
can kill/restart it), so you only need the dev server + the app:

```bash
# terminal 1: dev server
temporal server start-dev --ui-port 8233
# terminal 2: the app (it starts and manages the worker itself)
uv run uvicorn app:app --port 8000
```

> Don't also run `uv run worker.py` separately in live mode — a second worker
> would keep the workflow alive and break the kill-worker demo.

Open `http://localhost:8000`. The header shows **LIVE · real Temporal** and:
- **Pull the shot** starts a real `BrewEspressoWorkflow`; the middle panel reflects
  the actual workflow state over SSE.
- At **Awaiting approval**, click **Approve — pull the shot** to send the real
  `approve` signal.
- **Kill worker** (the crash button) really `SIGKILL`s the worker process, then
  the app restarts it; the workflow survives on the server and resumes via replay.

Opened as a plain file (not served), the same page falls back to its built-in
simulation. Machine parts are **inspect-only** (they explain the mapping; they
don't execute anything).

Endpoints: `POST /api/brew`, `GET /api/brew/{id}/events` (SSE),
`POST /api/brew/{id}/approve`, `POST /api/worker/kill`, `POST /api/worker/restart`,
`GET /api/worker/status`, `GET /api/temporal-ui` (where the Web UI lives — local or Cloud).

## What to try

**Automatic retry** — `heat_water` fails on its first attempt on purpose. The
worker log shows `attempt 1` failing, then `attempt 2` succeeding; the workflow
never notices. That's the `RetryPolicy(maximum_attempts=10)` on the call.

**Human-in-the-loop (durable signal wait)** — start it *without* auto-approval to
see the workflow pause indefinitely, holding no resources, until a human signals:

```bash
AUTO_APPROVE=false uv run starter.py
# copy the printed workflow id, then:
temporal workflow signal --workflow-id <id> --name approve
```

**Durable replay** — start a brew, and while the worker is running, kill it
(Ctrl+C) mid-shot. Restart `uv run worker.py`. Temporal replays the event
history and resumes from the last completed activity — no lost state, no
re-running finished steps.

## Point it at Temporal Cloud

No code changes — just environment variables:

```bash
export TEMPORAL_ADDRESS="<namespace>.<account>.tmprl.cloud:7233"
export TEMPORAL_NAMESPACE="<namespace>.<account>"
export TEMPORAL_API_KEY="<your-api-key>"
uv run worker.py   # and, in another shell, uv run starter.py
```

## Files
| File | Purpose |
|------|---------|
| `shared.py` | `BrewOrder` / `Shot` dataclasses, task queue name |
| `activities.py` | The six brew activities (all I/O lives here) |
| `workflows.py` | `BrewEspressoWorkflow` — deterministic orchestration + approval signal |
| `connection.py` | Client connection (local by default, Cloud via env vars) |
| `worker.py` | Runs the worker |
| `starter.py` | Starts a workflow and reports the result |
