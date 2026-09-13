# agent-transcripts/

Assignment deliverable #6: coding-agent transcripts and logs, **including failed attempts and how they were corrected**. Secrets and API keys must be stripped before anything in this folder is committed.

This folder is written **as we go**, not reconstructed on submission day. The five prompts in `prompts.md` and the session protocol in `AGENTS.md` all require a write here; skipping it until the end is how it ends up empty.

## What to put here

One markdown file per working session, named:

```
YYYY-MM-DD-<short-slug>.md
```

Each file should cover, in plain language:

- What we tried
- What worked
- What failed, and how it was corrected (this is the part the brief explicitly asks for)
- Decisions that are already in `docs.md` can be linked, not restated

Raw Cursor/Claude/Codex jsonl may be copied alongside the markdown **only after** a secrets pass (no `.env` values, no API keys, no tokens). Prefer the markdown summary as the evaluator-facing artifact; keep raw logs only when they show a failure path that the summary would flatten.

## Sanitization checklist (run before every commit)

- [ ] No API keys, tokens, or `.env` values
- [ ] No personal emails / phone numbers that aren't already in public docs
- [ ] Failed attempts are still present — do not "clean up" the log into a success-only narrative

## Index

| File | Session |
|---|---|
| `2026-09-13-planning-review.md` | Plan review, git init, transcript-capture + model-timeout gaps closed |
| `2026-09-13-day1-build.md` | Ponytail install + Day 1 list (scaffold through Groq qa) |
| `2026-09-13-day2-skills.md` | GitHub push, Ollama toggle, Ship 30/30 + growth brief, Artifact Viewer |
| `2026-09-13-groq-ingest.md` | Groq key live, gpt-oss-120b swap, eval harness, full ingest started |
| `2026-09-13-eval-failover.md` | Full ingest done, eval 48.48%, Cloudflare 429 failover + structured logs |
