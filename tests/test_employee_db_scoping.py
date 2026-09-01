import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from data.seed_employees import seed
from hr_rag.sources import employee_db


def setup_module():
    seed()


def test_returns_only_the_authenticated_employees_core_record():
    chunks = employee_db.search("E1001", "what's my leave balance")
    core = chunks[0]
    assert core.metadata["employee_id"] == "E1001"
    # manager_id legitimately references another employee (E1003) -- that's
    # not a scoping leak. What must never appear is another employee's own
    # identity as the *subject* of the record.
    for other_name in ("Marcus Lee", "Sofia Reyes", "Daniel Okafor"):
        assert other_name not in core.text


def test_unknown_employee_id_returns_nothing():
    assert employee_db.search("NOPE", "what's my balance") == []


def test_leave_balance_keyword_pulls_in_employee_leaves_table():
    chunks = employee_db.search("E1002", "what's my PTO balance?")
    tables = [c.metadata.get("table") for c in chunks]
    assert "employee_leaves" in tables


def test_non_leave_query_does_not_pull_in_compensation():
    chunks = employee_db.search("E1002", "what's my department?")
    tables = [c.metadata.get("table") for c in chunks]
    assert "compensation" not in tables


def test_compensation_is_scoped_to_requester_only():
    comp = employee_db.get_my_compensation("E1002")
    assert comp is not None
    assert comp["base_salary"] == 78000.0
    assert employee_db.get_my_compensation("NOPE") is None


def test_get_my_leaves_is_scoped():
    leaves = employee_db.get_my_leaves("E1004", leave_year=2026)
    assert leaves["available_leaves"] == 2.0
    assert leaves["sick_leaves_available"] == 1.0
    assert employee_db.get_my_leaves("NOPE", leave_year=2026) is None


def test_get_my_leaves_defaults_to_current_year():
    from datetime import date

    leaves = employee_db.get_my_leaves("E1001")
    if date.today().year == 2026:
        assert leaves is not None
        assert leaves["used_leaves"] == 8.5
    else:
        assert leaves is None


def test_get_my_expense_reports_is_scoped():
    expenses = employee_db.get_my_expense_reports("E1001")
    assert len(expenses) == 1
    assert expenses[0]["expense_id"] == "EXP002"
