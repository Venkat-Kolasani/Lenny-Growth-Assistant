# Session — 13 Sep 2026 — LLM --contextualize backfill

**Agent:** Cursor (Grok 4.6) · **Status:** backfill done; eval still 81.82%

## What we tried

User asked to chase eval toward 90% with `python scripts/ingest.py --contextualize`. Timed one prefix: Groq **0.9s**, Ollama 3B **9.7s**. Per-chunk on 10,043 chunks is ~27h locally or ~10k Groq calls (free cap ~1k/day). Implemented episode-level: one Groq sentence from the first chunk, copy onto every chunk, re-embed without re-chunking. Resume skips rows that no longer use the template prefix.

## What worked

- `--limit 1` smoke: Ada Chen Rekhi, 34 chunks, 8s.
- Full backfill: `done: 10009 chunks` (Ada already done); DB **10043/10043** LLM prefixes, 0 template leftovers. ~24 min.
- `pytest` 34 passed.

## What failed, and how it was corrected

1. **Did not run per-chunk 3B.** Calendar + Groq daily cap. Documented in `architecture.md` §3 and `docs.md`.
2. **Eval did not move: 81.82% (27/33), same six MISS rows.** Episode-level prefixes put the guest in the dense vector, but the remaining questions are paraphrases with no distinctive tokens ("stay or quit", "growth org in practice"). Did not edit the golden set.

## Not done

Demo video, clean-clone check, per-chunk overnight pass, Cloudflare live 429.
