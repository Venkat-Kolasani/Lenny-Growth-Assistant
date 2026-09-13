# test-plan.md — QA strategy

Testing bar for this project: cover the paths that are actually graded (assignment §8, `PRD.md` §4 acceptance criteria) well, rather than chasing coverage percentage. Every category below maps to something explicitly asked for.

## 1. Automated tests

### API contract
- Session create/get/list return the documented shape; invalid payloads return structured 4xx errors, not 500s.
- `/health` and `/health/dependencies` correctly reflect DB / model-provider / Ollama reachability (mocked down states, not just the happy path).

### Retrieval + eval harness (the load-bearing one)
- `eval/golden_set.json` — ~30 hand-built question → expected episode/guest pairs, sampled across different topic clusters from the repo's own index, not clustered on one easy topic.
- `python -m eval.run` reports precision (expected source in top-k) — this number is what `PRD.md` §2.2's success metric actually is, not a claim in prose.
- Unit tests for the RRF fusion logic itself (dense-only hit, sparse-only hit, both agree, neither hits → confirms the insufficient-evidence gate fires).

### Skill routing
- Given an explicit essay request, the `ship30_essay` skill is selected, not `qa`.
- Given an explicit growth-brief request, `growth_brief` is selected.
- Given a plain question, `qa` is selected and no artifact is produced.
- A misrouted case (ambiguous phrasing) fails gracefully to `qa` rather than to an error.

### Persistence
- A session's messages and artifacts survive a service restart (real Postgres in the test environment, not mocked away).
- Cascade delete: removing a session removes its messages and artifacts.

### Artifact security (a graded requirement, not a nice-to-have)
- A generated HTML artifact containing a `<script>` tag does not execute against the parent page when rendered — assert directly against the sandboxed iframe's permissions, not just "it looks fine."
- A Markdown artifact containing raw `<script>` or event-handler attributes is stripped before reaching the DOM.

### Resilience (each of these is its own test, not a manual check)
- Missing `GROQ_API_KEY` → clear config-error response, app still boots.
- Ollama container / host daemon down → chat on the Ollama provider returns a readable "local model unavailable" message, not a hang or crash.
- Model timeout → a slow or hung provider call is cut by a client-side timeout and returns a readable error (not a spinner that never resolves). Assignment §5 names this alongside missing keys / Ollama down / DB failures; it is its own case, not folded into "Ollama unreachable."
- Empty retrieval result → the insufficient-evidence path fires instead of a hallucinated answer.
- Postgres unreachable → `/health` reports it, API returns 503 with a human-readable body.

## 2. Manual UI test plan

Run through this checklist before every demo recording, not just once:

- [ ] Create a new session; empty state shows the suggested-question prompt, not a blank box
- [ ] Ask a grounded question; citation(s) appear and link to a real episode
- [ ] Ask a follow-up ("why though?"); confirm it's correctly rewritten against prior context, not searched literally
- [ ] Ask something outside the transcripts' coverage; confirm the insufficient-evidence state, not a confident guess
- [ ] Request a Ship 30/30 essay; confirm ~1,250 words, single consistent structure, citations present, renders in the Artifact Viewer
- [ ] Request a growth brief; confirm it renders as a distinct artifact alongside (or replacing) the essay
- [ ] Switch model provider mid-session; confirm the switch is visibly logged in the thread, and the next response actually comes from the new provider
- [ ] Stop the Ollama process and try the local provider; confirm the UI error state matches design.md, not a frozen spinner
- [ ] Force a model timeout (or wait out `MODEL_TIMEOUT_SECONDS`); confirm a readable "didn't respond in time" state, not a hung request
- [ ] Resize to mobile width; confirm the chat/artifact tab-switch behavior works and the badge appears when an artifact lands while on the Chat tab
- [ ] Keyboard-only pass: reach every interactive element (new session, send message, open artifact, switch model) without a mouse
- [ ] Screen-reader spot check: streaming response and error states are announced, not silent

## 3. Mapping back to acceptance criteria

Every checkbox in `PRD.md` §4 should trace to a specific test or checklist item above — if one doesn't, either the criterion is under-tested or the test plan is missing something. Revisit this mapping on Day 3 (`PRD.md` §5) before finalizing, not after.
