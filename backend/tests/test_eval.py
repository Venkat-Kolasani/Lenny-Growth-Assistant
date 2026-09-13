from app.retrieval.eval_hit import hit


def test_guest_match_is_substring():
    assert hit("Aishwarya Naresh Reganti", ["Aishwarya Naresh Reganti + Kiriti Badam"])
    assert not hit("Brian Chesky", ["Adam Grenier", "Ada Chen Rekhi"])
