# AGENTS.md

Read this file in full before touching this repo. It's the standing reference for any coding agent (or Venkat) picking up work in a new session — what's decided, what's not, and the protocol for keeping `handoff.md` and `docs.md` honest as work progresses.

## What this project is

"The Lenny Growth Assistant" — a Forward Deployed Engineer take-home for Oogway Labs. Full context: `PRD.md` (product/discovery), `architecture.md` (technical), `design.md` (UI/UX), `test-plan.md` (QA). Read those before making a decision that contradicts one of them — if a change is genuinely warranted, update the doc in the same session, don't let it drift.

## Session protocol — do this every time

1. **Start of session:** read this file, then `handoff.md` for current state (what's built, what's next, open blockers). If picking up mid-task, `handoff.md` should tell you exactly where the last session stopped.
2. **During the session:** work from `PRD.md` §5's day-by-day plan unless `handoff.md` says otherwise.
3. **On any non-obvious decision** (a trade-off, a deviation from the docs, a workaround): append a short rationale entry to `docs.md` — this is Venkat's interview prep, so write it as "why," not just "what."
4. **As you go, not at the end:** append to `agent-transcripts/` — this is assignment deliverable #6 (required, including failed attempts and how they were corrected). Reconstructing it on submission day is how it gets forgotten. Strip secrets and API keys before writing. Format and sanitization rules live in `agent-transcripts/README.md`.
5. **End of session or any meaningful milestone:** update `handoff.md` — what changed, what's next, anything blocking. Don't leave it stale; the next session (possibly a fresh context window) depends on it being accurate.

Ready-to-paste prompts that enforce this are in `prompts.md` — use them rather than freehand session openers. Every prompt in that file also requires a `agent-transcripts/` write, on purpose.

## Stack — already decided, don't relitigate without a documented reason

- **Backend:** FastAPI
- **Agent layer:** Claude Agent SDK (Python), Skills-based — not Pi Coding Agent. Rationale in `architecture.md` §4.
- **Persistence + vectors:** Postgres + pgvector, one instance — not a separate Chroma/Neo4j service. Rationale in `architecture.md` §1.
- **Default DB target:** local Postgres via Docker Compose, not Supabase-hosted (free-tier inactivity pause risk). Supabase is a documented *optional* alternative.
- **Embeddings:** Ollama-served (`nomic-embed-text`), not a separate sentence-transformers dependency.
- **Cloud LLM:** Groq, `openai/gpt-oss-120b` (Groq's current free-tier replacement after `llama-3.3-70b-versatile` shut down 16 Aug 2026; override with `GROQ_MODEL`). **Cloudflare Workers AI** (`@cf/meta/llama-3.1-70b-instruct`, 10k free neurons/day) added as an automatic fallback for when Groq rate-limits mid-session — not a manual toggle, a failover. Anthropic adapter exists but is optional/non-default: Anthropic has no ongoing free API tier, only a one-time 30-day trial credit.
- **Local LLM:** Ollama, `llama3.2:3b` — confirmed against the actual dev machine (MacBook Pro, M3, 8GB RAM); an 8B model was the original placeholder but is too heavy alongside Docker + OS on 8GB total. **Ollama runs natively on the host, not inside Docker Compose** — Docker Desktop on Mac has no Metal GPU passthrough, so containerizing it would be both slower and worse on the memory budget that's already tight. Backend reaches it via `host.docker.internal:11434`.
- **Agent-layer model routing:** the Skills/subagent/tool-use *architecture* follows the Claude Agent SDK's patterns; actual inference for the free default path calls Groq/Ollama/Cloudflare natively rather than proxying them through the SDK's Anthropic transport (`ANTHROPIC_BASE_URL` tricks sit in an unresolved ToS gray area — see `architecture.md` §4). Full Agent SDK usage is wired in as a genuine, optional adapter for anyone supplying their own Anthropic key.
- **Retrieval:** hybrid dense (pgvector) + sparse (Postgres `tsvector`) fused with RRF, plus contextual chunk prefixes generated at ingestion time. Not a knowledge graph — see `PRD.md` §2.5 for why that's explicitly out of scope.
- **Frontend:** React, three-pane layout (sessions / chat / artifact viewer).
- **Artifact security:** Markdown sanitized, never raw-HTML'd; generated HTML/CSS renders in a script-disabled sandboxed iframe. Full spec in `architecture.md` §6 — implement exactly that, it's a graded requirement (assignment §4.3).
- **Budget constraint:** zero. Every dependency added must have a genuinely free tier or run locally — check before adding anything new.

## Repo structure

See the tree in `README.md` — keep new files inside it rather than inventing new top-level folders without updating that tree.

## Skills — exactly three, don't add a fourth without updating PRD.md §2.5

`qa` (grounded Q&A), `ship30_essay` (encoded Ship 30/30 framework — see `architecture.md` §4 for the specific rules to encode, not just "write in that style"), `growth_brief` (the differentiator — swappable per `PRD.md` §7 if Venkat decides to change it).

## Testing bar

Every PR-sized chunk of work should leave `pytest` passing and, if it touches retrieval, `python -m eval.run` reporting a number — not just "looks right in the UI." Full plan in `test-plan.md`.

## Coding style overlay

Ponytail (lazy senior) is always-on via `.cursor/rules/ponytail.mdc` and the skills under `.cursor/skills/ponytail*`. It governs how much code we write, not the stack or product decisions in this file. **Do not replace this `AGENTS.md` with Ponytail's** — theirs is a generic YAGNI ruleset; ours is the FDE session protocol.
