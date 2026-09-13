# docs.md — decision rationale & interview prep

Not graded, not for the evaluator — this is for you. Every non-obvious call, written as the answer you'd give if someone pushed back on it in an interview. Append to this as new decisions get made; don't let it go stale.

## "Why isn't this just another Lenny chatbot?"

Because the transcript repo's own README already lists 20+ public projects built on this exact dataset — graph RAG, citation tools, persona mentors, semantic explorers, two MCP servers. A meaningfully large share of the ~800-1000 other candidates will independently land on "vector search + citations + chat," because that's the obvious read and it's been done a dozen times publicly. The reframe: this is scoped as an **internal work-product tool** (skills that generate an essay or a growth brief you can actually paste into a deliverable), not a public exploration toy — a gap none of those 20 projects fill, and one that matches the brief's own language about what the user actually wants ("reusable written content... without needing to understand prompts").

## "What did researching Oogway Labs actually change?"

Oogway Labs is a real AI engineering consultancy — audit → build (4-6 week "quick wins") → production support, https://oogwaylabs.com. Two things from their own site directly shaped this build:

- **"Outcome-driven, not over-engineered... we use the simplest tool that works, sometimes that's a prompt, sometimes it's no AI at all."** This is the direct justification for *not* building a knowledge graph, *not* reaching for a 4th skill, and reading "production scale" as engineering discipline rather than literal infra scale. It's not a guess dressed up as a principle — it's their stated value, found before the build started.
- **"RAG & Memory Architecture" and "AI Reliability: Evals, Governance, Cost" are two of their seven named services.** That's a strong signal the evaluator has real, specific opinions about what good RAG and good evals look like — which is the direct justification for the retrieval eval harness being a first-class part of the build rather than an afterthought, and for cost/rate-limit handling being written down explicitly rather than assumed away.

## "Why FastAPI + Postgres/pgvector instead of a dedicated vector DB?"

One stateful service instead of two or three. Every extra container is one more thing a fresh evaluator's `docker compose up` can fail on — and "operability" (reproducibility, resilience) is graded as heavily as the RAG itself (assignment §8). Also deliberately *not* repeating the Neo4j-based approach used on a past project (MemoryWeave) — reaching for the same tool again shows less range than picking the right-sized tool for this constraint.

## "Why Groq if the brief says 'such as Anthropic Claude or OpenAI'?"

Groq is a cloud inference host for open-weight models (Llama, GPT-OSS, Qwen) on custom LPU chips — it satisfies "cloud provider" functionally (fast, hosted, not local) even though it isn't literally Anthropic/OpenAI-branded. Documented explicitly as an assumption in `PRD.md` §2.3 rather than silently substituted. The model-provider interface is written adapter-style specifically so a same-day Anthropic adapter is possible if that gap needs closing — cheap insurance, not a redesign.

## "What's your success metric, and why that one?"

Two: retrieval precision against a ~30-question golden set (operational — is the RAG actually grounding correctly, independent of prose quality), and artifact completion rate (product — did the session produce the thing the user actually came for, not just chat). Chose an eval harness deliberately because almost nobody will bother building one in three days, and it's the cheapest way to turn "we handled hallucination" from a claim into a number.

## "What would you do with more time or budget?"

Cross-encoder reranking on the retrieval fusion step, a live transcript-refresh pipeline instead of a static ingestion snapshot, a 4th skill (candidates considered: a PRD-1-pager generator, an interview-prep-question generator mirroring Lenny's own interviewing style), and exposing the assistant itself as an MCP server (two other community projects already did this for the same dataset — Lenny MCP, Lenny for Claude — so it's a known-good idea, just not core-path under this deadline).

## "Why llama3.2:3b locally instead of the bigger model you first suggested?"

The first pass defaulted to a 7-8B model before I'd confirmed hardware. Once the actual machine turned out to be an 8GB M3 MacBook Pro, that default stopped being safe — Docker Desktop's VM and macOS itself already claim a real share of 8GB, and a live demo that starts swapping mid-answer is a worse failure mode than a slightly weaker local model. Sized down to `llama3.2:3b` instead, and moved Ollama to run natively on the host rather than in Docker — Docker Desktop on Mac has no Metal GPU passthrough anyway, so containerizing it would've been slower *and* heavier on the same scarce memory.

## Plan review (13 Sep 2026) — is this good, and is it unique?

**Yes, with two caveats worth saying out loud.** The plan is strong enough to build against and distinct enough from the obvious "Lenny chatbot" that a tired evaluator will have already seen. It is *not* unique because of a novel RAG trick; it is unique because of the discovery work and the FDE framing.

**What is actually unique (keep defending these):**

- **Prior-art check against the dataset's own README.** 20+ public projects already exist on these exact 269 episodes. Almost nobody else will have read that list and then *not* built another citation chatbot. The reframe — internal work-product tool that ships an essay or a growth brief you can paste into a deliverable — is the gap those projects leave, and it matches the brief's own language ("reusable written content… without needing to understand prompts").
- **Oogway-shaped, not generic-AI-demo-shaped.** Their site's "outcome-driven, not over-engineered" line plus named services in RAG/evals/cost is why there is no Neo4j graph, no 4th skill, a real golden-set eval, and a $0 stack with documented free-tier numbers. That is customer judgment, which is the first scoring criterion.
- **Honest Agent SDK split.** Using the SDK's skill/subagent architecture while calling Groq/Ollama/Cloudflare natively, and wiring a real Anthropic adapter only for people with a key, is a more defensible FDE answer than either "ignore the SDK requirement" or "pretend Anthropic is free via `ANTHROPIC_BASE_URL`."
- **Hardware-realistic local demo.** `llama3.2:3b` on host-native Ollama because the machine is an 8GB M3, not because 3B is fashionable. Evaluators running the local path will notice if the demo swaps; they will not notice a missing 8B.

**What is good but not unique (still do them; they are graded):** hybrid dense+sparse with RRF, contextual chunk prefixes, sandboxed artifact viewer, session persistence, Groq/Ollama toggle. These are the price of entry. The eval harness and the Cloudflare-as-failover (not as a third toggle) are the two "price of entry, done slightly better" items.

**Caveats — do not paper over these:**

1. **Calendar.** Due 15 Sep 2026 EOD; today is 13 Sep; nothing is built. The original Sat/Sun/Mon plan assumed a 12 Sep start. Day 1 (scaffold → ingest → `qa` on Groq) has to start immediately, and contextual-prefix generation over 269 episodes on `llama3.2:3b` can eat the remaining weekend by itself. Fallback already implied by "stretch, not core": **first ingestion pass can skip contextual prefixes** (embed the bare chunk) so `qa` ships; prefixes are a quality rerun, not a blocker. Recorded here so we don't treat the full pipeline as non-negotiable on Day 1.
2. **SDK grading risk.** An evaluator who reads "build the agent layer using the Claude Agent SDK" as "the runtime must be the SDK" may ding the native-Groq path. Mitigation: the Anthropic adapter is real, documented, and demo-able with a key; the PRD assumption is explicit. Do not hide the split.
3. **`growth_brief` is a moderate differentiator.** It is better than a 4th shallow skill, but it is still "another markdown template." If there is time to sharpen it before Day 2, aim it at an Oogway-shaped artifact (a one-page audit POV / experiment the FDE would actually hand a client) rather than a generic growth-experiment worksheet. Open until Venkat confirms; do not invent a 4th skill.
4. **Doc drift caught in this review** (fixed in the same session): `architecture.md` §8 still listed Ollama as a Compose service; `design.md` still showed `llama3.1:8b` on the model-switch chip; `PRD.md` §2.3 still said hardware was unconfirmed; README troubleshooting still told the evaluator to `docker compose logs ollama`. Those leftovers would have made the handoff look internally confused.

**Build order after this review:** do not add more planning. Next commit starts the repo scaffold in `PRD.md` §5 / `handoff.md` Day 1 list.

## "Why add Cloudflare if Groq was already the pick?"

Not a replacement — a failover. Groq's free tier is ~30 requests/minute, which is thin margin if an evaluator hammers the demo. Cloudflare Workers AI is genuinely free (10k neurons/day, no card) and sits behind the same provider interface, so adding it is cheap: if Groq 429s, the client fails over automatically instead of surfacing a rate-limit error mid-demo.

## "You said 'Claude Agent SDK' — so is Anthropic footing the bill?"

No, and worth being upfront about this if asked directly: Anthropic's API has no ongoing free tier, only a one-time 30-day trial credit — not something to build a "free" project on. So the Agent SDK's *architecture* (skills, subagent boundaries, the tool-use loop) shapes how the agent layer is built, but the actual model calls for the default path go straight to Groq/Ollama/Cloudflare's own APIs. There's also a real, still-open question (an unanswered GitHub issue) about whether disguising a non-Anthropic model behind Anthropic's API shape via `ANTHROPIC_BASE_URL` is even within Anthropic's terms — so that route was avoided on purpose, not just for cost reasons. The SDK is still genuinely wired in as an optional adapter for anyone with their own Anthropic key.

## Free-tier numbers, for when someone asks "does this actually cost nothing?"

Groq free tier: ~30 requests/min, ~1,000/day, no card required, indefinite (not a trial). Supabase free tier: 500MB Postgres, pgvector included, pauses after 7 days idle — the reason local Postgres is the default, not a knock against Supabase itself. Ollama: fully local, zero marginal cost, the ceiling is your hardware not your wallet.

## "Why Ponytail, and why didn't you overwrite AGENTS.md?"

Ponytail is a coding-style overlay (YAGNI ladder, shortest working diff) so the agent doesn't spend Day 1 inventing layers we don't need. Cursor's adapter is `.cursor/rules/ponytail.mdc` plus the skills under `.cursor/skills/` — that is the documented install for this host. Ponytail also ships its own `AGENTS.md`; replacing ours with it would delete the FDE session protocol (handoff, docs, agent-transcripts, locked stack). So they sit side by side: this repo's `AGENTS.md` for *what* we build, Ponytail for *how little code* it takes.

## "Why a SQL init file instead of Alembic?"

The evaluator's first `docker compose up` has to create the schema with zero extra commands. `backend/db/init/*.sql` on Postgres's docker-entrypoint is one file and one boot. We are not running online migrations for a two-day take-home; if the schema changes we reset the volume. Alembic is the upgrade path if this ever lives past submission.
