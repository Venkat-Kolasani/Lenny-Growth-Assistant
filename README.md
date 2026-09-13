# The Lenny Growth Assistant

An internal work-product tool over **Lenny's Podcast** transcripts: ask grounded product and growth questions, get cited answers, and leave with a finished artifact (a Ship 30 for 30 essay or a one-page growth brief) instead of another chat thread that goes nowhere.

Built as a Forward Deployed Engineer take-home for [Oogway Labs](https://oogwaylabs.com). **Zero paid services** — Groq free tier + host Ollama + local Postgres.

| | |
|---|---|
| **UI** | http://localhost:5173 |
| **API** | http://localhost:8000 |
| **Health** | http://localhost:8000/health |
| **Docs** | [`docs/`](docs/) |

---

## Quick start

### 1. Prerequisites

- Docker Desktop (or Docker Engine + Compose v2)
- `git`
- A free [Groq API key](https://console.groq.com) (no card)
- [Ollama](https://ollama.com) installed **on the host** (not in Docker on Mac — see note below)
- Python 3.12+ on the host (for one-time ingest + optional eval)

**Mac / Apple Silicon note:** run Ollama natively. Docker Desktop has no Metal GPU passthrough; a containerized Ollama is slower and fights the same RAM budget. The backend container reaches host Ollama at `host.docker.internal:11434`. On Linux you can use `docker compose -f docker-compose.yml -f docker-compose.linux.yml up` instead.

### 2. Clone and configure

```bash
git clone https://github.com/Venkat-Kolasani/Lenny-Growth-Assistant.git
cd Lenny-Growth-Assistant

cp .env.example .env
# Edit .env and set GROQ_API_KEY=... (required for the default cloud path)
```

### 3. Pull local models

```bash
ollama serve          # if it is not already running
ollama pull llama3.2:3b
ollama pull nomic-embed-text
```

### 4. Start the stack

```bash
docker compose up --build
```

Wait until Postgres is healthy and the backend / frontend containers are up. First boot applies `backend/db/init/01_schema.sql` automatically.

| Service | URL |
|---|---|
| Home + workbench | http://localhost:5173 |
| API docs | http://localhost:8000/docs |
| Health | http://localhost:8000/health |

The UI opens on a short home page. Click **Enter** (or go to http://localhost:5173/#work) for the three-pane desk.

### 5. Ingest transcripts (required once)

The chat UI will start without citations until the corpus is loaded. From the **repo root**, with Ollama running on the host:

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r backend/requirements.txt

python scripts/ingest.py --limit 5 # smoke test (~1–2 min)
python scripts/ingest.py           # full corpus (~15–25 min, ~301 episodes)
```

Ingest clones [ChatPRD/lennys-podcast-transcripts](https://github.com/ChatPRD/lennys-podcast-transcripts) into `data/transcripts/` on first run, embeds with `nomic-embed-text`, and writes to local Postgres.

Optional quality pass (episode-level LLM prefixes, then re-embed):

```bash
python scripts/ingest.py --contextualize
```

### 6. Try it

1. Open http://localhost:5173 → **Enter**
2. Ask something grounded, e.g. *How do you build a high-performing growth team?*
3. Or ask for an artifact: *Write me a Ship 30/30 essay on activation for a B2B product*
4. Switch **Groq** ↔ **Ollama** in the chat header when you want local inference

---

## What you get

- **Grounded Q&A** with episode citations (guest + title); refuses when the transcripts do not cover it
- **Ship 30 for 30 essays** and **growth briefs** as first-class artifacts (Artifact pane; export as Markdown, Word, or PDF)
- **Hybrid retrieval:** dense (pgvector) + sparse (`tsvector`), fused with RRF
- **Model toggle:** Groq cloud (`openai/gpt-oss-120b`) or Ollama local (`llama3.2:3b`); optional Anthropic BYOK (`ANTHROPIC_API_KEY`); optional Cloudflare Workers AI failover on Groq 429
- **Artifact security:** sanitized Markdown; HTML in a script-disabled sandboxed iframe

---

## Environment variables

Copy `.env.example` → `.env`. Never commit a real `.env`.

| Variable | Required | Default | Notes |
|---|---|---|---|
| `GROQ_API_KEY` | Yes (cloud path) | — | Free tier at console.groq.com |
| `GROQ_MODEL` | No | `openai/gpt-oss-120b` | Override if Groq renames the free model again |
| `DATABASE_URL` | No | local Compose Postgres | Host scripts use `localhost`; the backend container is pointed at `postgres` |
| `OLLAMA_BASE_URL` | No | `http://127.0.0.1:11434` | Compose sets `http://host.docker.internal:11434` for the backend |
| `OLLAMA_MODEL` | No | `llama3.2:3b` | Sized for an 8GB M3 MacBook Pro |
| `OLLAMA_EMBED_MODEL` | No | `nomic-embed-text` | Used at ingest and query time |
| `DEFAULT_MODEL_PROVIDER` | No | `groq` | `groq` \| `ollama` \| `anthropic` |
| `CLOUDFLARE_ACCOUNT_ID` / `CLOUDFLARE_API_TOKEN` | No | — | Optional Groq-429 failover |
| `ANTHROPIC_API_KEY` | No | — | BYOK. Unlocks Anthropic in the UI. Not the free default |
| `ANTHROPIC_MODEL` | No | `claude-sonnet-4-5` | Used only when the Anthropic key is set |
| `MODEL_TIMEOUT_SECONDS` | No | `60` | Client-side cutoff per provider call |

**Supabase:** optional. Free-tier projects pause after inactivity, so local Postgres is the default.

---

## Tests and eval

```bash
docker compose exec backend pytest
source .venv/bin/activate          # if not already
python -m eval.run                 # retrieval guest precision: expected guest in top-k / 33
```

Manual UI checklist: [`docs/test-plan.md`](docs/test-plan.md).

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| No citations / empty answers about the corpus | Run `python scripts/ingest.py` with host Ollama + `nomic-embed-text` pulled |
| "Local model isn't running" | `ollama serve`, then `ollama list` should show `llama3.2:3b` and `nomic-embed-text` |
| Groq 429 / rate limit | Client retries; configure Cloudflare for failover, or switch the header to Ollama |
| Chat spinner never finishes | Should surface a timeout error; retry or switch provider |
| Postgres connection errors from ingest | Confirm `docker compose up` and that port `5432` is free; `.env` `DATABASE_URL` should use `localhost` |
| Frontend blank / old UI | Hard-refresh; Compose mounts `frontend/src` — `docker compose up --build frontend` if needed |
| Linux + Ollama in Compose | `docker compose -f docker-compose.yml -f docker-compose.linux.yml up --build` |

---

## Project structure

```
Lenny-Growth-Assistant/
├── README.md                 ← you are here
├── AGENTS.md · CLAUDE.md     ← pointers into docs/
├── .env.example
├── docker-compose.yml
├── backend/                  FastAPI, agent skills, retrieval, ingest
├── frontend/                 React (home + three-pane workbench)
├── eval/                     Retrieval golden set + runner
├── scripts/ingest.py         Host entrypoint for ingestion
├── data/transcripts/         Cloned on first ingest (gitignored content)
└── docs/                     All product, design, and process docs
    ├── PRD.md
    ├── architecture.md
    ├── design.md
    ├── test-plan.md
    ├── assignment.md
    ├── decisions.md
    ├── handoff.md
    ├── AGENTS.md
    ├── prompts.md
    └── agent-transcripts/    Assignment deliverable #6
```

---

## Documentation map

| Doc | Audience |
|---|---|
| [docs/PRD.md](docs/PRD.md) | Product discovery and acceptance criteria |
| [docs/architecture.md](docs/architecture.md) | Schema, APIs, retrieval, security |
| [docs/design.md](docs/design.md) | UI/UX and interaction states |
| [docs/test-plan.md](docs/test-plan.md) | QA strategy |
| [docs/decisions.md](docs/decisions.md) | Why each trade-off was made |
| [docs/agent-transcripts/](docs/agent-transcripts/) | Build log, including failed attempts |
| [docs/assignment.md](docs/assignment.md) | Original take-home brief |

---

## Data source

Transcripts from [Lenny's Podcast / Newsletter transcript repository](https://github.com/ChatPRD/lennys-podcast-transcripts), used for grounding. This project cites back to sources; it does not redistribute the corpus as a primary deliverable.
