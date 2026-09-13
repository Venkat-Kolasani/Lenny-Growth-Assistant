# 2026-09-14 — eval clarity, pytest, Anthropic BYOK

## Tried

Fix Compose `pytest` (`No module named 'eval'`), explain and modestly improve retrieval eval without rewriting `golden_set.json`, and add a real Anthropic Messages adapter as BYOK.

## Worked

- `hit()` now lives in `backend/app/retrieval/eval_hit.py`. Host `eval/run.py` and Compose tests import that. `docker compose exec backend pytest` is **48 passed**.
- Artifact sandbox test looks for `frontend/src/artifact.ts` on the host repo path or `/app/frontend/...` (compose bind-mount).
- Retrieval: denser/sparser pool 32, top-12, guest+title embed rerank after RRF.
- Anthropic: `anthropic` SDK Messages API. Toggle lists it; `available` is false without `ANTHROPIC_API_KEY`; switch without a key is 400.

## Failed / corrected

- First Compose pytest pass after the `eval` move: 47 passed, then `test_html_iframe_sandbox_forbids_scripts` looked at `/frontend/src/artifact.ts` (`parents[2]` from `/app/tests` is `/`). Search two candidate paths + mount the file.
- Guest+title rerank did **not** raise precision. Still **81.82% (27/33)**. Recovered “stay or quit” (Ada Chen Rekhi) but dropped Chesky “CEO stay in the details” and a few other paraphrases. Did not rewrite the golden set.

## Eval definition (unchanged)

HIT if `expected_guest` is a case-insensitive substring of any top-k `episode_guest`. Precision = hits / 33. Retrieval only, not answer quality.

## Not done

Demo video, live Cloudflare 429, clean-clone check, cloud deploy.
