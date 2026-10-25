# AGENTS.md — BellAI working agreement

Shared rules for every teammate **and** every AI coding assistant (Claude Code, Cursor, Copilot…) working in this repo. Read this before you touch code.

## What we're building

BellAI places automated, friendly voice calls to elderly people to remind them about medicines, appointments, meals, hydration and daily tasks. It listens to the reply, records the outcome, and escalates to a caregiver when needed.

```
Caregiver (Next.js form) ──REST──► FastAPI ──► DB (SQLite → Postgres)
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

## Repo layout & ownership

Each area has **one owner**. Work only inside your area on your branch; anything under "shared" needs a heads-up in the group chat before you change it.

| Area | Path | Owner | Branch prefix |
|---|---|---|---|
| Skeleton, shared contracts, integration | `AGENTS.md`, `docs/`, `backend/app/models.py`, `backend/app/schemas.py`, `frontend/src/lib/types.ts` | Ayush | `chore/…` |
| Input layer (forms, caregiver UI) | `frontend/` | _TBD_ | `feat/frontend-…` |
| Voice agent (Bolna agent, prompts, call + webhook) | `agent/`, `backend/app/services/bolna.py`, `backend/app/routers/webhooks.py` | _TBD_ | `feat/voice-…` |
| Intermediate layer (scheduler, outcome logic, caregiver alerts) | `backend/app/services/scheduler.py`, `outcomes.py`, `notifications.py` | _TBD_ | `feat/scheduler-…` |
| API routers (auth, profiles, tasks, calls) | `backend/app/routers/` (except webhooks) | _TBD_ | `feat/api-…` |

**Shared contracts** (change together, in one small PR, announced first):
- `backend/app/models.py` — DB tables
- `backend/app/schemas.py` — request/response shapes
- `frontend/src/lib/types.ts` — must mirror `schemas.py`
- `backend/app/main.py` — only add a line to register a new router

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
- `BOLNA_MOCK=true` (default) fakes outbound calls so everyone can develop without spending credits.

**Frontend (TypeScript, Next.js App Router)**
- All API calls go through `src/lib/api.ts`. No `fetch` calls scattered in components.
- Types in `src/lib/types.ts` mirror `backend/app/schemas.py`.
- Client components only where you need state/forms (`"use client"`).

**Voice agent**
- The Bolna agent's prompt lives in `agent/prompts/` (versioned in git, pasted into the Bolna dashboard).
- The agent must extract a structured `outcome` (`completed | later | needs_help`) plus optional `snooze_minutes` and `note`. The backend depends on these exact keys — see `agent/README.md`.

## Task status lifecycle (source of truth)

```
pending ──scheduler──► calling ──webhook──► completed   (recurring → back to pending at next time)
                          │                 snoozed     (outcome "later": re-call after snooze_minutes)
                          │                 needs_help  (caregiver notified)
                          └──no answer──►   pending again (retry) … after max_attempts → missed (caregiver notified)
```

## Running locally

See [README.md](README.md#quick-start).

## For AI assistants

- Stay inside the area the human asked about; don't refactor other owners' files.
- If a change needs a shared-contract edit, say so explicitly instead of silently editing it.
- Run `pytest` in `backend/` and `npm run build` in `frontend/` before declaring done.
