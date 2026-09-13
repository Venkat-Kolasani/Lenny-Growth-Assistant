from app.retrieval.rrf import reciprocal_rank_fusion
from app.retrieval.search import or_websearch


def test_rrf_both_lists_agree_on_top():
    fused = reciprocal_rank_fusion([["a", "b", "c"], ["a", "c", "d"]])
    assert fused[0][0] == "a"


def test_rrf_sparse_only_hit_still_ranks():
    fused = reciprocal_rank_fusion([[], ["z"]])
    assert fused[0][0] == "z"


def test_rrf_neither_hits_is_empty():
    assert reciprocal_rank_fusion([[], []]) == []


def test_or_websearch_keeps_guest_name_from_being_anded_away():
    q = or_websearch("Why do founders fail according to Ben Horowitz?")
    assert " OR " in q
    assert "Ben" in q and "Horowitz" in q
