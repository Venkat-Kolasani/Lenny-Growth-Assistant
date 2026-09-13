# Architecture — The Lenny Growth Assistant

Companion to `PRD.md`. This document is the technical contract: what's running, how data flows, and why each choice was made over the obvious alternative.

## 1. Component map

```
┌─────────────┐      ┌──────────────────┐      ┌─────────────────────┐
│   React     │─────▶│     FastAPI       │─────▶│  Claude Agent SDK    │
│  (chat +    │◀─────│   (api layer)     │◀─────│  (skills + routing)  │
│  artifacts) │      └────────┬──────────┘      └──────────┬───────────┘
└─────────────┘               │                             │
                               ▼                             ▼
                     ┌──────────────────┐          ┌──────────────────┐
                     │  Postgres +       │          │  Model providers  │
                     │  pgvector         │          │  Groq (cloud) /   │
                     │  (sessions,       │          │  Ollama (local)   │
                     │  messages,        │          └──────────────────┘
                     │  artifacts,       │
                     │  transcript_chunks,│
                     │  retrieval_traces)│
                     └──────────────────┘
```

**Why FastAPI + Postgres + pgvector, not FastAPI + Chroma/Neo4j:** one stateful service instead of two or three. Every extra container is something a fresh evaluator's `docker compose up` can fail on. pgvector gets dense retrieval on the same instance that already holds sessions/messages — fewer moving parts, which is the actual point of the "operability" scoring criterion, not a corner cut.

**Why Ollama runs natively on the host, not as a Compose service, on Mac:** Docker Desktop on macOS runs containers inside a Linux VM with no Metal GPU passthrough — an Ollama container on an 8GB M3 MacBook Pro would be both slower (CPU-only) and heavier on the one resource that's actually scarce (unified memory shared with the VM itself). Ollama installed natively gets Metal acceleration and plays nicely with macOS's unified-memory management; the backend container reaches it over `host.docker.internal`. A `docker-compose.linux.yml` variant containerizes Ollama normally for anyone running on Linux, where this trade-off doesn't apply.

**Why local Postgres is the default, not Supabase:** Supabase's free tier is real and pgvector-capable, but free-tier projects pause after 7 days of inactivity — a real risk if this sits in an evaluation queue. Docker Compose ships a local Postgres+pgvector container as the default `DATABASE_URL`; `.env.example` documents the Supabase connection string as a drop-in alternative for anyone who wants managed hosting.

## 2. Database schema

```sql
-- sessions: one per chat
CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_metadata JSONB DEFAULT '{}',
    model_provider TEXT NOT NULL DEFAULT 'groq',   -- 'groq' | 'ollama' | 'anthropic'
    model_name TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- messages: chat turns, including tool/skill metadata
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES sessions(id) ON DELETE CASCADE,
    role TEXT NOT NULL,               -- 'user' | 'assistant' | 'system'
    content TEXT NOT NULL,
    skill_used TEXT,                  -- 'qa' | 'ship30' | 'growth_brief' | NULL
    citations JSONB DEFAULT '[]',     -- [{guest, episode_title, youtube_url, chunk_id}]
    created_at TIMESTAMPTZ DEFAULT now()
);

-- artifacts: rendered work-products
CREATE TABLE artifacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES sessions(id) ON DELETE CASCADE,
    message_id UUID REFERENCES messages(id),
    type TEXT NOT NULL,               -- 'markdown' | 'html'
    title TEXT,
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- transcript_chunks: the knowledge base
CREATE TABLE transcript_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    episode_guest TEXT NOT NULL,
    episode_title TEXT NOT NULL,
    youtube_url TEXT,
    publish_date DATE,
    topic_tags TEXT[] DEFAULT '{}',       -- from the repo's own index/ folder
    chunk_index INT NOT NULL,
    contextual_prefix TEXT,               -- LLM-generated situating context (see §3)
    chunk_text TEXT NOT NULL,
    embedding VECTOR(768),                -- dim depends on chosen Ollama embed model
    search_vector TSVECTOR,               -- Postgres native full-text, for hybrid search
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX ON transcript_chunks USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX ON transcript_chunks USING gin (search_vector);
CREATE INDEX ON transcript_chunks USING gin (topic_tags);

-- retrieval_traces: every retrieval call, for debugging + the eval harness
CREATE TABLE retrieval_traces (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id UUID REFERENCES messages(id),
    query TEXT NOT NULL,
    method TEXT NOT NULL,             -- 'dense' | 'sparse' | 'hybrid_rrf'
    retrieved_chunk_ids UUID[] NOT NULL,
    scores JSONB,
    confidence FLOAT,                 -- top-score, drives the insufficient-evidence gate
    created_at TIMESTAMPTZ DEFAULT now()
);
```

`eval/golden_set.json` (question → expected guest/episode/topic) stays a version-controlled file, not a table — it's reviewed in PRs like test fixtures, not queried at runtime.

## 3. Ingestion + retrieval — the RAG design

Naive fixed-size chunking loses a lot on a 60-90 minute conversational transcript: topic drift, speaker context, and the fact that a chunk pulled from the middle of an anecdote is meaningless without knowing what anecdote it's from. The pipeline:

1. **Parse** each `episodes/{guest}/transcript.md`, pulling YAML frontmatter (guest, title, YouTube URL, date) and matching topic tags from the repo's own pre-built `index/` folder — that tagging work is already done, reuse it rather than re-deriving it.
2. **Chunk** at ~700-900 tokens with ~15% overlap, snapped to sentence boundaries.
3. **Contextualize** — before embedding, generate a short (1-2 sentence) prefix per chunk describing where it sits in the episode ("From Lenny's interview with X, discussing Y, on the topic of Z"), using the local Ollama model as a one-time batch ingestion cost. This is Anthropic's own published Contextual Retrieval idea: situating a chunk before embedding measurably reduces retrieval misses versus embedding the bare chunk, and running it through the already-local model keeps it free.
4. **Embed** via an Ollama-served embedding model (e.g. `nomic-embed-text`) rather than adding a separate Python embedding dependency — one less thing in the Docker image, and it's already a required service in the stack.
5. **Index** into `transcript_chunks` — both the vector column (dense) and a generated `tsvector` column (sparse/keyword), so proper nouns and named frameworks ("PMF", "North Star Metric") that embeddings sometimes blur are still catchable by exact term match.

**At query time:**
- Run dense (cosine) and sparse (`ts_rank`) search in parallel, merge with **Reciprocal Rank Fusion**, boost results whose `topic_tags` match a topic inferred from the query.
- If the fused top score is below a confidence threshold, skip generation and return the "not covered in the transcripts" path from `PRD.md` §3.2 instead of forcing an answer.
- On a follow-up turn, rewrite the question against recent conversation history into a standalone query before retrieving — a bare "why though?" needs the prior turn's subject folded in before it can be searched.
- Every returned chunk carries its `episode_guest` / `episode_title` / `youtube_url` straight into the response as a citation.

**Stretch, not core (add only with time to spare):** a cross-encoder rerank pass on the fused top-k before final context assembly.

## 4. Agent layer — Claude Agent SDK, skills, routing

Built on the Claude Agent SDK (Python) rather than Pi Coding Agent. The SDK is purpose-built on the Claude Code agent harness for exactly this shape of application — it ships context management, a tool ecosystem, and session handling out of the box, and its Skills/subagents model is a direct fit for what §4.2 of the assignment asks for: encoding a skill's rules structurally instead of relying on one unstructured prompt. Pi is a genuinely strong project, but its four-tool (read/write/edit/bash) design centers on being *a developer's* terminal coding harness, not a natural runtime agent embedded inside an end-user product.

**A note on how this stays free:** Anthropic's API has no ongoing free tier — new accounts get a one-time, 30-day trial credit, not a renewing allowance like Groq or Cloudflare. Routing every model call through the Claude Agent SDK's default Anthropic backend would eventually cost money, and routing it at a non-Anthropic provider by disguising that provider behind `ANTHROPIC_BASE_URL` sits in a gray area Anthropic hasn't clearly resolved (there's an open, unanswered GitHub issue asking Anthropic exactly this). So the split is: the skills/routing/tool-use **architecture** follows the Agent SDK's patterns (skill definitions, subagent boundaries, a structured tool-use loop) faithfully, but the actual inference calls for the default free path go straight to Groq's and Ollama's own native APIs, not through the SDK's Anthropic transport. The Agent SDK itself is wired in as a real, working adapter for anyone who supplies their own Anthropic key — genuinely present, genuinely optional, never required for the app to run for free.

Three skills, each a distinct subagent definition with its own system prompt, allowed tools, and output contract:

| Skill | Trigger | Tools available | Output |
|---|---|---|---|
| `qa` | default / explicit question | `retrieve`, nothing else | chat message + citations |
| `ship30_essay` | "write an essay / Ship 30 style piece" | `retrieve`, `write_artifact` | markdown artifact, ~1,250 words |
| `growth_brief` | "write a growth brief / experiment doc" | `retrieve`, `write_artifact` | markdown artifact, structured one-pager |

Routing: the top-level agent inspects intent (explicit slash-style command or inferred from phrasing) and hands off to the matching subagent; the subagent's own system prompt encodes its structural rules rather than the router trying to cram all three behaviors into one prompt.

**Ship 30 for 30 skill, specifically** — encoded from the actual published framework, not a one-line "write like Ship 30 for 30": force topic specificity and a stated credibility stance before drafting, pick one of the four angles (actionable / analytical / aspirational / anthropological), commit to a single organizing structure (steps, lessons, or mistakes — never mixed), format in "wheels and spokes" (H1 sections, H2/H3 sub-points) with an alternating short/long sentence rhythm, and run a differentiation check that rejects the first, most obvious take on the topic before drafting.

## 5. Model configuration layer

A single `ModelProvider` interface with adapters for `groq`, `ollama`, `cloudflare`, and (optional, non-default) `anthropic`. Session-level `model_provider` / `model_name` are stored per session and surfaced in the UI — switching is explicit and visible, never silent.

**Finalized models:**
- **Cloud (default): Groq, `llama-3.3-70b-versatile`.** Strong general-purpose quality for both grounded Q&A and the two writing skills, LPU-fast, free tier (~30 req/min, ~1,000 req/day, no card).
- **Local: Ollama, `llama3.2:3b`.** Sized for the reference dev machine — an 8GB M3 MacBook Pro — where a 7-8B model would compete with Docker Desktop and the OS for memory that isn't there to spare. `OLLAMA_EMBED_MODEL=nomic-embed-text` for ingestion/query embedding (~274MB, negligible either way).
- **Cloudflare Workers AI — free third provider, added specifically as a Groq rate-limit fallback**, not a default. 10,000 Neurons/day, no card required, resets daily. Model: `@cf/meta/llama-3.1-70b-instruct` (or the `3.3` variant if available in the account's catalog at build time — check `npx wrangler ai models list`). If Groq returns a 429 mid-demo, the client can fail over to this adapter automatically rather than surfacing the rate limit to the user at all.
- **Anthropic — optional, explicitly not part of the free default.** Anthropic's API has no ongoing free tier (a one-time 30-day trial credit only), so this adapter exists for completeness and for anyone using their own paid/trial key, and is never required to run the app.

Groq's rate limit is handled with client-side backoff and a readable message; if backoff is exhausted, the client automatically retries the same request against Cloudflare rather than surfacing a raw 429.

## 6. Artifact security

Two artifact types, two different handling paths — because "sanitize everything the same way" is the wrong instinct here:

- **Markdown artifacts** never touch `dangerouslySetInnerHTML`. Rendered through a Markdown parser with sanitization (strips raw HTML, script tags, event handlers) before hitting the DOM.
- **HTML/CSS artifacts** render inside a sandboxed `<iframe srcdoc="...">` with `sandbox="allow-same-origin"` only — no `allow-scripts`, no `allow-forms`, no `allow-popups` — plus a strict CSP inside the frame blocking any external resource load. A `<script>` tag in a generated artifact is inert; a form can't submit anywhere; nothing in the frame can reach the parent page or make a network call. This is deliberately what the viewer **permits** (styled static markup, CSS) versus **blocks** (any execution or network egress) — stated explicitly, per the assignment's ask.

## 7. API surface (FastAPI)

```
GET  /health                       liveness
GET  /health/dependencies          checks DB, active model provider, Ollama reachability
POST /sessions                     create session
GET  /sessions                     list sessions
GET  /sessions/{id}                session + message history
POST /sessions/{id}/messages       send a message → grounded response (+ skill routing)
GET  /sessions/{id}/artifacts      artifacts for a session
GET  /artifacts/{id}               single artifact content
GET  /config/providers             available providers/models, for the UI toggle
POST /sessions/{id}/provider       switch model provider mid-session
POST /eval/run                     (dev) run the golden-set retrieval eval, return metrics
```

## 8. Deployment topology

`docker-compose.yml` services: `backend` (FastAPI + agent layer), `postgres` (with pgvector, volume-persisted), `ollama` (pulls the configured model on first boot), `frontend` (React, served statically or via Vite dev server). One command: `docker compose up`. `.env.example` documents every variable with safe defaults and marks required vs. optional explicitly; no secret ships with a real value.

**Observability:** structured JSON logs (`structlog`), a request-scoped trace ID threaded through retrieval → model call → artifact render, so a failure at any stage is traceable from one log line. `/health/dependencies` is the first thing to check when something's wrong, before reading logs at all.

**Resilience, explicitly tested (see `test-plan.md`):** missing API key → clear config error, not a stack trace. Ollama unreachable → falls back to informing the user the local model is unavailable rather than hanging. Empty retrieval → the insufficient-evidence path from §3. Postgres unreachable → `/health` reports it plainly and the API returns a 503 with a human-readable message, not a 500.
