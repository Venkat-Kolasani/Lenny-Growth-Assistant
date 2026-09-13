# The Lenny Growth Assistant

A grounded PM/growth assistant over 269 episodes of Lenny's Podcast — built as a Forward Deployed Engineer take-home for Oogway Labs. Ask grounded questions, get cited answers, and turn threads into finished artifacts (a Ship 30 for 30 essay, a growth experiment brief) instead of chat bubbles that go nowhere.

Full product rationale: `PRD.md` · Technical depth: `architecture.md` · UI/UX: `design.md` · QA: `test-plan.md`

## Architecture overview

FastAPI backend + Claude Agent SDK (skills: grounded Q&A, Ship 30/30 essay, growth brief) + Postgres/pgvector (hybrid dense + keyword retrieval) + React frontend with a sandboxed Artifact Viewer. Cloud inference via Groq, local inference via Ollama, switchable at runtime. Full diagram and schema in `architecture.md`.

## Prerequisites

- Docker + Docker Compose
- A free [Groq API key](https://console.groq.com) (no card required)
- [Ollama](https://ollama.com) installed **natively on the host**, not in a container (see note below)
- `git`

No paid service is required anywhere in this stack.

**On an 8GB Apple Silicon Mac (this project's reference machine) specifically:** run Ollama as a native macOS install, not inside Docker Compose. Docker Desktop on Mac runs containers in a Linux VM with no Metal GPU passthrough, so an Ollama container would be slow *and* would duplicate memory pressure that's already tight at 8GB total. The backend (in Docker) reaches native Ollama via `http://host.docker.internal:11434`. On Linux, Ollama can run as a normal compose service instead — see `docker-compose.linux.yml`.

## Installation

```bash
git clone <repo-url>
cd lenny-growth-assistant
cp .env.example .env      # fill in GROQ_API_KEY at minimum
ollama serve &             # if not already running natively
ollama pull llama3.2:3b
ollama pull nomic-embed-text
docker compose up
```

First boot runs transcript ingestion automatically — expect it to take longer than subsequent starts.

## Environment variables

| Variable | Required | Default | Notes |
|---|---|---|---|
| `GROQ_API_KEY` | Yes | — | Free tier at console.groq.com, ~30 req/min |
| `DATABASE_URL` | No | local compose Postgres | Point at Supabase instead if preferred (see note below) |
| `OLLAMA_BASE_URL` | No | `http://host.docker.internal:11434` | Native host Ollama on Mac; swap for `http://ollama:11434` if using the Linux compose file |
| `OLLAMA_MODEL` | No | `llama3.2:3b` | Sized for an 8GB M3 MacBook Pro — a full 7-8B model is too tight alongside Docker + OS on 8GB total. Size up if your machine has more RAM. |
| `OLLAMA_EMBED_MODEL` | No | `nomic-embed-text` | ~274MB, negligible RAM impact either way |
| `DEFAULT_MODEL_PROVIDER` | No | `groq` | `groq` \| `ollama` \| `cloudflare` |
| `CLOUDFLARE_ACCOUNT_ID` / `CLOUDFLARE_API_TOKEN` | No | — | Optional third free cloud adapter (Workers AI, 10k neurons/day) — fallback if Groq's rate limit is hit mid-demo |
| `ANTHROPIC_API_KEY` | No | — | Optional adapter using your own Anthropic credit — Anthropic has no ongoing free API tier (only a one-time, 30-day trial credit), so this is never the default path |

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

Create a free key at console.groq.com, drop it into `.env` as `GROQ_API_KEY`. No payment method needed. Free tier is rate-limited (~30 req/min) — the client retries with backoff automatically if you hit it.

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
| Startup hangs on first run | Ollama pulling a multi-GB model | Expected once; check `docker compose logs ollama` |
| 429 from chat endpoint | Groq free-tier rate limit hit | Client retries automatically; switch to Ollama if it persists |
| Chat works, no citations ever appear | Ingestion didn't run / DB empty | `docker compose logs backend`, then re-run `python scripts/ingest.py` |
| "Local model isn't running" | Ollama container not up or model not pulled | `docker compose ps`, `ollama list` inside the container |
| Postgres connection errors | Port conflict with a local Postgres install | Change the exposed port in `docker-compose.yml` |

## Data source & attribution

Transcripts from the [Lenny's Podcast / Newsletter transcript repository](https://github.com/ChatPRD/lennys-podcast-transcripts), used for grounding only — this project doesn't redistribute the transcripts beyond citing back to their source.

## Project structure

```
lenny-growth-assistant/
├── backend/
│   ├── app/
│   │   ├── api/            # FastAPI routers
│   │   ├── agent/          # Claude Agent SDK skills + routing
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
└── agent-transcripts/
```
