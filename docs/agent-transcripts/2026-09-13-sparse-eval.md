# Session — 13 Sep 2026 — title-in-sparse + AND/OR fusion

**Agent:** Cursor (Grok 4.6) · **Status:** eval 81.82% after sparse fix; pushed with Session 7 first

## What we tried

Pushed Cloudflare failover + the 48.48% eval number (`19ea5cc`), then continued on retrieval. Full-corpus misses were thematic neighbors (Aishwarya's "AI products fail" ranked Laura Schaffer). Two changes: guest + title in the generated `search_vector` with a template prefix (no 3B LLM), and sparse query semantics.

## What worked

- Live `ALTER` + prefix backfill on 10043 chunks; no re-embed.
- Root cause of empty sparse: `plainto_tsquery` ANDs every term, so "Why do founders fail according to Ben Horowitz…" matched **zero** rows even though Horowitz was in every one of his chunks.
- Fusing AND (`plainto_tsquery`) + OR (`websearch_to_tsquery` of tokens ≥3 chars) with dense RRF.
- Eval: **48.48% (16/33) → 81.82% (27/33)**.
- `pytest` 33 passed.

## What failed, and how it was corrected

1. **Title-in-vector alone was a +3 point change (48.48 → 51.52).** Sparse was still empty on long questions. OR-only then dropped the Aishwarya title HIT (too many AI episodes). AND+OR fusion got both guest-named and title-like questions.
2. **Did not rewrite `eval/golden_set.json` to manufacture 90%.** Six remaining misses are generic paraphrases ("stay or quit", "growth org in practice").
3. **Did not run LLM `--contextualize`.** Would re-embed ~10k chunks for the last stretch; recorded as next only if we need ≥90%.

## Not done

Demo video, clean-clone check, live Cloudflare 429 (credentials still empty).
