# handoff.md

Living state of the build. Newest entry on top. Read the top entry at the start of every session before doing anything else — it's the single source of truth for "where did we leave off."

**Entry template:**
```
## Session N — <date>
**Done this session:** ...
**Current state:** ... (what runs, what doesn't)
**Next up:** ... (concrete, in order)
**Open decisions / blockers:** ... (or "none")
```

---

## Session 3 — Sat 13 Sep 2026 (plan review + git init)

**Done this session:** Read the assignment and every planning doc. Confirmed the plan is good and unique (write-up in `docs.md` — uniqueness is the work-product framing against 20+ existing Lenny projects, not a novel RAG trick). Initialized git; three focused commits so far: planning baseline, `agent-transcripts/` capture protocol (assignment deliverable #6, now in all five `prompts.md` templates), model-timeout as its own resilience case (assignment §5). Closed leftover Session-1 drift: Compose topology no longer lists Ollama as a Mac service, `design.md` chip uses `llama3.2:3b`, README troubleshooting talks to host Ollama, PRD hardware assumption marked resolved. Documented a Day-1 ingestion fallback: skip contextual prefixes if the 3B batch would blow the weekend.

**Current state:** Docs + git only. No application code, no `docker-compose.yml`, no schema. Due date is **15 Sep 2026 EOD**.

**Next up** (start immediately, one commit per item):
1. Repo scaffold matching the tree in `README.md` (backend/frontend/eval/scripts stubs)
2. `docker-compose.yml` + `docker-compose.linux.yml` + `.env.example`
3. DB schema + migrations from `architecture.md` §2
4. Ingestion script: clone → parse → chunk → embed → load; contextualize is optional (`--contextualize`)
5. FastAPI health endpoints (`/health`, `/health/dependencies`)
6. `qa` skill working end-to-end against Groq only

**Open decisions / blockers:**
- Differentiator skill still `growth_brief`. Plan review: sharpen toward an Oogway-shaped audit/experiment one-pager if Venkat wants, before Day 2 — do not add a 4th skill.
- Confirm Cloudflare model string with `npx wrangler ai models list` at build time.
- Git is local-only so far; assignment requires a **public GitHub repo** before submission — push when Venkat asks, not before.

---

## Session 2 — Sat 13 Sep 2026 (planning, continued)

**Done this session:** Hardware confirmed (MacBook Pro, M3, 8GB RAM) — resolved the open question from Session 1. Finalized models: Groq `llama-3.3-70b-versatile` (cloud default), Ollama `llama3.2:3b` (local, sized for 8GB total RAM), `nomic-embed-text` (embeddings). Added Cloudflare Workers AI (`@cf/meta/llama-3.1-70b-instruct`, free, 10k neurons/day) as an automatic failover for Groq rate-limiting, not a manual option. Resolved how the agent layer stays free: Skills/routing architecture follows Claude Agent SDK patterns, but actual inference for the default path calls Groq/Ollama/Cloudflare directly rather than proxying through the SDK's Anthropic transport — Anthropic's API has no ongoing free tier, and disguising a third-party model as Anthropic via `ANTHROPIC_BASE_URL` is an unresolved ToS gray area. Also decided Ollama runs natively on the Mac host (no Docker GPU passthrough on Mac) rather than as a Compose service; a Linux compose variant containerizes it normally. `README.md`, `architecture.md`, `AGENTS.md` updated accordingly.

**Current state:** Still docs-only, nothing built.

**Next up:** Unchanged from Session 1's Day 1 list — repo scaffold, `docker-compose.yml` (+ `docker-compose.linux.yml` variant), DB schema/migrations, ingestion script, health endpoints, `qa` skill live on Groq.

**Open decisions / blockers:**
- Differentiator skill still `growth_brief`, still swappable if Venkat wants to change it before Day 2.
- Need to check `npx wrangler ai models list` at build time to confirm the exact Cloudflare Llama 3.3 model string is live on the account (documented as `llama-3.1-70b-instruct` as the confirmed-available fallback either way).

---

## Session 1 — Sat 13 Sep 2026 (planning)

**Done this session:** No code yet. Assignment analyzed, Oogway Labs researched (real site: an AI engineering consultancy — audit → build → production model, "outcome-driven, not over-engineered" as a stated principle), the transcript repo's structure and 20+ existing prior-art projects reviewed. Product direction, architecture, and RAG design decided and written up across `PRD.md`, `architecture.md`, `design.md`. Free-tools-only constraint locked in and checked against Groq/Supabase/Ollama free-tier realities.

**Current state:** Nothing built. Docs only.

**Next up** (per `PRD.md` §5, Day 1 / "Sat"):
1. Repo scaffold matching the tree in `README.md`
2. `docker-compose.yml` skeleton (backend, postgres+pgvector, ollama, frontend containers — even as stubs that boot)
3. DB schema + migrations from `architecture.md` §2
4. Ingestion script: clone transcript repo → parse frontmatter → chunk → contextualize (Ollama) → embed (Ollama) → load into `transcript_chunks`
5. FastAPI health endpoints (`/health`, `/health/dependencies`)
6. `qa` skill working end-to-end against Groq only (Ollama toggle comes Day 2)

**Open decisions / blockers:**
- Local machine RAM/GPU not yet confirmed — `OLLAMA_MODEL` currently defaults to `llama3.1:8b` in `AGENTS.md`/`README.md`; revisit once confirmed (`PRD.md` §7).
- Differentiator skill is `growth_brief` — open to being swapped per `PRD.md` §7 if Venkat wants a different pick before Day 2 build starts.
