from hr_rag import session_store


def test_create_and_get_session():
    token = session_store.create_session("E1001")
    session = session_store.get_session(token)
    assert session is not None
    assert session.employee_id == "E1001"


def test_unknown_token_returns_none():
    assert session_store.get_session("not-a-real-token") is None


def test_delete_session_invalidates_token():
    token = session_store.create_session("E1002")
    session_store.delete_session(token)
    assert session_store.get_session(token) is None


def test_tokens_are_unique():
    token1 = session_store.create_session("E1001")
    token2 = session_store.create_session("E1001")
    assert token1 != token2
