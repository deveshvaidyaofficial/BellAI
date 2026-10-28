# Voice agent (Bolna)

Owner: Devesh (voice agent and outbound calls). The agent itself is configured in the [Bolna dashboard](https://platform.bolna.ai); this folder versions its prompt, languages, and extraction fields so they're reviewable in git.

## Setup checklist

1. Create an agent in Bolna → paste `prompts/reminder_agent.md` as the system prompt.
2. Pick STT/TTS/LLM providers (try Sarvam for Hindi/Marathi, Deepgram for English). Record what you chose below.
3. **Extraction**: in the agent's analytics/extraction settings, ask Bolna to extract this JSON from each call. The backend reads these exact keys:

   ```json
   {
     "outcome": "completed | later | needs_help",
     "snooze_minutes": 30,
     "note": "free-text anything the elder said that a caregiver should see"
   }
   ```

4. **Webhook**: set to `https://<your-ngrok>.ngrok.app/api/webhook/call-outcome`.
5. Copy the agent id + API key into `backend/.env`, set `BOLNA_MOCK=false`.

## Variables passed per call (`user_data`)

Built in `backend/app/services/bolna.py::build_user_data`. Use them in the prompt as `{elder_name}` etc.

| Variable | Example |
|---|---|
| `elder_name` | Asha |
| `language` | hi |
| `task_type` | medication |
| `task_title` | Take BP tablet (Amlodipine 5mg) |
| `task_details` | after breakfast, with water |
| `task_id` | 12 |

## Provider choices / benchmarks

| Date | STT | TTS | LLM | Language | Latency notes |
|---|---|---|---|---|---|
| | | | | | |
