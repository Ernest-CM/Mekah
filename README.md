# Mekah — Adaptive Web Interface (CRL + HITL)

Implementation of the system described in `project_document.txt` and refined in
`revised.md`: an adaptive web interface that uses **constrained reinforcement
learning** with a **WCAG safety shield** and **human-in-the-loop** governance.

The architecture follows revised.md §5 to the letter:

```
┌──────────────────────┐     /api/context        ┌──────────────────────┐
│  React + TypeScript  │ ─────────────────────▶  │   FastAPI gateway    │
│   demo task UI       │     /api/adapt/decide   │                      │
│   theme engine       │     /api/adapt/validate │  ┌────────────────┐  │
│   reviewer console   │     /api/adapt/execute  │  │  LinUCB policy │  │
│   metrics console    │     /api/policy/update  │  │  (NumPy)       │  │
└──────────────────────┘     /api/hitl/*         │  └────────────────┘  │
                                                 │  ┌────────────────┐  │
                                                 │  │ WCAG validator │  │
                                                 │  │ (rule engine)  │  │
                                                 │  └────────────────┘  │
                                                 │  ┌────────────────┐  │
                                                 │  │ HITL queue +   │  │
                                                 │  │ reward calc    │  │
                                                 │  └────────────────┘  │
                                                 │  SQLite audit log    │
                                                 └──────────────────────┘
```

## What's implemented

- **Online contextual bandit (LinUCB)** with disjoint per-arm linear payoffs,
  versioned snapshots, and persistence (`backend/app/core/linucb.py`,
  `backend/app/core/policy_service.py`).
- **6 discrete UI actions** (A1–A6) per revised.md §4.3
  (`backend/app/core/actions.py`).
- **Reward function** with weights matching revised.md §4.4
  (0.4·r_task + 0.2·r_time + 0.2·r_error + 0.2·r_trust − λ·v) plus the −0.5
  HITL-rejection bonus penalty (`backend/app/core/reward.py`).
- **WCAG 2.1 safety shield**: contrast (1.4.3 / 1.4.6), resize text (1.4.4),
  reflow (1.4.10), keyboard (2.1.1), target size (2.5.5), animation (2.3.3).
  Every candidate action is *simulated* and gated before deployment
  (`backend/app/core/wcag.py`).
- **HITL governance**: triggers (low confidence, validator warn, high-impact
  region, vulnerable profile), role-aware approve/reject/override with
  product-owner-only override + mandatory reason
  (`backend/app/core/hitl.py`, `backend/app/api/hitl.py`).
- **Full audit trail** in SQLite — context, decision, validation, HITL,
  execution, policy update, snapshot tables (`backend/app/db/models.py`).
- **Frontend**: 4-step demo task with profile presets (default / low vision /
  screen reader / motor / cognitive), live theme engine, real-time validation
  panel, HITL reviewer dashboard, metrics dashboard.

## Quick start

### 1. Install backend (Python 3.12 required — Pydantic 2 has no Py3.14 wheels yet)

```bash
cd backend
py -3.12 -m pip install -r requirements.txt
```

### 2. Install frontend

```bash
cd frontend
npm install
```

### 3. Run both

In one terminal:

```bash
cd backend
py -3.12 -m uvicorn app.main:app --reload --port 8000
```

In another terminal:

```bash
cd frontend
npm run dev
```

Open <http://localhost:5173>. The Vite dev server proxies `/api/*` to the
FastAPI backend on port 8000.

### 4. Smoke-test the API

```bash
cd backend
py -3.12 smoke_test.py
```

This walks /context → /adapt/decide → /hitl/review → /adapt/execute →
/policy/update → /metrics for two contrasting scenarios.

### 5. Run the unit tests

```bash
cd backend
py -3.12 -m pytest tests/ -q
```

32 tests cover: LinUCB algorithm, snapshot persistence, exploration vs
exploitation, WCAG rules, contrast math, action simulation, reward formula,
context-vector normalization, and the experiment runner.

### 6. Run the phased online evaluation (revised.md §7)

```bash
cd backend
py -3.12 run_experiment.py --warmup 60 --learning 240 --test 120 --seed 42
```

This runs the **methodologically correct** evaluation that replaces Chapter 3
§3.11's invalid 80:20 split:

  - **Phase A** (warm-up) — limited exploration with safe defaults
  - **Phase B** (online learning) — LinUCB updates after every episode
  - **Phase C** (frozen test) — alpha=0, no updates, A/B vs three baselines

Compares LinUCB against `static` (no adaptation), `rule_based` (hand-coded
if/else), and `random` baselines, with two-proportion z-tests for compliance
and Mann-Whitney U for completion time, trust, and reward. Headline KPIs are
checked against revised.md §3 targets (≥98% compliance, ≥15% reward gain). A
JSON report is written to `experiment_report.json` for Chapter 5.

## Try it

1. **Demo task** tab — pick a profile and click through the 4 steps. Each
   correct click triggers an adaptation request. Watch the validation panel
   show which WCAG rules were checked and whether the action was simulated as
   pass / warn / fail.
2. **HITL reviewer** tab — when an adaptation is flagged (low confidence,
   warn, high-impact, vulnerable profile), it lands here. Approve, reject, or
   (as a Product Owner) override with a written reason. Rejections fall back
   to A6 (no change) and feed a −0.5 reward penalty into the next policy
   update.
3. **Metrics** tab — live counters for compliance rate, fallbacks, per-arm
   pulls and average rewards, model version. Compliance target is ≥ 98%
   per revised.md §3.

## API surface (revised.md §5.2)

| Endpoint              | Purpose                                             |
| --------------------- | --------------------------------------------------- |
| `POST /api/context`   | Persist a client context snapshot.                  |
| `POST /api/adapt/decide`   | LinUCB selects an action; auto-validates and flags HITL if needed. |
| `POST /api/adapt/validate` | Stand-alone WCAG check for any (context, action) pair. |
| `POST /api/adapt/execute`  | Apply (or fallback) the decision after HITL has resolved. |
| `GET  /api/hitl/queue`     | List pending review items.                          |
| `POST /api/hitl/review`    | Submit approve / reject / override.                 |
| `POST /api/policy/update`  | Compute reward, update LinUCB, snapshot model.      |
| `GET  /api/metrics`        | Live KPIs: compliance, reward, arm stats, queue.    |
| `GET  /api/actions`        | Reference list of UI actions A1–A6.                 |

OpenAPI/Swagger UI: <http://127.0.0.1:8000/docs>

## Mapping back to the dissertation

| Document section                            | Implementation                                |
| ------------------------------------------- | --------------------------------------------- |
| Ch. 3 §3.1–3.2 modules + architecture       | `backend/app/api/*`, `backend/app/core/*`     |
| Ch. 3 §3.6 RL framework                     | `core/linucb.py`, `core/features.py`          |
| Ch. 3 §3.7 constrained learning             | `core/wcag.py` + gate in `api/adapt.py`       |
| Ch. 3 §3.8 HITL                             | `core/hitl.py`, `api/hitl.py`                 |
| Ch. 3 §3.11 (revised in `revised.md` §7)    | Phased online evaluation via `/policy/update` |
| Ch. 3 §3.12 evaluation metrics              | `api/policy.py` `/metrics` endpoint           |
| Ch. 3 §3.13 ethical / audit                 | All `db/models.py` audit tables               |
| revised.md §4.4 reward equations            | `core/reward.py`                              |
| revised.md §4.5 pre-action gate logic       | `api/adapt.py` `decide()` + `execute()`       |
| revised.md §8 HITL governance               | `core/hitl.py` triggers + role rules in `api/hitl.py` |

## Repo layout

```
backend/
├── app/
│   ├── main.py              # FastAPI entrypoint
│   ├── config.py            # weights, thresholds, paths
│   ├── api/                 # route handlers per spec module
│   ├── core/                # LinUCB, features, WCAG, reward, HITL trigger
│   ├── db/                  # SQLAlchemy models + audit tables
│   └── schemas/             # Pydantic request/response schemas
├── requirements.txt
├── run.py                   # `py -3.12 run.py`
└── smoke_test.py            # end-to-end pipeline test
frontend/
├── src/
│   ├── App.tsx              # router shell
│   ├── api/client.ts        # typed API client
│   ├── theme/               # CSS variables driven by adaptations
│   ├── hooks/               # useTelemetry, useAdaptiveUI
│   ├── pages/               # DemoTask, ReviewerDashboard, MetricsDashboard
│   └── components/          # ProfilePicker, ValidationPanel
├── package.json
└── vite.config.ts           # /api proxy to :8000
```

## Notes & known limits

- DB is SQLite (single file under `backend/data/mekah.db`); swap `DB_URL` in
  `backend/app/config.py` for PostgreSQL if you want what revised.md §5.1
  ultimately specifies.
- Monitoring is via `/api/metrics` JSON; revised.md mentions Prometheus +
  Grafana — those would plug in via a `/metrics` Prometheus exporter without
  changing the rest of the stack.
- WCAG checks are a curated subset of the success criteria most affected by
  the supported actions; this matches the project's stated limit (Ch. 1
  §1.7) that automated tooling catches ≈30–50% of accessibility issues.
