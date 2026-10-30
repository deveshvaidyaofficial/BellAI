# Voice Agent (Bolna Integration)

Owner: Devesh (voice agent and outbound calls).

BellAI integrates with an existing voice agent configured in the [Bolna Dashboard](https://platform.bolna.ai). Do not create, clone, or replace this agent.

---

## 1. Existing Agent Configuration

* **Agent ID:** `c8fcf1f9-a513-4bff-83fc-2cb627bf6b1c`
* **Supported Languages:** English and Hindi (`en`, `hi`)
* **Speech-to-Text (STT) Provider:** Sarvam Saaras v3
* **Text-to-Speech (TTS) Provider:** Sarvam Bulbul v3 Priya
* **Prompt Reference:** [`prompts/reminder_agent.md`](prompts/reminder_agent.md)

---

## 2. Dynamic Call Variables (`user_data`)

When BellAI initiates a call via `POST https://api.bolna.ai/call`, it injects these context variables (constructed in `backend/app/services/bolna.py::build_user_data`):

| Variable | Type | Description | Example |
| :--- | :--- | :--- | :--- |
| `elder_name` | string | Elder's first or full name | `Asha` |
| `language` | string | Preferred language code (`en` or `hi`) | `hi` |
| `task_type` | string | Category of reminder (`medication`, `appointment`, `meal`, `hydration`, `other`) | `medication` |
| `task_title` | string | Short reminder description | `Take BP tablet (Amlodipine 5mg)` |
| `task_details`| string | Optional details or instructions | `after breakfast, with water` |
| `task_id` | integer| Database ID of the task | `12` |

> 🔒 **Security note:** No caregiver authentication tokens, API keys, or personal credentials are ever passed to Bolna.

---

## 3. Structured Extractions Contract

In the Bolna dashboard under the agent's **Extractions** tab, the post-call extraction is configured to return the following JSON schema:

```json
{
  "outcome": "completed | later | needs_help",
  "snooze_minutes": 30,
  "note": "A concise factual note about what the elder said that a caregiver may need to know."
}
```

* **`outcome`**:
  * `completed`: Elder confirmed task is done or is doing it now.
  * `later`: Elder requested a callback later.
  * `needs_help`: Elder reported distress, pain, a fall, confusion, emergency, or explicitly requested caregiver assistance.
* **`snooze_minutes`**: Integer minutes (e.g. `15`, `30`, `60`) when `outcome` is `later`. Clamped by backend between 5 and 240 minutes (default 30).
* **`note`**: Concise string with factual observations. Persisted to `CallLog.extracted_note` and viewable by caregivers.

---

## 4. Webhook Configuration (Dashboard Steps)

> ⚠️ **Status:** The webhook is **not configured yet** in the Bolna dashboard. A developer or administrator must manually complete this step before live webhooks can be received.

### Step 4.1: Determine Webhook URL
* **Production Deployment:**
  ```text
  https://<your-public-domain>/api/webhook/call-outcome
  ```
* **Local Development / Testing (using HTTPS tunnel):**
  Start an HTTPS tunnel (e.g. ngrok):
  ```bash
  ngrok http 8000
  ```
  Use the generated HTTPS URL:
  ```text
  https://<your-subdomain>.ngrok.app/api/webhook/call-outcome
  ```

### Step 4.2: Configure in Bolna Dashboard
1. Log in to [Bolna Dashboard](https://platform.bolna.ai).
2. Select the existing agent: `c8fcf1f9-a513-4bff-83fc-2cb627bf6b1c`.
3. Go to the **Extractions** tab.
4. Locate the **Webhook Configuration** section.
5. In **Webhook URL**, paste your endpoint (`https://<domain>/api/webhook/call-outcome`).
6. Enable the **Add headers** toggle to secure incoming deliveries.
7. Enter a JSON object with your shared secret:
   ```json
   {
     "X-Bolna-Webhook-Secret": "your-secure-random-secret"
   }
   ```
   *(Alternatively, Bolna supports `"X-Api-Key": "your-secure-random-secret"` or `"Authorization": "Bearer your-secure-random-secret"`).*
8. Save the agent configuration. (Bolna will mask the secret value with `********`).
9. Use the **Send test** button in the dashboard to verify connectivity.

---

## 5. Environment Configuration

### Local `.env` (Development with Mock Defaults)
By default, `BOLNA_MOCK=true` fakes outbound calls and allows running tests without contacting Bolna or spending credits:
```dotenv
DATABASE_URL=sqlite:///./bellai.db
BOLNA_MOCK=true
BOLNA_AGENT_ID=c8fcf1f9-a513-4bff-83fc-2cb627bf6b1c
BOLNA_BASE_URL=https://api.bolna.ai
BOLNA_API_KEY=
BOLNA_FROM_PHONE_NUMBER=
BOLNA_WEBHOOK_SECRET=
BOLNA_TIMEOUT_SECONDS=15
```

### Live Calls Configuration (Staging / Production)
To place real calls, supply your secret credentials locally or in your deployment secret manager:
```dotenv
BOLNA_MOCK=false
BOLNA_AGENT_ID=c8fcf1f9-a513-4bff-83fc-2cb627bf6b1c
BOLNA_BASE_URL=https://api.bolna.ai
BOLNA_API_KEY=bolna_live_...
BOLNA_FROM_PHONE_NUMBER=+1XXXXXXXXXX   # optional caller ID if configured on telephony provider
BOLNA_WEBHOOK_SECRET=your-secure-random-secret
BOLNA_TIMEOUT_SECONDS=15
```

> 🔒 Never commit `.env` or real API keys to version control.

---

## 6. Testing Guide

### 6.1 Running Automated Unit & Mock Tests
The test suite runs entirely in mock mode and does not require an API key or network access:
```bash
cd backend
.venv\Scripts\pytest
```

### 6.2 Running a Single Controlled Live Test
Before enabling the scheduler or running unattended live calls:
1. Ensure `BOLNA_MOCK=false`, `BOLNA_AGENT_ID=c8fcf1f9-a513-4bff-83fc-2cb627bf6b1c`, and `BOLNA_API_KEY` are set in `backend/.env`.
2. Set `SCHEDULER_ENABLED=false` to prevent pending tasks from automatically triggering.
3. Configure an elder profile with an **explicitly authorized developer/tester phone number** (E.164 format, e.g. `+9198XXXXXXXX`).
4. Create a test task due in the future.
5. Use the Call-Now endpoint or click "Call now" in the dashboard:
   ```bash
   curl -X POST http://localhost:8000/api/tasks/<task_id>/call-now
   ```
6. Check the returned response: it contains the persisted `bolna_call_id` (the Bolna `execution_id`).
7. Answer the call on your phone, test the voice conversation in English or Hindi, and state whether you finished the task, want a reminder later, or need help.
8. Check the call history endpoint (`GET /api/calls?task_id=<task_id>`) to verify:
   * `status` updated to `completed`
   * `outcome` mapped correctly (`completed`, `later`, or `needs_help`)
   * `extracted_note` persisted with the notes from the call
   * `delivery_result` recorded if an alert was triggered

---

## 7. Known Limitations & Operational Considerations

1. **Webhook Delivery Order:** Bolna transitions calls through `queued` $\rightarrow$ `initiated` $\rightarrow$ `ringing` $\rightarrow$ `in-progress` $\rightarrow$ `call-disconnected` $\rightarrow$ `completed`. The `call-disconnected` event marks audio hangup; post-call extraction is only populated when the status reaches `completed`. BellAI treats `call-disconnected` as intermediate unless extractions are present, and only finalizes the task on the `completed` event.
2. **Idempotency:** Webhook deliveries may be retried or duplicated by networks. BellAI uses `CallLog.outcome` and `Task.status` idempotency locks: once an outcome is applied to a call log, subsequent callbacks for the same execution ID are recorded as acknowledged duplicates without modifying task states.
3. **Webhook Security:** Bolna does not sign payloads with asymmetric cryptography (HMAC SHA-256 signature headers). Authenticity is enforced via custom headers (e.g. `X-Bolna-Webhook-Secret`) configured in the dashboard. In production, ensure HTTPS is enforced and your firewall permits Bolna's official webhook IPs (`13.203.39.153`, `13.126.9.249`, `13.202.133.53`).
