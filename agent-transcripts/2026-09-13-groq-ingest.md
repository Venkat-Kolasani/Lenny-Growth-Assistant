# Session — 13 Sep 2026 — Groq key, model swap, ingest

**Agent:** Cursor (Grok 4.6) · **Status:** Groq qa/essay/brief proven in UI; full ingest running

## What we tried

User added `GROQ_API_KEY` to `.env` and asked to test, push remaining files, and continue. Recreated the backend so compose picked up the key. First Groq call 404'd: `llama-3.3-70b-versatile` is gone on this free/developer key (Groq shutdown 16 Aug 2026). Listed `/v1/models` from inside the backend container (host Python SSL failed), switched default to Groq's documented replacement `openai/gpt-oss-120b`. Then ran live `qa`, essay, and growth brief. Started `python3 scripts/ingest.py` with no `--limit`. Wrote the retrieval eval harness.

## What worked

- `/health/dependencies` showed `groq_api_key.ok` after recreate.
- Groq `qa` on acquisition channels: 8 citations, all Adam Grenier, grounded answer.
- Ship 30/30 + growth brief persisted as artifacts; UI rendered the brief (Situation / Audit POV / experiment) and citation chips.
- `pytest`: 24 passed.
- Ingest underway: 303 episodes, host Ollama embeddings.

## What failed, and how it was corrected

1. **`GROQ_API_KEY` in `.env` was ignored until backend recreate.** pydantic-settings reads env at process start; compose `env_file` is injected at container create.
2. **Llama 3.3 70B 404.** Not a bad key — the model ID is retired. Default is now `openai/gpt-oss-120b`, overridable with `GROQ_MODEL`.
3. **Host `urllib` SSL cert verify failed** listing Groq models. Used the backend container's httpx instead. Did not disable TLS on the host.
4. **Essay skill returned empty content.** gpt-oss fills a `reasoning` field first; `max_tokens=4096` was consumed before `content`. Set `reasoning_effort: "low"` and raised the writing cap.
5. **Did not commit `.env`.** Key length checked only; value never logged.

## Not done this session

Ingest of all 303 episodes still running at wrap. `python -m eval.run` not executed yet (would fight Ollama with ingest). Cloudflare failover, structured logs, demo video still next.
