"""Scoped access to employee records.

v1 access model (PRD section 4): every query is scoped to the authenticated
employee's own record. Every function here takes employee_id as a required
first argument and uses it in the WHERE clause via a parameterized query --
there is no free-text SQL, and no function returns rows outside that one
employee, across any of the five tables (employees, employee_leaves,
leave_requests, compensation, expense_reports). This is what makes the
access control real at the data layer rather than a prompt-level
instruction (NFR-Security) -- it applies equally to compensation, the
clearest stress-test for the self-scoping rule.

RBAC EXTENSION POINT: when manager/HR-admin roles are added (PRD section 8,
deferred), broader-visibility queries must be added as new, explicitly-scoped
functions here (e.g. get_team_leaves(manager_id), gated on the
requester actually being that employee's manager via employees.manager_id)
-- never by loosening these functions or by allowing arbitrary employee_id
substitution without a role check.
"""

import sqlite3
from datetime import date, datetime

from hr_rag.config import EMPLOYEE_DB_PATH
from hr_rag.models import RetrievedChunk

_EMPLOYEE_COLUMNS = (
    "employee_id, full_name, email, job_title, department, employment_type, "
    "start_date, location, manager_id, status"
)


def _connect():
    return sqlite3.connect(EMPLOYEE_DB_PATH)


def _rows_as_dicts(cur, rows) -> list[dict]:
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in rows]


def _tenure_years(start_date: str) -> float:
    start = datetime.strptime(start_date, "%Y-%m-%d").date()
    return round((date.today() - start).days / 365.25, 2)


def get_my_record(employee_id: str) -> dict | None:
    conn = _connect()
    try:
        cur = conn.execute(
            f"SELECT {_EMPLOYEE_COLUMNS} FROM employees WHERE employee_id = ?",
            (employee_id,),
        )
        row = cur.fetchone()
        if row is None:
            return None
        record = _rows_as_dicts(cur, [row])[0]
        record["tenure_years"] = _tenure_years(record["start_date"])
        return record
    finally:
        conn.close()


def get_my_leaves(employee_id: str, leave_year: int | None = None) -> dict | None:
    """Returns the employee's leave summary (available/used PTO and sick
    leave) for `leave_year`, defaulting to the current calendar year."""
    leave_year = leave_year or date.today().year
    conn = _connect()
    try:
        cur = conn.execute(
            "SELECT leave_year, available_leaves, used_leaves, sick_leaves_available, "
            "sick_leaves_used, accrual_per_month, carry_forward_days, last_updated "
            "FROM employee_leaves WHERE employee_id = ? AND leave_year = ?",
            (employee_id, leave_year),
        )
        row = cur.fetchone()
        return _rows_as_dicts(cur, [row])[0] if row else None
    finally:
        conn.close()


def get_my_leave_requests(employee_id: str) -> list[dict]:
    conn = _connect()
    try:
        cur = conn.execute(
            "SELECT request_id, leave_type, start_date, end_date, status, requested_on, approved_by "
            "FROM leave_requests WHERE employee_id = ? ORDER BY requested_on DESC",
            (employee_id,),
        )
        return _rows_as_dicts(cur, cur.fetchall())
    finally:
        conn.close()


def get_my_compensation(employee_id: str) -> dict | None:
    conn = _connect()
    try:
        cur = conn.execute(
            "SELECT base_salary, currency, pay_band, effective_date "
            "FROM compensation WHERE employee_id = ? ORDER BY effective_date DESC LIMIT 1",
            (employee_id,),
        )
        row = cur.fetchone()
        return _rows_as_dicts(cur, [row])[0] if row else None
    finally:
        conn.close()


def get_my_expense_reports(employee_id: str) -> list[dict]:
    conn = _connect()
    try:
        cur = conn.execute(
            "SELECT expense_id, category, amount, currency, status, submitted_date, approver_id "
            "FROM expense_reports WHERE employee_id = ? ORDER BY submitted_date DESC",
            (employee_id,),
        )
        return _rows_as_dicts(cur, cur.fetchall())
    finally:
        conn.close()


# Query keywords that gate which auxiliary tables get pulled into a
# retrieval alongside the always-included core record. Keeps compensation
# (sensitive) and other tables out of unrelated answers rather than
# dumping the whole employee profile into every prompt.
_LEAVE_BALANCE_KEYWORDS = (
    "balance", "leave", "pto", "sick", "accrual", "days left",
    "days do i have", "time off", "days off",
)
_LEAVE_REQUEST_KEYWORDS = ("request", "approved", "pending", "denied", "time off i booked", "schedule")
_COMPENSATION_KEYWORDS = ("salary", "pay band", "compensation", "comp ", "how much do i make", "raise")
_EXPENSE_KEYWORDS = ("expense", "reimburse", "reimbursement")


def _matches(query: str, keywords: tuple[str, ...]) -> bool:
    lowered = query.lower()
    return any(kw in lowered for kw in keywords)


def search(employee_id: str, query: str) -> list[RetrievedChunk]:
    """Entry point used by the pipeline's employee_db source.

    Always includes the employee's core record (needed for tenure/role/
    department-based eligibility checks even when not explicitly asked for),
    plus whichever auxiliary tables the query keywords indicate are relevant.
    Every lookup is scoped to `employee_id` -- see module docstring.
    """
    record = get_my_record(employee_id)
    if record is None:
        return []

    chunks = [
        RetrievedChunk(
            source="employee_db",
            text=(
                f"Employee record for {record['full_name']} ({record['employee_id']}): "
                f"job_title={record['job_title']}, department={record['department']}, "
                f"employment_type={record['employment_type']}, location={record['location']}, "
                f"start_date={record['start_date']}, tenure_years={record['tenure_years']}, "
                f"manager_id={record['manager_id']}, status={record['status']}."
            ),
            metadata=record,
        )
    ]

    if _matches(query, _LEAVE_BALANCE_KEYWORDS):
        leaves = get_my_leaves(employee_id)
        if leaves:
            text = (
                f"Leave summary for {leaves['leave_year']} (as of {leaves['last_updated']}): "
                f"the employee currently has {leaves['available_leaves']} regular leave days "
                f"remaining to use (this figure is already net of usage -- do not subtract "
                f"used_leaves from it again), and has used {leaves['used_leaves']} regular "
                f"leave days so far this year. Separately, {leaves['sick_leaves_available']} "
                f"sick leave days remain (also already net of usage), with "
                f"{leaves['sick_leaves_used']} sick days used so far this year. Regular leave "
                f"accrues at {leaves['accrual_per_month']} days/month, and "
                f"{leaves['carry_forward_days']} days were carried forward from the previous "
                f"year (already included in the remaining balance above)."
            )
            chunks.append(RetrievedChunk(source="employee_db", text=text, metadata={"table": "employee_leaves"}))

    if _matches(query, _LEAVE_REQUEST_KEYWORDS):
        requests = get_my_leave_requests(employee_id)
        if requests:
            text = "; ".join(
                f"{r['leave_type']} request {r['request_id']}: {r['start_date']} to {r['end_date']}, "
                f"status={r['status']}, requested_on={r['requested_on']}, approved_by={r['approved_by']}"
                for r in requests
            )
            chunks.append(RetrievedChunk(source="employee_db", text=text, metadata={"table": "leave_requests"}))

    if _matches(query, _COMPENSATION_KEYWORDS):
        comp = get_my_compensation(employee_id)
        if comp:
            text = (
                f"Current compensation: base_salary={comp['base_salary']} {comp['currency']}, "
                f"pay_band={comp['pay_band']}, effective_date={comp['effective_date']}."
            )
            chunks.append(RetrievedChunk(source="employee_db", text=text, metadata={"table": "compensation"}))

    if _matches(query, _EXPENSE_KEYWORDS):
        expenses = get_my_expense_reports(employee_id)
        if expenses:
            text = "; ".join(
                f"{e['category']} expense {e['expense_id']}: {e['amount']} {e['currency']}, "
                f"status={e['status']}, submitted={e['submitted_date']}, approver={e['approver_id']}"
                for e in expenses
            )
            chunks.append(RetrievedChunk(source="employee_db", text=text, metadata={"table": "expense_reports"}))

    return chunks
