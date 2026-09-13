from app.agent.router import route


def test_plain_question_is_qa():
    assert route("How do you measure activation?") == "qa"


def test_essay_phrasing_selects_ship30():
    assert route("Write me an essay on staying in the details") == "ship30_essay"
    assert route("Ship 30 style piece on pricing") == "ship30_essay"


def test_brief_phrasing_selects_growth_brief():
    assert route("Write a growth brief for our onboarding drop-off") == "growth_brief"
    assert route("Draft an experiment doc on activation") == "growth_brief"


def test_ambiguous_falls_back_to_qa():
    assert route("Tell me about essays founders write") == "qa"
