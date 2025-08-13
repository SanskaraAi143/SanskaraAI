# Sanskara AI – Collaborative Indian Wedding Planner (Multi‑Agent System)

Sanskara AI is a production-focused, multi-agent wedding planning assistant specializing in Indian (multi-tradition) weddings. It combines structured domain workflows (tasks, budget, vendors, rituals) with LLM reasoning, smart context pruning, semantic memory, and real‑time WebSocket interaction.

This README is an end‑to‑end guide: architecture, environment, setup, running (API + WebSocket), database schema, smart context system, testing, deployment, and troubleshooting.

---
## Table of Contents
1. Vision & Core Value
2. High‑Level Architecture
3. Data & Memory Model
4. Smart Context System (Intent Driven)
5. Agents & Tools
6. API Surface (REST + WebSocket)
7. Environment Variables (.env)
8. Local Development (Non‑Docker & Docker)
9. Running the System
10. Onboarding → Active Wedding Flow
11. WebSocket Realtime Interaction
12. Database Schema (Supabase / PostgreSQL)
13. Logging & Observability
14. Testing Strategy & Commands
15. Typical User Journeys
16. Deployment Guidance
17. Security & Data Handling Notes
18. Troubleshooting
19. Roadmap / Future Enhancements
20. License
21. Contributing Guidelines

---
## 1. Vision & Core Value
Deliver an intelligent, culturally aware, proactive wedding planner that:
- Reduces planning friction (tasks, vendors, budget, timeline) across families.
- Supports nuanced Hindu / regional traditions while adapting to modern preferences.
- Keeps state, context, and decisions in sync without repeating questions.
- Offers real‑time multi‑modal (text now; audio/video scaffolding present) assistance.

Core principle: Invisible operations. Users see decisions & guidance, not system internals.

---
## 2. High‑Level Architecture
Text diagram:
```
User (UI / Client / WebSocket) ─────┐
                                   │  TEXT / (AUDIO / IMAGE future)
FastAPI (REST + WebSocket) ──► OrchestratorAgent (google-adk LlmAgent)
                                   │
                                   ├─ Smart Context Manager (intent → scoped data)
                                   ├─ Semantic Recall (pgvector Supabase memories)
                                   ├─ Sub‑Agents (exposed as tools)
                                   │    • Vendor Management
                                   │    • Budget & Expense
                                   │    • Ritual & Cultural
                                   │    • Creative (mood / imagery)
                                   │    • Task & Timeline
                                   │    (Guest/Collaboration pending)
                                   │
                                   ├─ Tool Layer (DB queries, workflows, tasks)
                                   │
Supabase PostgreSQL  ◄─────────────┤  (weddings, tasks, budget_items, chat_sessions, memories, vendors …)
SQLite (sessions.db) ◄─────────────┤  (ADK session service local fallback)
Redis / Celery (future)            │
AgentOps (observability)           │
Logging (JSON via loguru wrapper)  │
```

---
## 3. Data & Memory Model
Key tables (see `docs/design/overall_schema.sql`):
- weddings, wedding_members, tasks, workflows
- budget_items, user_shortlisted_vendors, vendors(+services, availability)
- chat_sessions, chat_messages (rolling + final summaries)
- memories (pgvector 1024‑dim embeddings for long‑term semantic recall)

Memory Layers:
1. Session State (per ADK session; ephemeral)
2. Smart Context (scoped fetch per user intent)
3. Conversation Summary + Recent Messages
4. Semantic Memory (retrieved embeddings via `semantic_search_facts`)

---
## 4. Smart Context System
Replaces “load everything” with intent‑driven selective fetch.
- Intent inferred from user_message keywords → scope (e.g., VENDOR_FOCUSED, BUDGET_FOCUSED, TIMELINE_FOCUSED, MINIMAL, FULL fallback)
- Caps list sizes (token guard) and normalizes keys
- Adds conversation_summary, recent_messages, semantic_memory.facts
- Rolling summaries every N user turns
See `SMART_CONTEXT_MIGRATION.md` for detailed evolution & performance notes.

---
## 5. Agents & Tools
Root agent: `OrchestratorAgent` (`sanskara/sanskara/agent.py`)
Sub‑agents (exposed as `AgentTool` wrappers). Many currently commented out from `sub_agents` list (can progressively re‑enable). Tools available include:
- Workflow & Task Ops: `upsert_workflow`, `upsert_task`, `update_task_details`, `update_workflow_status`, `get_active_workflows`
- Domain Helpers: vendor search/management (in sub‑agent), budget insights, timeline summarization (parts in task agent)
- Date helper: `get_current_datetime`

Response policy & examples baked into `prompt.py` (Sections 1–6). Strict rules: no exposing internal IDs; proactive next steps; culturally aware phrasing.

---
## 6. API Surface
FastAPI app: `api/app.py`

REST Endpoints (selected):
- Health: `GET /health` → aggregated component checks (local_db, agentops, supabase)
    *   **Note on AstraDB:** While the `/health` endpoint has a placeholder for AstraDB, Supabase is currently the primary and fully supported data persistence option. AstraDB integration is a potential future enhancement.
- Onboarding: `POST /onboarding/submit` (first or second partner), `GET /onboarding/partner-details?email=...`
- Weddings: `GET /weddings/{weddingId}`, `PUT/PATCH /weddings/{weddingId}`

WebSocket Endpoint:
- `ws://localhost:8765/ws?user_id=<uuid>` (after onboarding user belongs to a wedding via `wedding_members` mapping)

Swagger / OpenAPI: `http://localhost:8765/docs`

---
## 7. Environment Variables (.env)
Create `sanskara/.env`. (Empty example file currently present — populate.)
Suggested variables:
```
# Core Supabase
SUPABASE_URL= https://<project>.supabase.co
SUPABASE_KEY= <anon-or-service-role-key>
SUPABASE_ACCESS_TOKEN= <database-password>

# Google / Gemini (google-adk + google-genai)
GOOGLE_API_KEY= <if using client-side key>
# or service account credentials via application default (mounted separately)

# AgentOps
AGENTOPS_API_KEY= <agentops_key>

# Optional Feature Toggles
LOG_LEVEL=INFO
LOG_TO_FILE=false
LOG_FILE_PATH=app.log
DISABLE_SEMANTIC_RECALL=0

# Voice / Model Config Overrides (defaults in config.py)
MODEL=gemini-1.5-flash
VOICE_NAME=Puck

# (Future) Redis / Celery
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2
```
If Supabase vars are set → PostgreSQL URL constructed for MEMORY_DATABASE_URL; otherwise SQLite fallback for session service.

---
## 8. Local Development
### Option A: Pure Python
```
cd sanskara
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```
App listens on `0.0.0.0:8765`.

### Option B: Docker Compose
From repository root (contains `docker-compose.yml`).
```
docker-compose up --build
```
Hot‑reload is not yet wired; container mounts `./sanskara` directory.

### Option C: Direct Dockerfile
```
cd sanskara
docker build -t sanskara-ai .
docker run -p 8765:8765 --env-file .env sanskara-ai
```

---
## 9. Running the System
1. Configure `.env` with Supabase + AgentOps keys.
2. Apply schema in your Supabase SQL editor: `docs/design/overall_schema.sql` (run once; ensure pgvector extension enabled).
3. Start app (Python or Docker).
4. Onboard first partner (see next section) to create wedding + membership.
5. Onboard second partner (optional) which transitions wedding to `active` (depending on business rule adjustments).
6. Connect WebSocket using a UI / simple client passing the `user_id` (stored in Supabase `users` table) to start chatting.

---
## 10. Onboarding → Active Wedding Flow
Step 1: (External) User signs up via Supabase Auth (trigger inserts into `users`).
Step 2: Call `POST /onboarding/submit` with payload (first partner):
```
{
  "wedding_details": { ... },
  "current_user_onboarding_details": {"email": "a@example.com", "role": "bride", "name": "A"},
  "partner_onboarding_details": {"email": "b@example.com", "role": "groom", "name": "B"}
}
```
Step 3: Second partner fetches details: `GET /onboarding/partner-details?email=b@example.com` then submits `SecondPartnerSubmission` to same POST.
Step 4: Wedding status becomes `active`; Orchestrator full capabilities unlocked.

---
## 11. WebSocket Realtime Interaction
Endpoint: `ws://localhost:8765/ws?user_id=<user_uuid>`

Client → Server message types (JSON):
- `{ "type": "text", "data": "Find decorators in Mumbai under 1L" }`
- `{ "type": "audio", "data": <base64 PCM> }` (scaffold)
- `{ "type": "video", "data": <base64 JPEG>, "mode": "webcam" }` (scaffold)
- `{ "type": "end" }` (turn boundary hint)

Server → Client message types:
- `ready` – connection accepted
- `session_id` – ADK session identifier
- `text` – streaming partial model outputs (only chunks flagged `partial=True` forwarded)
- `audio` – (future) synthesized speech frames
- `turn_complete` – model finished a response
- `interrupted` – user input interrupted model
- `error` – error message

Session Priming:
- On connect, backend queries `wedding_members` to map user → wedding and stores `current_wedding_id` & `current_user_id` in session state.
- Smart context callback (`before_agent_callback`) attaches structured context each turn.

---
## 12. Database Schema
Canonical schema: `docs/design/overall_schema.sql` (PostgreSQL + extensions).
Key Extensions: `uuid-ossp`, `pg_trgm`, `btree_gin`, `vector`.
Important Tables Recap:
- Planning: `weddings`, `wedding_members`, `tasks`, `workflows`, `timeline_events`
- Financial: `budget_items`
- Vendors: `vendors`, `vendor_services`, `vendor_availability`, `user_shortlisted_vendors`, `bookings`, `booking_services`, `payments`, `reviews`
- Collaboration / Feedback: `task_feedback`, `task_approvals`, `notifications`
- Creativity: `mood_boards`, `mood_board_items`, `image_artifacts`
- Conversation: `chat_sessions`, `chat_messages`, `memories`

Embedding / Memory:
- `memories.embedding` currently 1024‑dim vector (index: ivfflat). Adjust `lists` parameter per data volume.

---
## 13. Logging & Observability
- Structured JSON logging via `logger.py` (loguru wrapper with contextualization: request_id, wedding_id, user_id, agent_name).
- Middleware adds `request_id` per HTTP request.
- AgentOps initialized if `AGENTOPS_API_KEY` present (tags: `google adk`).
- Health aggregation endpoint `/health` provides component statuses.

---
## 14. Testing Strategy & Commands
See `docs/TESTING_STRATEGY.md` for rationale.

Quick Commands:
```
# Unit + integration
cd sanskara
pytest -q

# Smart context behavior tests (examples)
pytest test_smart_context.py -q
pytest test_smart_context_simple.py -q
pytest test_intent_only.py -q

# Real (semi‑E2E) scripted tests
./run_real_tests.sh  # orchestrated shell flow (ensure env + test data)
```
Test Categories:
1. Tool Unit Tests (DB queries, budget calculations)
2. Agent Logic (mock LLM responses / tool invocations)
3. Orchestrator Delegation (ensures correct sub‑agent tool use)
4. End‑to‑End (API + DB mutation flows)

Mocking External Services: Supabase SQL execution, vendor APIs, Twilio (planned), Search.

---
## 15. Typical User Journeys
A. New Couple → Onboard → Chat → Vendor Shortlists → Budget Guidance → Task Progress → Timeline Refinement.
B. Progress Report ("booked venue") → Orchestrator silently updates tasks/workflows → returns reinforcement + next actions.
C. Budget Inquiry → Smart context injects budget aggregates → guided price range suggestions.
D. Vendor Discovery → Vendor sub‑agent invoked as a tool → results summarized with budget + timeline perspective.

---
## 16. Deployment Guidance
Minimum Requirements:
- Python 3.11+ (Dockerfile uses 3.13‑alpine) with system deps for scientific libs.
- Supabase project (or self‑hosted Postgres + pgvector) with applied schema.

Steps:
1. Build Docker image & push (GHCR / GCR / ECR).
2. Set environment secrets in orchestrator platform (Render / Fly / Cloud Run / ECS).
3. Run DB migrations by re‑executing `overall_schema.sql` (idempotent except for object drops—review before prod).
4. Configure scaling: WebSocket concurrency mainly CPU + network bound; consider separate worker for heavy embedding tasks (future Celery queue).
5. Add HTTPS termination (reverse proxy / ingress).

---
## 17. Security & Data Handling
- Secrets only via environment, never baked into image.
- Supabase RLS (row level security) recommended (not covered here) – enforce per wedding scoping.
- PII: emails in `users` + partner details; apply encryption-at-rest (Postgres default) and restrict exposure in API serializers.
- Logging: Avoid dumping large payloads or secrets (current logging already minimal; review before prod).

---
## 18. Troubleshooting
Issue: `/health` shows `supabase` degraded.
- Check `SUPABASE_URL`, `SUPABASE_ACCESS_TOKEN`, network egress.

Issue: WebSocket returns `No wedding found`.
- Confirm onboarding completed and `wedding_members` row exists mapping `user_id`.

Issue: Repeated context / agent re‑asking questions.
- Inspect logs for missing context keys; validate smart context intent classification; run `pytest test_intent_only.py`.

Issue: High token usage.
- Ensure list caps active (see `agent.py` token guard section) & disable FULL scope fallback for generic queries or refine intent mapping.

Issue: Semantic recall empty.
- Confirm `memories` table exists; feature flag `DISABLE_SEMANTIC_RECALL` not set; embedding pipeline (currently per-session summary) executed.

Issue: Docker build fails on Alpine compiling wheels.
- Add any missing build deps; or switch base image to `python:3.11-slim` for easier wheels.

---
## 19. Roadmap / Future Enhancements
Planned:
- Guest & Communication Agent reintegration (WhatsApp / email automations)
- Collaboration & Consensus workflows (paired decision tasks)
- Redis caching for smart context & predictive prefetch
- ML-based intent classifier (replace keyword heuristics)
- Image generation & mood board enrichment (already scaffolded with `image_artifacts`)
- Vendor portal (staff logins + task coordination)
- Fine-grained RLS policies & audit logging
- A/B testing of context compression strategies
- Automated budget anomaly detection

---
## 20. License

This project is currently unlicensed. We plan to add a `LICENSE` file (e.g., MIT or Apache-2.0) at the repository root in the near future to specify the terms of use and distribution.

---
## 21. Contributing Guidelines

We welcome contributions to Sanskara AI! By contributing, you help us build a more robust and comprehensive wedding planning assistant. Please follow these guidelines to ensure a smooth and effective collaboration process.

### How to Report Bugs

If you find a bug, please open an issue on our GitHub repository. When reporting a bug, provide as much detail as possible:

*   **Clear and concise description:** Explain the bug and its impact.
*   **Steps to reproduce:** Provide numbered steps to reliably reproduce the issue.
*   **Expected behavior:** Describe what you expected to happen.
*   **Actual behavior:** Describe what actually happened, including any error messages or stack traces.
*   **Environment:** Specify your operating system, Python version, and any relevant dependencies.

### How to Suggest New Features

We love new ideas! If you have a feature suggestion:

*   Open an issue on GitHub.
*   Clearly describe the feature, its purpose, and how it would benefit users.
*   Explain any potential challenges or alternative approaches.

### Code Style Guidelines

To maintain code quality and consistency:

*   **Python:** Adhere to [PEP 8](https://www.python.org/dev/peps/pep-0008/) conventions. We use `Black` for code formatting and `Flake8` for linting. Please run these tools before submitting a Pull Request:
    ```bash
    pip install black flake8
    black .
    flake8 .
    ```
*   **SQL:** Follow a consistent style for SQL queries, favoring readability and clarity.

### Pull Request (PR) Process

1.  **Fork the repository** and clone your fork.
2.  **Create a new branch** from `main` for your changes: `git checkout -b feature/your-feature-name` or `git checkout -b bugfix/your-bug-description`.
3.  **Implement your changes.** Ensure your code adheres to the [Code Style Guidelines](#code-style-guidelines).
4.  **Write tests** for your changes. All new features and bug fixes should be accompanied by appropriate unit and/or integration tests.
5.  **Run all tests** to ensure no existing functionality is broken: `cd sanskara && pytest -q`.
6.  **Commit your changes** with clear and concise commit messages. Follow Conventional Commits if possible (e.g., `feat: Add new feature`, `fix: Resolve bug`).
7.  **Push your branch** to your fork.
8.  **Open a Pull Request** against the `main` branch of the original repository.
    *   Provide a descriptive title and detailed explanation of your changes.
    *   Reference any related issues (e.g., `Closes #123`).
    *   Ensure all automated checks (CI/CD) pass.
9.  **Address feedback** from reviewers promptly.

Thank you for contributing!

---
## Quick Reference Cheat Sheet
Run API: `python main.py`
Health: `curl http://localhost:8765/health`
Onboard (first partner): `POST /onboarding/submit`
Fetch Wedding: `GET /weddings/{id}`
WebSocket: `ws://localhost:8765/ws?user_id=<uuid>`
Tests: `pytest -q`
Schema: `docs/design/overall_schema.sql`
