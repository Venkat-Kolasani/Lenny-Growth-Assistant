# PRD — The Lenny Growth Assistant

**Author:** Venkat · **For:** Oogway Labs FDE Take-Home · **Status:** Draft v1 · **Target ship date:** 15 Sep 2026

---

## 1. Summary

The Lenny Growth Assistant is an internal tool that turns Lenny's Podcast (269 episodes of product and growth interviews) into something a working operator can actually use under time pressure: grounded answers, and — more importantly — **finished written artifacts** they can drop straight into a real deliverable, instead of forty minutes of half-remembered podcast advice.

It is not built to be the smartest "chat with a podcast" demo. That category is already crowded — see §2.4. It's built to be the version of that idea a Forward Deployed Engineer would actually hand off to a team: grounded, cited, cheap to run, resilient when a dependency goes down, and documented well enough that someone else can pick it up.

## 2. Discovery Brief

### 2.1 User and problem

**Primary user:** someone doing Oogway-shaped work — an FDE or account lead prepping for a client **Audit** or scoping a **Quick-Wins build** (Oogway's own two entry phases; see `decisions.md` for the source). Their job in that moment isn't "learn about product management." It's: *find a defensible, cited point of view on a specific product/growth question fast enough to use in a roadmap doc or a client call, without becoming a prompt engineer to get it.*

**The pain removed:** today that means either scrolling YouTube transcripts hoping to remember which episode covered activation metrics, or writing generic advice from memory and hoping it holds up when a client pushes back. Neither produces something you can paste into a deliverable.

**The job to be done:** ask a grounded question → get an answer with a receipt (which guest, which episode) → optionally turn that thread into a finished written artifact (an essay, a one-pager) without re-explaining the context to a blank prompt box.

### 2.2 Success metrics

Two, one operational and one product-facing — both measurable from day one, not aspirational:

1. **Retrieval grounding precision ≥ 90%** against a hand-built golden set of ~30 question/expected-source pairs (see `eval/golden_set.json`, built from the repo's own topic index). Measures whether the RAG layer is actually doing its job, independent of how good the final prose sounds.
2. **Artifact completion rate** — the % of sessions that end with at least one saved artifact (essay, growth brief, or exported Q&A thread). This is the real proxy for the stated user goal ("reusable written content"); a session that only produces chat bubbles hasn't delivered the thing the user actually came for.

### 2.3 Assumptions

Documenting these explicitly because the brief leaves them open, and because a real FDE would rather state an assumption than silently guess:

- **"Cloud provider" is interpreted functionally, not by brand.** Groq isn't Anthropic or OpenAI directly — it's a fast inference host serving open-weight models (Llama, GPT-OSS, Qwen) on custom LPU silicon. It satisfies "cloud LLM provider" in spirit and was the explicit ask. To also satisfy the letter of the requirement, the model-provider interface is written as a swappable adapter, so a direct Anthropic Claude adapter behind the same toggle is a same-day addition, not a redesign.
- **Zero budget.** No paid APIs, no paid infra tier, anywhere in the stack. Every choice below was checked against this before it made the doc (see §2.6 and `architecture.md` for the specific free-tier numbers).
- **"Production scale" is read as production-grade discipline, not literal infrastructure scale.** Given the zero-budget constraint and the take-home context, "production scale" can't mean horizontally-scaled infra — so it's interpreted as evals, cost-consciousness, graceful degradation, and clean interfaces. This reading isn't a guess: it's Oogway's own stated engineering philosophy (*"outcome-driven, not over-engineered... we use the simplest tool that works"* — see `decisions.md`), so it's also the version most likely to match what the evaluator actually values.
- **Single-user, single-team internal tool.** No multi-tenant auth, no roles/permissions, no SSO. A lightweight `user_metadata` field on sessions is enough to satisfy "user metadata" in the persistence requirement.
- **Local machine specs confirmed:** MacBook Pro, M3, 8GB RAM. Local model is Ollama `llama3.2:3b` (a 7–8B model is not safe alongside Docker + OS on 8GB total). Flagged in §7 as resolved; leftover "unconfirmed" wording in an earlier draft of this section is no longer current.
- **The evaluator may run this days after receiving it.** That ruled out Supabase-hosted Postgres as the *default* path — its free tier pauses projects after 7 days of inactivity, which would break "clone and run" on exactly the kind of delay a hiring pipeline produces. Local Postgres+pgvector via Docker Compose is the default; Supabase is documented as an optional managed alternative.

### 2.4 Prior art — what's already been built on this exact dataset

Real discovery, not assumed: the transcript repo's own README lists **20+ public projects** already built on these 269 episodes — graph-based multi-hop RAG (Lennyhub RAG, Lenny's Knowledge Graph), citation-to-timestamp tools (Ask Lenny, Lenny Distilled, Lenny's Library), a skills database, guest personas as Notion mentors, semantic "idea constellation" exploration, contradiction-surfacing (Wisdom Wall, Antimemes), situational advice generators, and two MCP servers.

This changes the target. A meaningfully large share of the other ~800-1000 candidates will independently converge on "vector search + citations + chat UI" — because that's the obvious read of the brief, and it's already been built a dozen times publicly. The gap none of those 20 projects fill: an **internal work-product tool** for a team that has to ship documents, not a public exploration toy for podcast fans. That's the gap this scopes into.

### 2.5 Scope

**In scope**
- Grounded conversational Q&A with session memory and follow-up handling
- Two content-generation skills: Ship 30 for 30 essay generator (mandatory) and a Growth Experiment Brief generator (the differentiator — see `architecture.md` §Agent Layer)
- Hybrid retrieval (dense + keyword) with source provenance on every grounded claim
- A small retrieval-quality eval harness tied to the success metric above
- Artifact Viewer rendering Markdown and HTML/CSS safely, side-by-side with chat
- Cloud (Groq) / local (Ollama) model toggle, visible in the UI
- Postgres persistence for sessions, messages, artifacts, retrieval traces
- Docker Compose one-command startup, structured logging, documented failure handling

**Explicitly out of scope, and why**
- **Multi-tenant auth / roles** — not needed for a single-evaluator internal tool; would spend a day on a problem the brief doesn't have.
- **A 4th+ skill** — two well-built skills with real grounding beat four shallow ones; more skills is the first thing cut if time runs short (see §5).
- **A full knowledge graph (Neo4j-style entity graph)** — two of the 20 existing projects already did this well publicly; hybrid vector+keyword retrieval gets most of the grounding benefit at a fraction of the ingestion complexity, which matters given the timeline.
- **Live transcript refresh / new-episode ingestion pipeline** — the repo is a static snapshot for this exercise; a scheduled refresh job is a documented "next step," not a build item.
- **Reranking model, query-classification ML** — noted as a stretch in `architecture.md`, added only if the core is solid with time to spare.

### 2.6 Risks and trade-offs

| Risk | Mitigation |
|---|---|
| **Hallucination** | Provenance on every claim; explicit "not covered in the transcripts" path when retrieval confidence is low, instead of forcing an answer. |
| **Latency** | Groq is fast by design (LPU inference); Ollama on a local 3B model will be visibly slower — documented and shown honestly in the demo, not hidden. |
| **Cost** | Hard $0 constraint. Groq's free tier is ~30 req/min and roughly 1,000 req/day, no card required — the client includes backoff/retry and a friendly rate-limit message rather than a raw 429. |
| **Local-model quality** | A 3B local model will be visibly weaker than Groq's larger hosted models on nuanced synthesis — documented as an expected, honest trade-off of the local path, not something to paper over in the demo. |
| **Data leakage** | Dataset is public (MIT-adjacent educational archive); the real leakage surface is API keys — `.env` is gitignored, `.env.example` ships with placeholders only. |
| **Unsafe artifact rendering** | Markdown never renders as raw HTML; generated HTML/CSS artifacts render inside a sandboxed iframe with scripts disabled. Full detail in `architecture.md`. |
| **Free-tier operational risk** | Supabase's free-tier inactivity pause could break a delayed evaluation — mitigated by making local Postgres the default path (§2.3). |
| **Hung / slow model call** | Every provider call has a client-side timeout (`MODEL_TIMEOUT_SECONDS`, default 60) and returns a readable error rather than a request that never comes back (assignment §5). |
| **Ingestion wall-clock on Day 1** | Contextual prefixes over 269 episodes via `llama3.2:3b` can consume the remaining calendar by themselves. First pass may skip prefixes (bare-chunk embeddings) so `qa` ships; prefixes are a quality rerun, not a Day-1 blocker. |

## 3. Key user flows

1. **Grounded question →** user asks a product/growth question → retrieval runs → answer returns with inline citations (guest, episode, link) → user asks a follow-up, which is rewritten against conversation history before re-retrieving.
2. **Insufficient evidence →** retrieval confidence falls below threshold → assistant says so plainly instead of guessing, and suggests a nearby topic that *is* covered.
3. **Essay generation →** user asks for a Ship 30/30-style piece on the thread's topic → essay skill drafts against the encoded framework → renders in the Artifact Viewer, editable, exportable as Markdown.
4. **Growth brief generation →** user asks for a structured growth experiment write-up → brief skill drafts hypothesis/metric/design/risks grounded in the Growth Strategy topic cluster → renders as an artifact.
5. **Model switch →** user toggles Groq ↔ Ollama mid-session; next message uses the new provider; the UI makes the active provider visible at all times (never a silent switch).

## 4. Acceptance criteria

- [ ] A fresh `git clone` + `docker compose up` produces a running app with zero manual steps beyond copying `.env.example` → `.env`
- [ ] Every grounded answer that cites the transcripts shows at least one verifiable guest/episode reference
- [ ] Retrieval eval script runs standalone and reports the golden-set precision number used in §2.2
- [ ] Killing the Ollama process, removing the Groq key, stopping Postgres, and simulating a hung model call each produce a clear, non-crashing error state — verified by a test for each (model timeout is a client-side cutoff with a readable error, not a request that never returns)
- [ ] Generated HTML artifact cannot execute a `<script>` tag against the parent page — verified by a test
- [ ] Essay skill output is ~1,250 words, uses a single consistent organizing structure, and traces its claims to specific episodes

## 5. Implementation plan

| Day | Focus |
|---|---|
| **Sat 13** | Repo scaffold, Docker Compose skeleton, DB schema + migrations, ingestion script (clone → chunk → contextualize → embed → load), health endpoints, Q&A skill working end-to-end on Groq only |
| **Sun 14** | Ollama + model toggle, real session persistence, Ship 30/30 skill, Growth Experiment Brief skill, Artifact Viewer + sanitization, citations UI |
| **Mon 15 AM / remaining** | Retrieval eval harness + real numbers, resilience paths (including model timeouts), structured logging, automated + manual tests, finalize all docs, record demo video |
| **Mon 15 EOD** | Clean-clone verification, submission |

**Every day, not a Day-3 leftover:** append to `agent-transcripts/` (assignment deliverable #6) as work happens — including failed attempts and how they were corrected, secrets stripped. The five session prompts in `prompts.md` all require this write-up so it cannot be forgotten until submission. See `agent-transcripts/README.md`.

If time runs short, cut order is: 4th skill → reranking stretch → UI polish. Tests, resilience, docs, and the running `agent-transcripts/` log are cut last — they're worth more per hour against §8 of the assignment than any additional feature.

## 6. Interview crib

See `decisions.md` for the "why" behind every decision above, written for you to defend out loud, not just read.

## 7. Open questions

- ~~Local machine RAM/GPU~~ — **resolved:** MacBook Pro, M3, 8GB RAM. Local model finalized as Ollama `llama3.2:3b` (a 7-8B model isn't safe alongside Docker + OS on 8GB total); cloud model is Groq `openai/gpt-oss-120b` (Groq retired `llama-3.3-70b-versatile` on 16 Aug 2026); Cloudflare Workers AI added as a free automatic failover for Groq rate limits. Full detail in `architecture.md` §5.
- Whether to keep the differentiator skill as Growth Experiment Brief or swap it — open until you confirm.
