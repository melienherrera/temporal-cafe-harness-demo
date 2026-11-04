# ☕ Melissa's Cafe — Temporal as the Agent Harness

An interactive demo for **how Temporal shows up in your agent harness**, using a coffee
machine as the vehicle.

- The **espresso machine** is the harness (tools, context, guardrails, sandbox, observability).
- The **bean** is the model.
- **Temporal** is what makes the whole thing durable, observable, and replayable.

The point it makes: **Temporal is essential to agent harnesses.**

## Two layers

| | What it is |
|---|---|
| **`harness-cafe.html`** | A single self-contained front end. Runs as a **simulation** when opened as a file, and goes **live against real Temporal** when served by the backend. |
| **`temporal/`** | A real, runnable Python Temporal implementation — `BrewEspressoWorkflow`, activities, worker, and a FastAPI app the front end talks to. |

The front end has three panels: the **espresso machine** (inspect any part to see the harness
component it maps to), **"What's happening in Temporal"** (the live event timeline), and the
**workflow code**.

## Quick start

### Just the simulation
Open `harness-cafe.html` in a browser. No dependencies, no backend.

### Live, on real Temporal
Prereqs: [`temporal` CLI](https://docs.temporal.io/cli) and [`uv`](https://docs.astral.sh/uv/).

```bash
# 1. local Temporal dev server + UI (http://localhost:8233)
temporal server start-dev --ui-port 8233

# 2. the app — serves the UI and manages the worker itself
cd temporal && uv run uvicorn app:app --port 8000
```

Open **http://localhost:8000**. The header shows a green **LIVE · real Temporal** badge.

> In live mode the app owns the worker, so **don't** run `uv run worker.py` separately — a
> second worker would break the kill-worker demo. See [`temporal/README.md`](temporal/README.md)
> for CLI-only usage and pointing at Temporal Cloud.

## What it demonstrates

- **Durability & replay** — hit **Kill worker** mid-run; the real worker process is
  `SIGKILL`ed, the workflow survives on the server, and a fresh worker replays history and
  resumes from the last completed activity.
- **Automatic retry** — `heat_water` fails its first attempt and is retried via `RetryPolicy`.
- **Human-in-the-loop** — the workflow durably pauses on a signal, waiting for a human to
  **approve** pulling the shot, then resumes.

## The BrewEspresso workflow

Each machine component maps to a Temporal activity and a harness concept:

| Machine part | Activity | Harness concept |
|---|---|---|
| Grinder | `grind_beans` | Tools |
| Boiler | `heat_water` | Context engineering |
| Pressure valve | `set_pressure` | Guardrails & policy |
| Portafilter | `lock_portafilter` | Sandboxing |
| Group head | `extract_shot` | The model does its work |
| Shot timer | `log_shot_timer` | Observability |

## Repo layout

```
harness-cafe.html      # the front end (simulation + live mode)
temporal/              # real Python Temporal implementation
  workflows.py         # BrewEspressoWorkflow (+ approve signal, stage query)
  activities.py        # the six activities
  worker.py            # the worker
  starter.py           # start a workflow from the CLI
  connection.py        # client connection (local default, Cloud via env)
  app.py               # FastAPI: serves the UI, bridges to Temporal, owns the worker
  README.md            # backend details
```

## Related

This demo illustrates the *outer harness*. For the real product, see
[`temporal-agent-harness`](https://github.com/temporal-community/temporal-agent-harness).
