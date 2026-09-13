# decisions.md — decision rationale & interview prep

Not graded as a named deliverable — this is interview prep. Every non-obvious call, written as the answer you'd give if someone pushed back on it in an interview. Append to this as new decisions get made; don't let it go stale. Lives under `docs/` with the rest of the product docs.

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

No. Anthropic has no ongoing free API tier. Skills/routing follow Agent SDK patterns; default inference is Groq/Ollama (Cloudflare on Groq 429). **BYOK Anthropic** is the official `anthropic` Messages API, not the `claude-agent-sdk` coding harness (CLI + tools — wrong shape for turn-based RAG). Set `ANTHROPIC_API_KEY` to unlock the toggle; without it the option is disabled and `POST .../provider` returns 400. No `ANTHROPIC_BASE_URL` disguise.

## "How is retrieval eval calculated?"

`python -m eval.run`: 33 golden questions, each with an `expected_guest`. After hybrid retrieve, **HIT** if that guest string is a case-insensitive substring of any top-k `episode_guest`. Precision = hits / 33. It measures retrieval, not prose. We do not rewrite the golden set to manufacture 90%. Guest+title embed rerank after RRF is a free extra signal on generic paraphrases; ceiling is still "no cross-encoder."

## Free-tier numbers, for when someone asks "does this actually cost nothing?"

Groq free tier: ~30 requests/min, ~1,000/day, no card required, indefinite (not a trial). Supabase free tier: 500MB Postgres, pgvector included, pauses after 7 days idle — the reason local Postgres is the default, not a knock against Supabase itself. Ollama: fully local, zero marginal cost, the ceiling is your hardware not your wallet.

## "Why Ponytail, and why didn't you overwrite AGENTS.md?"

Ponytail is a coding-style overlay (YAGNI ladder, shortest working diff) so the agent doesn't spend Day 1 inventing layers we don't need. Cursor's adapter is `.cursor/rules/ponytail.mdc` plus the skills under `.cursor/skills/` — that is the documented install for this host. Ponytail also ships its own `AGENTS.md`; replacing ours with it would delete the FDE session protocol (handoff, docs, agent-transcripts, locked stack). So they sit side by side: this repo's `AGENTS.md` for *what* we build, Ponytail for *how little code* it takes.

## "Why a SQL init file instead of Alembic?"

The evaluator's first `docker compose up` has to create the schema with zero extra commands. `backend/db/init/*.sql` on Postgres's docker-entrypoint is one file and one boot. We are not running online migrations for a two-day take-home; if the schema changes we reset the volume. Alembic is the upgrade path if this ever lives past submission.

`search_vector` is a generated `tsvector` column (guest + title + prefix + chunk) rather than a trigger-maintained one — Postgres keeps it in sync, we don't. Guest and title have to be in that expression: `plainto_tsquery` ANDs the whole question, so long eval queries returned **zero** sparse rows until we fused an OR `websearch_to_tsquery` alongside the AND query. That, not a 3B prefix LLM, is what moved eval from 48.48% to 81.82%.

## "Why no tiktoken / sentence-transformers in ingestion?"

Chunk size is ~800 tokens approximated as 3200 characters, snapped to sentence boundaries. tiktoken would be a tokenizer for a model we are not calling at ingest time; sentence-transformers would duplicate Ollama's `nomic-embed-text`. PyYAML is the one extra ingest dep because the transcript frontmatter is real YAML (multiline `description`). Contextual prefixes stay behind `--contextualize` so Day 1 can finish.

## "Why is follow-up rewrite just concatenating the last user turn?"

Architecture wants a standalone query before retrieval. A dedicated rewrite LLM call would double Groq usage on the free tier (~30 req/min) and add another timeout path. Concatenating a short follow-up onto the previous user question is enough for "why though?" and is marked to upgrade if evals show it failing.

## "Did you sharpen growth_brief, or leave the generic worksheet?"

Sharpened in place — still the same third skill, not a fourth. The prompt now asks for an FDE-shaped one-pager (Situation, Audit POV, one experiment, what would kill the bet, sources) rather than a blank "growth experiment worksheet." The uniqueness write-up already said a generic template is a weak differentiator; this is that change without expanding scope.

## "Why Markdown → React nodes instead of marked + DOMPurify?"

Architecture §6 forbids `dangerouslySetInnerHTML` on Markdown. A sanitizer library would have been another npm install and a frontend image rebuild. Stripping tags, rejecting `javascript:` URLs, and mapping a heading/list/emphasis whitelist to React elements never puts untrusted HTML in the DOM. HTML artifacts still go through a `sandbox="allow-same-origin"` iframe (no `allow-scripts` / `allow-forms`) plus a `default-src 'none'` CSP in the `srcdoc`.

## "Why bind-mount the backend and run uvicorn --reload?"

Same reason as the frontend `src` mount: Day 2 is a lot of Python changes, and rebuilding the image for every prompt tweak wastes the remaining calendar. The evaluator's `docker compose up` still works; `--reload` is a no-op cost if they never touch the files.

## "Why isn't the cloud model still llama-3.3-70b-versatile?"

Because Groq shut it down for free/developer keys on 16 Aug 2026. The live `/v1/models` list on this key does not include it; the 404 is `model_not_found`. Groq's own deprecation page names `openai/gpt-oss-120b` (or `qwen/qwen3.6-27b`) as the replacement. We default to `gpt-oss-120b` and make it overridable with `GROQ_MODEL` so the next catalog rotation is an env change, not another code hunt.

gpt-oss spends completion tokens on a `reasoning` field first. A 4096 `max_tokens` cap on the essay skill returned empty `content` (reasoning ate the budget). `reasoning_effort: "low"` plus a higher cap leaves room for the actual markdown.

## "Why Cloudflare only on Groq 429, not a third toggle?"

The brief asks for a visible cloud/local switch. A third provider in the header would imply the user should pick it. They shouldn't — Cloudflare is a safety net for Groq's ~30 req/min free tier, not a product choice. One retry with a 2s pause, then Workers AI `@cf/meta/llama-3.1-70b-instruct` if `CLOUDFLARE_ACCOUNT_ID` + token are set. Unconfigured, the readable rate-limit message still fires. Not a demo toggle, on purpose.

## "Why is retrieval eval 48% instead of 90%?"

The golden set is guest-grounded ("why do most AI products fail") but Day-1 ingest skipped LLM prefixes so we could ship `qa` this weekend. First full-corpus run was **48.48% (16/33)** — dense-only in practice, because `plainto_tsquery` ANDs every term and long questions matched nothing. Putting guest + title in `search_vector` plus fusing AND and OR sparse lists moved it to **81.82% (27/33)**. The six misses are generic paraphrases with no distinctive guest/title tokens. Did not rewrite the golden set to force 90%.

`--contextualize` then ran as **one Groq sentence per episode**, copied onto every chunk, then a full re-embed (24 min, 10043 chunks). Per-chunk Ollama is ~27h and Groq's free daily cap is ~1k, so that path was not runnable this weekend. Eval **stayed 81.82% (27/33)** — same six paraphrases. The bottleneck is question ambiguity, not missing guest names in the vectors. Cross-encoder rerank or per-chunk prefixes overnight is the remaining stretch.

## "Why show Thinking as a disclosure, not streamed tokens?"

gpt-oss already spends tokens on a `reasoning` field. Surfacing that plus the retrieved guest/title list is the actual trace (what we searched, then how the model used it). Streaming chain-of-thought would double Groq usage and still be empty on Ollama 3B. Collapsed `<details>` keeps the answer first.

## "Why add archive and rename after saying we wouldn't?"

The first cut was delete-only because nobody had asked to restore a thread. Then they did. `sessions.title` + `archived_at` is the smallest schema that lets a stored name override the first-message fallback and hide a thread without losing it. One `PATCH /sessions/{id}` covers both; empty title stores NULL so the list falls back. Delete stays hard-cascade. Native `<dialog>` replaces `window.confirm` so rename can share the same modal. Tablet rail still only keeps New + delete.

Citations were one chip per retrieved chunk, so eight identical Adam Grenier links. Dedup by `(guest, title)` at emit time; the answer is still grounded in all eight chunks, the UI just stops repeating the receipt.

## "Why a document card instead of the essay in chat?"

Chat dumping the full Ship 30/30 draft next to the Artifact pane is two copies of the same document. A compact card (type, title, Download PDF) is the Claude-doc-chip pattern: the thread stays a conversation, the pane is the work product. Selecting the card focuses that artifact. `qa` answers still render as sanitized markdown in chat; they do not create a card.

## "Why print-to-PDF instead of a PDF library?"

No new dependency. A print stylesheet reuses the same cream/ink/accent tokens and Iowan/Palatino/Georgia stack. "Download PDF" calls `window.print()` so the user gets a real PDF from the browser, not an HTML file with a `.pdf` extension.

## "Why a home page with hash routes instead of opening straight into chat?"

Opening on a chatbot is the generic Lenny-project first screen. A one-file masthead (`Home.tsx`) states the product before the desk: grounded Q&A, essays, briefs. Hash (`#work`) is enough; react-router would be a dependency for two views. The rust spine and numbered Ask / Write / Keep columns reuse the same cream/ink/accent tokens so it reads as the same object, not a marketing site glued on.

## "Why no em-dashes?"

Asked explicitly. One `unemdash` helper on the markdown path (chat + artifacts) plus the thinking/banner strings. UI copy we write uses hyphen or a period. Prompt text sent to the model was left alone.

## "Why move every markdown doc under docs/?"

A client-facing root should be `README.md` plus the runnable tree. Evaluators open the repo cold; a pile of `PRD.md` / `architecture.md` / `handoff.md` at the top looks like a notes dump. Everything that is not code, compose, or env lives in `docs/` with an index. `docs.md` became `docs/decisions.md` so the path is not `docs/docs.md`. Root keeps thin `AGENTS.md` / `CLAUDE.md` pointers so agent tools that look at the repo root still find the protocol.

## "Why one Export menu instead of three download buttons?"

Three parallel buttons (MD / DOCX / PDF) on a compact document card compete with the title and crowd the Artifact head. One **Export** disclosure matches the session ⋯ pattern: progressive disclosure, one clear verb, formats listed with extensions so the choice is explicit. Markdown and Word are real file downloads from the artifact body; PDF stays print-to-PDF so we keep the site typography without a PDF library. Word is a minimal OOXML zip built in the browser (plain paragraphs) — no new npm dependency.


