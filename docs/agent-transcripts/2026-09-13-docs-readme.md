# 2026-09-13 — docs folder + submission README

## Tried

User asked to keep all docs in a `docs/` folder and make the README submission-ready and client-facing, with clear clone-and-run steps.

## Worked

- Moved `PRD.md`, `architecture.md`, `design.md`, `test-plan.md`, `handoff.md`, `prompts.md`, `AGENTS.md`, assignment brief, and `agent-transcripts/` under `docs/`.
- Renamed former root `docs.md` → `docs/decisions.md` (avoids `docs/docs.md`).
- Root `AGENTS.md` / `CLAUDE.md` are thin pointers so tooling still finds a protocol entry.
- Root `README.md` rewritten as evaluator path: prerequisites → clone → `.env` → Ollama pulls → `docker compose up` → Python venv + ingest → open UI. Includes troubleshooting and a docs map.

## Failed / corrected

- First instinct was to leave agent transcripts at repo root as a "deliverable." User asked for all docs under `docs/`; transcripts are deliverable #6 documentation, so they moved with the rest. Updated prompts and protocol paths accordingly.

## Not done

- Did not push. Did not run a full clean-clone dry run in this pass.
