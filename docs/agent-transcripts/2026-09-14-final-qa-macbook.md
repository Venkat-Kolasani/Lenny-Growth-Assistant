# Final QA — MacBook Pro (14 Sep 2026)

**Worker:** `bc-7843085d-e9ac-551f-9e5e-09795b0ebd65`  
**Repo:** `Venkat-Kolasani/Lenny-Growth-Assistant` @ `main` → branch `cursor/ollama-qa-context-bd65`  
**Checkout:** `~/Library/Mobile Documents/com~apple~CloudDocs/Job Applications/Oogway Labs/Lenny Growth Assistant`

## Verdict

| Area | Result |
|---|---|
| **Overall** | **PASS** (with caveats) |
| **pytest** | **49 passed**, 0 failed |
| **eval.run** | **81.82% (27/33)** — unchanged |
| **Local demo** | **PASS** — `/health` ok, UI `:5173` 200, deps show 10,043 embedded chunks |
| **Ollama (fresh sessions)** | **PASS** — grounded on README/sample questions |
| **Ollama (multi-turn)** | **WEAK** — `llama3.2:3b` drifts after 2–3 turns (mitigated in fix PR) |
| **Groq compare** | **Mixed** — sharper answers when not rate-limited; hit 429 during burst QA |

## Root cause of prior sample failures

Postgres volume had **0 transcript chunks** at QA start. Every sample looked like an Ollama/model failure but was really **empty retrieval**. Re-ran `python scripts/ingest.py` (303 episodes → **10,043 chunks / 302 episodes**). After ingest, Ollama answers grounded with citations.

`/health/dependencies` now exposes `corpus` chunk count (diagnostic, does not fail overall health).

## Environment

- **Branch:** `main` @ `f637d13` (clean working tree before fix branch)
- **Ollama:** running; models `llama3.2:3b`, `nomic-embed-text`
- **Configured:** `OLLAMA_MODEL=llama3.2:3b`, `DEFAULT_MODEL_PROVIDER=groq`; UI toggle → `POST /sessions/{id}/provider`
- **Docker:** started for QA; compose stack healthy

## Tests

```bash
docker compose exec backend pytest   # 49 passed, 1 warning
python -m eval.run                   # precision=81.82% (27/33)
```

## Local demo

| Check | Result |
|---|---|
| `GET /health` | `{"status":"ok"}` |
| `GET /health/dependencies` | postgres ✓, ollama ✓, groq key ✓, **corpus: 10043 embedded chunks** |
| `http://localhost:5173/` | HTTP 200, Vite UI loads |

## Ollama sample quality (fresh session each question)

Model: **Ollama `llama3.2:3b`** via header toggle. One new session per question unless noted.

| Question | Label | Time | Notes |
|---|---|---:|---|
| Why do most AI products fail in production? | **grounded** | 27s | Cites Reganti/Badam, Paul Adams, Adriel Frederick |
| How do you build a high-performing growth team? | **grounded** (thin) | 34s | Opens with “don't have direct answer” then cites Fishman/Cutler/Williams/Tan |
| What is Brian Chesky's new playbook for running product? | **grounded** | 25s | Cites **Brian Chesky**; playbook summary thin vs Groq |
| When should a company invest in a new acquisition channel? | **grounded** | 27s | Cites Adam Grenier |
| How should a CEO stay in the details without micromanaging? | **grounded** | 18s | Cites Howie Liu, Nir Eyal |
| Write me a Ship 30/30 essay on activation for a B2B product | **grounded_artifact** | 43s | Artifact “Activation Strategies for B2B Products”, ~3k chars |
| Write a growth brief for shipping an AI feature people will actually use | **grounded_artifact** | 30s | Artifact “AI Feature Adoption”, ~2.4k chars |

**Multi-turn (same session, pre-fix):** Q2+ polluted by prior answers; Chesky question retrieved wrong guests. **Post-fix (2-turn history cap):** less bleed, still weaker than fresh sessions on Q2/Q3.

**Out-of-corpus probe:** nonsense question returned a hedged answer with citations still attached (**hallucination-adjacent** — retrieval returns top-k even when irrelevant; model should refuse harder).

## Groq comparison (same questions, fresh sessions)

| Question | Label | Time | Notes |
|---|---|---:|---|
| Why do most AI products fail in production? | **grounded** | 2.4s | Longer, structured answer; same citation set |
| How do you build a high-performing growth team? | **grounded** | 1.9s | Direct, cites Fishman framework |
| What is Brian Chesky's new playbook… | **rate_limited** then **grounded** | 2.6s / 2.1s | 503 during burst; retry succeeded with Chesky citation |
| When should a company invest in a new acquisition channel? | **rate_limited** | 2.6s | 503 during burst (not retried in same run) |

**Takeaway:** retrieval is shared; Groq is faster and more coherent when not 429'd. Ollama is usable for demo on fresh turns; multi-turn + off-topic refusal remain 3B limits.

## Resilience (quick)

| Probe | Result |
|---|---|
| Ollama down | Not run (would stop host daemon) |
| Empty corpus | **Reproduced at start** — all samples empty/refuse; fixed by ingest |
| Groq 429 | **Observed** — readable 503 message |
| Nonsense / off-corpus | Weak refuse; citations still emitted |

## Fix shipped

Branch **`cursor/ollama-qa-context-bd65`**: tighten Ollama context (6 chunks × 700 chars, 2-turn history), cap local artifact token limits, add `corpus` to `/health/dependencies`. **49 pytest pass** after change.

## Recommended before demo recording

1. Confirm `corpus.ok` in `/health/dependencies` (run ingest if 0).
2. Use **fresh session** or **New** between sample clicks when demoing Ollama.
3. Prefer Groq for multi-turn; Ollama for “local / $0” beat.
4. Pause between Groq calls to avoid 429 during recording.
