import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from eval.run import hit


def test_guest_match_is_substring():
    assert hit("Aishwarya Naresh Reganti", ["Aishwarya Naresh Reganti + Kiriti Badam"])
    assert not hit("Brian Chesky", ["Adam Grenier", "Ada Chen Rekhi"])
