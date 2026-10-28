# AGENTS.md — BellAI working agreement

Shared rules for every teammate **and** every AI coding assistant (Claude Code, Cursor, Copilot…) working in this repo. Read this before you touch code.

## What we're building

BellAI places automated, friendly voice calls to elderly people to remind them about medicines, appointments, meals, hydration and daily tasks. It listens to the reply, records the outcome, and escalates to a caregiver when needed.

```
Caregiver (Next.js form) ──REST──► FastAPI ──► DB (SQLite on each machine for now)
                                     │
                         APScheduler polls due tasks
                                     │
                                     ▼
                         Bolna API  POST /call  ──► phone call to elder
                                     │
                    Bolna webhook ◄──┘  /api/webhook/call-outcome
                                     │
                     outcome → completed / later / needs_help / no_answer
```

Full flow: [docs/architecture.md](docs/architecture.md).

## Team

Ayush, Devesh, and Utkarsh. The call path is three owners. Each area has **one owner**. Work only inside your area on your branch. Anything under "shared" needs a heads-up in the group chat before you change it.

| Area | Path | Owner | Branch prefix |
|---|---|---|---|
| Caregiver UI | `frontend/` | Ayush | `feat/frontend-…` |
| Scheduler, retries, reminder state, and the reminder HTTP routes (including call-now) | `backend/app/services/scheduler.py`, `apply_outcome` in `backend/app/services/outcomes.py`, `backend/app/routers/tasks.py` | Ayush | `feat/scheduler-…` |
| Voice agent and outbound calls. Bolna agent, prompt, languages, extraction fields. Bolna client, mock mode, execution ids, call errors. | `agent/`, `backend/app/services/bolna.py` | Devesh | `feat/voice-…` |
| Webhooks, outcome normalization, caregiver alerts, elder and contact routes, call-log reads, auth stub | `backend/app/routers/webhooks.py`, `classify` in `backend/app/services/outcomes.py`, `backend/app/services/notifications.py`, `backend/app/routers/profiles.py`, `backend/app/routers/calls.py`, `backend/app/routers/auth.py` | Utkarsh | `feat/webhook-…` |

How the three meet:

1. Ayush decides a reminder is due and calls Devesh's outbound client with the elder's phone and the reminder context.
2. Devesh places the call (or the mock call) and returns the provider execution id, or a failure (timeout, auth, rejected request, malformed response). Ayush stores that result on the attempt.
3. Bolna calls Utkarsh's webhook. Utkarsh matches the execution id, ignores duplicates and intermediate updates, and maps the payload onto the shared outcome.
4. Utkarsh hands that outcome to Ayush. Ayush applies the state change: reschedule, retry, or stop. Ayush's rules say when a caregiver must be told.
5. Utkarsh sends that alert and records whether delivery worked.

The same task id and Bolna execution id (`bolna_call_id`) are used the whole way through.

**Shared contracts** (change together, in one small PR, announced first). All three agree before the PR is opened.
- `backend/app/models.py` — tables. Ayush proposes reminder columns and status values. Utkarsh proposes call-log columns. Devesh proposes the execution-id field.
- `backend/app/schemas.py` — request and response shapes, including the webhook body and the outcome names.
- `frontend/src/lib/types.ts` — must mirror `schemas.py`. Ayush updates this file in that same PR.
- `backend/app/main.py` — only add a line to register a new router.
- `backend/app/db.py`, `backend/app/config.py` — local database and env. Heads-up before editing.

Stored outcome codes today are `completed`, `later`, `needs_help`, and `no_answer`. The names the three of us use in discussion map onto them like this: completed; requested-later → `later`; help-needed → `needs_help`; no-answer and failed-call → `no_answer`; unresolved → `needs_help` until we split it. Renaming the stored codes is a shared-contract change, not a one-person edit.

`docs/` is shared. Heads-up in the group chat before editing it.

## Git workflow (how we avoid merge conflicts)

1. `main` is always runnable. Never commit directly to it.
2. Branch from latest `main`: `git checkout main && git pull && git checkout -b feat/voice-webhook-parsing`
3. Keep PRs small (one feature). Rebase on `main` before opening: `git pull --rebase origin main`
4. One reviewer approves, then squash-merge.
5. Never commit `.env`, `*.db`, `node_modules/`, `.venv/`.

Commit messages: `area: what changed`, e.g. `frontend: add medication task form`, `voice: parse extracted_data from Bolna webhook`.

## Conventions

**Backend (Python, FastAPI)**
- Python 3.9+ compatible (use `Optional[X]`, `List[X]`, not `X | None`).
- Routers live in `app/routers/`, business logic in `app/services/`. Routers stay thin.
- All datetimes are stored **naive UTC**. Convert to the elder's timezone only when speaking/displaying.
- Config comes from env via `app/config.py` — never hard-code keys.
- The database is a local SQLite file (`sqlite:///./bellai.db`). That is enough for the first users on one machine. Scaling to a shared hosted database later will need something like Postgres.
- `BOLNA_MOCK=true` (default) fakes outbound calls so everyone can develop without spending credits.

**Frontend (TypeScript, Next.js App Router)**
- All API calls go through `src/lib/api.ts`. No `fetch` calls scattered in components.
- Types in `src/lib/types.ts` mirror `backend/app/schemas.py`.
- Client components only where you need state/forms (`"use client"`).

**Voice agent (Devesh)**
- The Bolna agent's prompt lives in `agent/prompts/` (versioned in git, pasted into the Bolna dashboard).
- The agent must extract a structured `outcome` (`completed | later | needs_help`) plus optional `snooze_minutes` and `note`. Utkarsh's webhook reads these exact keys — see `agent/README.md`.

**Reminder rules (Ayush)**
- Only Ayush moves a task between statuses. A due task becomes `calling` only when a call is authorized. A cancelled task, a task already `calling`, and a task already resolved are not called again.
- Quiet hours are the elder's `call_window_start` / `call_window_end` in the elder's timezone.
- `later` snoozes. `needs_help` stops and asks Utkarsh to alert the caregiver. `no_answer` retries until `max_attempts`, then `missed`, which also alerts the caregiver.

## Task status lifecycle (source of truth, Ayush)

```
pending ──Ayush's scheduler──► calling ──Utkarsh's webhook──► completed   (recurring → back to pending at next time)
                                  │                            snoozed     (outcome "later": re-call after snooze_minutes)
                                  │                            needs_help  (Utkarsh alerts the caregiver)
                                  └──no answer──►              pending again (retry) … after max_attempts → missed (caregiver alerted)
```

## Running locally

See [README.md](README.md#quick-start).

## For AI assistants

- Stay inside the area the human asked about; don't refactor other owners' files.
- If a change needs a shared-contract edit, say so explicitly instead of silently editing it.
- Run `pytest` in `backend/` and `npm run build` in `frontend/` before declaring done.
