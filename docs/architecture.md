# BellAI architecture

## System flow

1. **Setup (Ayush, frontend):** caregiver registers the elder, trusted contacts, preferred language, calling window. _Later: OTP / Google login._
2. **Input layer (Ayush, frontend):** forms to store medication reminders, appointments, meals, hydration, daily tasks. The reminder HTTP routes are his too. Elder, contact, and call-log routes are Utkarsh's. _Later: vision model reads prescriptions/schedules._
3. **Reminder trigger (Ayush, `services/scheduler.py`):** APScheduler polls every `SCHEDULER_INTERVAL_SECONDS` for due tasks. Ayush owns eligibility, quiet hours, cancellation, retries, and the task state machine.
4. **Automated call (Devesh, `services/bolna.py`):** `POST https://api.bolna.ai/call` with the elder's phone and task context. Returns Bolna's execution id. `BOLNA_MOCK=true` skips the real call.
5. **Conversation (Devesh, `agent/prompts/`):** greets, delivers the reminder, answers simple questions, confirms, and extracts the structured outcome.
6. **Callback (Utkarsh, `routers/webhooks.py`):** match the execution id, skip duplicate and intermediate callbacks, and map the payload onto the shared outcome (`classify` in `services/outcomes.py`).
7. **State change (Ayush, `apply_outcome` in `services/outcomes.py`):**
   - `completed` → mark done (recurring tasks roll to next occurrence)
   - `later` → snooze, re-call after `snooze_minutes`
   - `needs_help` → mark, and require a caregiver alert
   - no answer / busy / failed → retry up to `max_attempts`, then `missed`, and require a caregiver alert
8. **Record (Utkarsh):** every call is a `CallLog` row (status, outcome, transcript, summary), keyed by the Bolna execution id.
9. **Caregiver alert (Utkarsh, `services/notifications.py`):** send the alert when Ayush's rules require it, and record whether delivery worked. _Prototype logs only; later SMS/WhatsApp._

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
