# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

An interactive educational demo for **Temporal as the agent harness**, using a coffee
machine as the vehicle: the espresso machine is the harness, the bean is the model, and
Temporal is what keeps it all durable, observable, and replayable. The point the demo
makes: **Temporal is essential to agent harnesses.**

It has two layers:

1. **`harness-cafe.html`** — the front end. A single self-contained HTML file (embedded
   CSS/JS). It runs in two modes automatically:
   - **Simulation** — opened as a plain file (e.g. the published Artifact), everything is
     faked in JavaScript. No backend needed.
   - **Live** — when served by the backend below, it drives a **real** Temporal workflow
     and reflects actual workflow state. The header shows a green **LIVE · real Temporal**
     badge when connected.
2. **`temporal/`** — a real, runnable Python Temporal implementation (workflow, activities,
   worker, client, and a FastAPI app the front end talks to).

## Running

**Simulation only:** open `harness-cafe.html` in a browser.

**Live (real Temporal):** two processes — the app owns and manages the worker.
```bash
temporal server start-dev --ui-port 8233          # dev server + UI
cd temporal && uv run uvicorn app:app --port 8000 # serves the UI, spawns the worker
# open http://localhost:8000
```
Do **not** run `uv run worker.py` separately in live mode — a second worker would keep the
workflow alive and break the kill-worker demo. (Running the worker/starter standalone is
fine for CLI-only use; see `temporal/README.md`.)

## Front end (`harness-cafe.html`)

Three panels:
- **Left — "This is your harness"**: SVG espresso machine. Parts are **inspect-only**
  hotspots — clicking one shows the harness component it maps to and highlights its code.
  They do **not** execute anything (activities run only as part of the workflow).
- **Middle — "What's happening in Temporal"**: the live event timeline
  (pending/running/retrying/done) — in live mode this is the real workflow state streamed
  over SSE; a durable **Awaiting approval** pause surfaces an **Approve** button.
- **Right — "The actual code"**: the `BrewEspressoWorkflow` Python (educational display).

Graceful degradation is driven by a `GET /api/health` probe on load (`LIVE` flag). The
**ON/OFF toggle** and the simulated crash are simulation-only teaching devices; in live
mode the ON/OFF toggle is hidden and the crash button becomes a **real** worker kill.

## Core data model (front end)

The `STEPS` array maps each machine component → a Temporal activity → a harness concept:

```js
STEPS = [
  { id: 'grind',    act: 'grind_beans',       harness: 'Tools' },
  { id: 'heat',     act: 'heat_water',         harness: 'Context engineering' },
  { id: 'pressure', act: 'set_pressure',       harness: 'Guardrails & policy' },
  { id: 'sandbox',  act: 'lock_portafilter',   harness: 'Sandboxing' },
  { id: 'pull',     act: 'extract_shot',       harness: 'The model does its work' },
  { id: 'observe',  act: 'log_shot_timer',     harness: 'Observability' },
]
```

## Backend (`temporal/`)

| File | Purpose |
|------|---------|
| `shared.py` | `BrewOrder` / `Shot` dataclasses, `TASK_QUEUE` (sandbox-safe) |
| `activities.py` | The six activities (all I/O). `heat_water` fails attempt 1 to show a real retry |
| `workflows.py` | `BrewEspressoWorkflow` — deterministic orchestration + `approve` **signal** + `stage` **query** gating `extract_shot` |
| `connection.py` | Client connection: local dev server by default, Temporal Cloud via `TEMPORAL_ADDRESS/NAMESPACE/API_KEY` |
| `worker.py` | Runs the worker |
| `starter.py` | Starts a workflow from the CLI |
| `app.py` | FastAPI: serves the front end; `/api/brew`, `/api/brew/{id}/events` (SSE), `/api/brew/{id}/approve`, `/api/worker/{kill,restart,status}`. **Owns the worker subprocess** so the browser can kill/restart it |

## Temporal concepts demonstrated

- **Durability & replay** — kill the worker mid-run; the workflow survives on the server and
  resumes from the last completed activity (live: real `SIGKILL` + restart of the worker).
- **Automatic retry** — `heat_water` fails once and is retried via `RetryPolicy`.
- **Human-in-the-loop** — the workflow durably pauses on `wait_condition` until the `approve`
  signal arrives.

## Temporal Developer Skill

When working on any Temporal-related code in this repo (workflows, activities, worker,
client, or the FastAPI bridge), invoke the **temporal-developer skill** first:

```
/temporal-developer
```

Prefer it over general knowledge when there is any ambiguity about correct Temporal patterns.

## Temporal correctness rules

Real executable code lives in `temporal/` and must be correct. (The Python shown *inside*
`harness-cafe.html` is intentionally simplified for readability — e.g. `retry=RetryPolicy(max=10)`
and no explicit timeouts — matching the house style of Temporal's own demo code panels. Keep
the two in sync in spirit, not character-for-character.)

**Workflow code must be deterministic.** Never use in workflow context:
- `datetime.now()` → `workflow.now()`
- `random.random()` → `workflow.random()`
- `asyncio.sleep()` → `workflow.sleep()`
- `uuid.uuid4()` → `workflow.uuid4()`

**Activities handle all non-deterministic operations** (I/O, API calls, randomness). Keep
workflow code purely orchestration.

**RetryPolicy** lives on the `workflow.execute_activity()` call. Real code uses
`retry_policy=RetryPolicy(maximum_attempts=10)`; `execute_activity` also requires a timeout
(`start_to_close_timeout`). Multi-argument activities use `args=[...]`.

**File separation**: workflow definitions and activity implementations stay in separate
files; the workflow imports activities under `workflow.unsafe.imports_passed_through()`.

**Task queue names** must match exactly between worker registration and client start calls
(`TASK_QUEUE` in `shared.py`).

## Styling

CSS variables define the coffee-themed palette: `--ink`, `--espresso`, `--matcha`, `--crema`,
`--indigo`. Status colors: pending (gray), running (blue), done (matcha green), retry (orange),
failed (red). Layout is a three-panel grid; the logo lockup sits on a cream "signage" plate.
