"""Retrieval eval: fraction of questions whose expected guest appears in top-k."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def hit(expected_guest: str, guests: list[str]) -> bool:
    needle = expected_guest.lower()
    return any(needle in guest.lower() for guest in guests)


def run() -> float:
    sys.path.insert(0, str(ROOT / "backend"))
    from app.retrieval.search import retrieve

    items = json.loads((ROOT / "eval" / "golden_set.json").read_text())
    if not items:
        raise SystemExit("eval/golden_set.json is empty")
    hits = 0
    for item in items:
        chunks = retrieve(item["question"])
        guests = [c.episode_guest for c in chunks]
        ok = hit(item["expected_guest"], guests)
        hits += int(ok)
        flag = "HIT" if ok else "MISS"
        print(f"{flag}\t{item['expected_guest']}\t{item['question'][:70]}")
    precision = hits / len(items)
    print(f"precision={precision:.2%} ({hits}/{len(items)})")
    return precision


if __name__ == "__main__":
    run()
