from app.retrieval.rrf import reciprocal_rank_fusion


def test_rrf_both_lists_agree_on_top():
    fused = reciprocal_rank_fusion([["a", "b", "c"], ["a", "c", "d"]])
    assert fused[0][0] == "a"


def test_rrf_sparse_only_hit_still_ranks():
    fused = reciprocal_rank_fusion([[], ["z"]])
    assert fused[0][0] == "z"


def test_rrf_neither_hits_is_empty():
    assert reciprocal_rank_fusion([[], []]) == []
