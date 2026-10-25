# BellAI architecture

## System flow

1. **Setup (frontend):** caregiver registers the elder, trusted contacts, preferred language, calling window. _Later: OTP / Google login._
2. **Input layer (frontend):** forms to store medication reminders, appointments, meals, hydration, daily tasks. _Later: vision model reads prescriptions/schedules._
3. **Reminder trigger (backend `services/scheduler.py`):** APScheduler polls every `SCHEDULER_INTERVAL_SECONDS` for due tasks.
4. **Automated call (backend `services/bolna.py`):** `POST https://api.bolna.ai/call` with the elder's phone and task context.
5. **Conversation (Bolna agent, `agent/prompts/`):** greets, delivers the reminder, answers simple questions, confirms.
6. **Understand response (backend `routers/webhooks.py` → `services/outcomes.py`):**
   - `completed` → mark done (recurring tasks roll to next occurrence)
   - `later` → snooze, re-call after `snooze_minutes`
   - `needs_help` → mark, notify caregiver
   - no answer / busy / failed → retry up to `max_attempts`, then `missed` + notify caregiver
7. **Record & monitor:** every call is a `CallLog` row (status, outcome, transcript, summary).
8. **Caregiver support (`services/notifications.py`):** alerts for missed reminders / help requests. _Prototype logs only; later SMS/WhatsApp._

## Backend flow

```
[ Next.js / React (TypeScript) ]
             │  (REST / JSON)
             ▼
      [ FastAPI App ]
      ├── API Routers (Auth, Profiles, Tasks, Calls, Webhook)
      ├── APScheduler (polls due reminder tasks)
      └── DB Layer (SQLModel → SQLite on each machine for now)
             │
             ├──► Outbound: Bolna REST API (POST /call)
             └──◄ Inbound:  Bolna webhook (POST /api/webhook/call-outcome)
```

## API contract (v0)

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | liveness |
| POST | `/api/auth/login` | _stub_ |
| GET/POST | `/api/elders` | list / create elder |
| GET/PATCH/DELETE | `/api/elders/{id}` | read / update / delete elder |
| GET/POST | `/api/elders/{id}/contacts` | trusted contacts |
| GET/POST | `/api/tasks` | list (`?elder_id=`) / create task |
| GET/PATCH/DELETE | `/api/tasks/{id}` | read / update / delete task |
| POST | `/api/tasks/{id}/call-now` | trigger a call immediately (demo button) |
| GET | `/api/calls` | call logs (`?task_id=`) |
| POST | `/api/webhook/call-outcome` | Bolna webhook |

Shapes are defined in `backend/app/schemas.py` (live at `/docs`) and mirrored in `frontend/src/lib/types.ts`.

## Data model

- **Elder** — name, phone (E.164), language, timezone, call window
- **TrustedContact** — elder_id, name, phone, relation, notify_on_missed
- **Task** — elder_id, type, title, details, scheduled_at (next due, UTC), recurrence, status, attempts, max_attempts, retry_minutes
- **CallLog** — task_id, bolna_call_id, status, outcome, transcript, summary

SQLite on the API machine is enough for the first users. Scaling later will need a hosted database such as Postgres.
