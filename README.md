# The Lenny Growth Assistant

A grounded PM/growth assistant over 269 episodes of Lenny's Podcast — built as a Forward Deployed Engineer take-home for Oogway Labs. Ask grounded questions, get cited answers, and turn threads into finished artifacts (a Ship 30 for 30 essay, a growth experiment brief) instead of chat bubbles that go nowhere.

Full product rationale: `PRD.md` · Technical depth: `architecture.md` · UI/UX: `design.md` · QA: `test-plan.md`

## Architecture overview

FastAPI backend + three skills (grounded Q&A, Ship 30/30 essay, growth brief) + Postgres/pgvector (hybrid dense + keyword retrieval) + React frontend with a sandboxed Artifact Viewer. Cloud inference via Groq, local inference via Ollama, switchable at runtime. Skills/routing follow the Claude Agent SDK's shape; inference is native HTTP, not the SDK package. Full diagram and schema in `architecture.md`.

## Prerequisites

- Docker + Docker Compose
- A free [Groq API key](https://console.groq.com) (no card required)
- [Ollama](https://ollama.com) installed **natively on the host**, not in a container (see note below)
- `git`

No paid service is required anywhere in this stack.

**On an 8GB Apple Silicon Mac (this project's reference machine) specifically:** run Ollama as a native macOS install, not inside Docker Compose. Docker Desktop on Mac runs containers in a Linux VM with no Metal GPU passthrough, so an Ollama container would be slow *and* would duplicate memory pressure that's already tight at 8GB total. The backend (in Docker) reaches native Ollama via `http://host.docker.internal:11434`. On Linux, Ollama can run as a normal compose service instead — see `docker-compose.linux.yml`.

## Installation

```bash
git clone https://github.com/Venkat-Kolasani/Lenny-Growth-Assistant.git
cd Lenny-Growth-Assistant
cp .env.example .env      # fill in GROQ_API_KEY at minimum
ollama serve &             # if not already running natively
ollama pull llama3.2:3b
ollama pull nomic-embed-text
docker compose up
```

First boot of Postgres applies `backend/db/init/01_schema.sql`. Then ingest transcripts (needs host Ollama with `nomic-embed-text`):

```bash
python scripts/ingest.py           # skip contextual prefixes (Day-1 default)
python scripts/ingest.py --contextualize   # one LLM sentence per episode, then re-embed
```

## Environment variables

| Variable | Required | Default | Notes |
|---|---|---|---|
| `GROQ_API_KEY` | Yes | — | Free tier at console.groq.com, ~30 req/min |
| `DATABASE_URL` | No | local compose Postgres via localhost from the host; compose overrides to the `postgres` hostname inside the backend container | Point at Supabase instead if preferred (see note below) |
| `OLLAMA_BASE_URL` | No | `http://127.0.0.1:11434` on the host; compose sets `http://host.docker.internal:11434` for the backend container | Native host Ollama on Mac; swap for `http://ollama:11434` if using the Linux compose file |
| `OLLAMA_MODEL` | No | `llama3.2:3b` | Sized for an 8GB M3 MacBook Pro — a full 7-8B model is too tight alongside Docker + OS on 8GB total. Size up if your machine has more RAM. |
| `OLLAMA_EMBED_MODEL` | No | `nomic-embed-text` | ~274MB, negligible RAM impact either way |
| `DEFAULT_MODEL_PROVIDER` | No | `groq` | `groq` \| `ollama` \| `cloudflare` |
| `CLOUDFLARE_ACCOUNT_ID` / `CLOUDFLARE_API_TOKEN` | No | — | Optional third free cloud adapter (Workers AI, 10k neurons/day) — fallback if Groq's rate limit is hit mid-demo |
| `ANTHROPIC_API_KEY` | No | — | Reserved only. No Anthropic adapter ships in this repo (Anthropic has no ongoing free API tier). See `architecture.md` §4. |
| `MODEL_TIMEOUT_SECONDS` | No | `60` | Client-side cutoff for every provider call. A slow or hung model returns a readable error instead of a hung request (assignment §5). |

`.env.example` ships with every variable above and safe placeholders — never commit a real `.env`.

**On Supabase:** it works fine here (pgvector included), but its free tier pauses a project after 7 days of inactivity, which can bite a delayed review. Local Postgres is the default for that reason; swap `DATABASE_URL` if you'd rather use managed hosting.

## Local model setup (Ollama)

Install Ollama natively (not via Docker — see the prerequisites note above), then:

```bash
ollama pull llama3.2:3b
ollama pull nomic-embed-text
```

`llama3.2:3b` is the default because it's realistic on an 8GB machine; if you're on a machine with more headroom, `llama3.1:8b` or larger will give noticeably better answer quality — just update `OLLAMA_MODEL` in `.env`.

## Cloud model setup (Groq)

Create a free key at console.groq.com, drop it into `.env` as `GROQ_API_KEY`. No payment method needed. Free tier is rate-limited (~30 req/min) — the client retries with backoff automatically if you hit it. Default chat model is `openai/gpt-oss-120b` (Groq retired `llama-3.3-70b-versatile` on 16 Aug 2026); override with `GROQ_MODEL`.

## Run commands

```bash
docker compose up              # full stack
docker compose up backend      # backend only, useful while iterating on frontend
python scripts/ingest.py       # re-run transcript ingestion manually
python -m eval.run             # run the retrieval eval harness, prints precision against golden set
```

## Tests

```bash
docker compose exec backend pytest          # automated backend tests
python -m eval.run                            # retrieval quality, standalone
```

Manual UI test plan lives in `test-plan.md`.

## Agent transcripts

`agent-transcripts/` is assignment deliverable #6 — required, including failed attempts. Session logs are written as we work, not reconstructed on submission day. How to capture and what to strip: `agent-transcripts/README.md`.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Startup hangs on first run | Ingestion embedding a large transcript corpus, or Ollama still pulling a model | Expected once; `docker compose logs backend`. Confirm native Ollama with `ollama list` on the host |
| 429 from chat endpoint | Groq free-tier rate limit hit | Client retries automatically, then fails over to Cloudflare if configured; switch to Ollama if it persists |
| Chat spinner never finishes | Model call hung / exceeded client timeout | UI should surface "didn't respond in time" rather than spin forever; retry or switch provider |
| Chat works, no citations ever appear | Ingestion didn't run / DB empty | `docker compose logs backend`, then re-run `python scripts/ingest.py` |
| "Local model isn't running" | Host Ollama not up, or model not pulled | `ollama serve`, then `ollama list` — you should see `llama3.2:3b` and `nomic-embed-text`. On Linux using `docker-compose.linux.yml`, check the `ollama` service instead |
| Postgres connection errors | Port conflict with a local Postgres install | Change the exposed port in `docker-compose.yml` |

## Data source & attribution

Transcripts from the [Lenny's Podcast / Newsletter transcript repository](https://github.com/ChatPRD/lennys-podcast-transcripts), used for grounding only — this project doesn't redistribute the transcripts beyond citing back to their source.

## Project structure

```
lenny-growth-assistant/
├── backend/
│   ├── app/
│   │   ├── api/            # FastAPI routers
│   │   ├── agent/          # skills + routing (SDK-shaped, native inference)
│   │   ├── ingestion/      # transcript loader, chunker, embedder
│   │   ├── retrieval/      # hybrid search, RRF, eval harness
│   │   └── models.py
│   ├── tests/
│   └── Dockerfile
├── frontend/
│   ├── src/
│   └── Dockerfile
├── eval/golden_set.json
├── scripts/ingest.py
├── docker-compose.yml
├── .env.example
├── PRD.md · architecture.md · design.md · test-plan.md
├── AGENTS.md · CLAUDE.md · handoff.md · docs.md · prompts.md
├── agent-transcripts/
└── .cursor/                 # Ponytail overlay; does not replace AGENTS.md
```
