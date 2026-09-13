# Session — 13 Sep 2026 — submission audit vs assignment

**Agent:** Cursor (Grok 4.6) · **Status:** product built; not submission-ready (no demo video)

## What we tried

Read the assignment in full, then `main` (only branch). Scored every §6 deliverable and §8 rubric item. Extra checks the brief forgets: `agent-transcripts/` written as-you-go, and model timeout as its own resilience case (not folded into Ollama-down / 429 / empty retrieval / DB).

## What worked

- App is real: FastAPI, Postgres/pgvector, three skills, three-pane UI, sandboxed artifacts, Groq/Ollama toggle, hybrid RRF, eval **81.82% (27/33)**.
- Unique touch is the Oogway-shaped `growth_brief` + work-product framing against 20+ existing Lenny chatbots — not a novel RAG trick.
- Timeouts are first-class: `MODEL_TIMEOUT_SECONDS`, 504, readable UI copy, tests on Groq/Ollama/Cloudflare.
- Transcripts folder has nine prior sessions including failures (Llama 3.3 404, eval 48%→81.82%).

## What failed, and how it was corrected

1. **Not submission-ready.** Deliverable #8 (camera-on YouTube demo) is missing. Cannot invent a video. Left as Venkat's job.
2. **Docs claimed a wired Claude Agent SDK / Anthropic adapter.** `requirements.txt` has no SDK; there is no `anthropic.py`. Corrected in this session: architecture, AGENTS, docs.md, README, `.env.example` now say reserved env var, not a shipped adapter. Did not invent an SDK integration.
3. **README ingest assumed host Python deps.** Added `pip install -r backend/requirements.txt`. Design said tokens stream; they do not — corrected.

## Not done (do not fake)

- YouTube demo
- Wiring `claude-agent-sdk` (grading risk, documented; same-day add if Venkat wants the letter of §3.1)
- Clean-clone on a fresh machine
- Cloudflare live 429 (credentials empty)

Full verdict: `docs/submission-audit.md` in the project store (not this repo).
