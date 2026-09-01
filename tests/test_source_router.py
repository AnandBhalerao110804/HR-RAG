from hr_rag.routing.source_router import NONE_SOURCE, _heuristic_route


def test_my_balance_routes_to_employee_db():
    sources = _heuristic_route("What's my leave balance?")
    assert sources == ["employee_db"]


def test_policy_question_routes_to_policy_db():
    sources = _heuristic_route("Am I eligible for the sabbatical program?")
    assert "policy_db" in sources


def test_current_law_routes_to_web_search():
    sources = _heuristic_route("What's the current minimum wage in California?")
    assert sources == ["web_search"]


def test_cross_source_query_routes_to_both():
    sources = _heuristic_route("Am I eligible for the sabbatical policy given my tenure?")
    assert "policy_db" in sources
    assert "employee_db" in sources


def test_ambiguous_query_returns_no_heuristic_match():
    sources = _heuristic_route("hello there")
    assert sources == []


def test_greeting_routes_to_none_source():
    for greeting in ("hi", "Hello!", "hey", "thanks", "thank you so much"):
        assert _heuristic_route(greeting) == [NONE_SOURCE]


def test_greeting_embedded_in_a_real_question_is_not_short_circuited():
    sources = _heuristic_route("Hi, what's my leave balance?")
    assert sources != [NONE_SOURCE]
    assert "employee_db" in sources
