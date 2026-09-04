"""Catalog of the employee-record tables the agent can explicitly request
via search_employee_record's `tables` parameter (hr_rag/agent.py).

Single source of truth for what the model is told exists -- replaces the
old approach of guessing relevance from substring keyword matching on a
free-text query (hr_rag/sources/employee_db.py's old _matches() helper).

The core `employees` table is deliberately NOT here: it's not something
the model selects, it's always included automatically by
employee_db.search() regardless of what's requested.
"""

TABLE_CATALOG = {
    "employee_leaves": {
        "description": (
            "Regular (PTO) and sick leave balances for the current year -- "
            "days remaining, days used, accrual rate, carry-forward from "
            "last year."
        ),
        "columns": [
            "leave_year", "available_leaves", "used_leaves",
            "sick_leaves_available", "sick_leaves_used",
            "accrual_per_month", "carry_forward_days", "last_updated",
        ],
    },
    "leave_requests": {
        "description": (
            "History of specific leave requests the employee has "
            "submitted -- dates, status (pending/approved/denied), who "
            "approved them."
        ),
        "columns": [
            "request_id", "leave_type", "start_date", "end_date",
            "status", "requested_on", "approved_by",
        ],
    },
    "compensation": {
        "description": "Current salary, pay band, and effective date.",
        "columns": ["base_salary", "currency", "pay_band", "effective_date"],
    },
    "expense_reports": {
        "description": (
            "Submitted expense reports -- category, amount, currency, "
            "approval/reimbursement status, approver."
        ),
        "columns": [
            "expense_id", "category", "amount", "currency", "status",
            "submitted_date", "approver_id",
        ],
    },
}

TABLE_NAMES = list(TABLE_CATALOG.keys())
