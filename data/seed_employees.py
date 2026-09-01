"""Creates and seeds the local employees.db SQLite database with sample data
across the full 5-table schema (employees, employee_leaves, leave_requests,
compensation, expense_reports)."""

import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from hr_rag.config import EMPLOYEE_DB_PATH

SCHEMA = """
-- Core identity + role data. Anchors self-scoping, tenure calcs (parental
-- leave tiers, PTO accrual), and role-based eligibility (remote work).
CREATE TABLE employees (
  employee_id      TEXT PRIMARY KEY,
  full_name        TEXT,
  email            TEXT,
  job_title        TEXT,        -- drives role-based eligibility, e.g. remote work
  department       TEXT,
  employment_type  TEXT,        -- full_time / part_time / contractor
  start_date       DATE,        -- drives tenure-based eligibility
  location         TEXT,        -- city/country, for region-specific policy variants
  manager_id       TEXT,        -- nullable, FK -> employees.employee_id (future RBAC)
  status           TEXT         -- active / on_leave / terminated
);

-- One row per employee per leave_year, tracking PTO and sick leave together.
-- Replaces the earlier long-format leave_balances table.
CREATE TABLE employee_leaves (
  leave_id               TEXT PRIMARY KEY,
  employee_id            TEXT,       -- FK -> employees
  leave_year             INTEGER,    -- calendar year this record applies to
  available_leaves       REAL,       -- remaining PTO/general leave balance
  used_leaves            REAL,       -- PTO/general leave used so far this year
  sick_leaves_available  REAL,
  sick_leaves_used       REAL,
  accrual_per_month      REAL,       -- PTO accrual rate
  carry_forward_days     REAL,       -- days carried over from the previous year
  last_updated           DATE
);

-- Leave request history/status -- supports scheduling and "was it approved" queries.
CREATE TABLE leave_requests (
  request_id     TEXT PRIMARY KEY,
  employee_id    TEXT,          -- FK -> employees
  leave_type     TEXT,
  start_date     DATE,
  end_date       DATE,
  status         TEXT,          -- pending / approved / denied
  requested_on   DATE,
  approved_by    TEXT           -- nullable
);

-- Sensitive comp data -- the clearest stress-test for the self-scoping rule (FR4).
CREATE TABLE compensation (
  comp_id        TEXT PRIMARY KEY,
  employee_id    TEXT,          -- FK -> employees
  base_salary    REAL,
  currency       TEXT,
  pay_band       TEXT,
  effective_date DATE
);

-- Ties directly to the expense policy's approval tiers -- good for a cross-source
-- (SQL + vector) test query, e.g. "I want to expense $600, do I need extra approval?"
CREATE TABLE expense_reports (
  expense_id     TEXT PRIMARY KEY,
  employee_id    TEXT,          -- FK -> employees
  category       TEXT,          -- travel / meals / equipment / other
  amount         REAL,
  currency       TEXT,
  status         TEXT,          -- pending / approved / denied / reimbursed
  submitted_date TEXT,
  approver_id    TEXT           -- nullable
);
"""

EMPLOYEES = [
    # employee_id, full_name, email, job_title, department, employment_type,
    # start_date, location, manager_id, status
    ("E1001", "Priya Nair", "priya.nair@company.com", "Senior Software Engineer",
     "Engineering", "full_time", "2019-03-04", "Bengaluru, India", "E1003", "active"),
    ("E1002", "Marcus Lee", "marcus.lee@company.com", "Account Executive",
     "Sales", "full_time", "2023-01-10", "Austin, TX, USA", "E1003", "active"),
    ("E1003", "Sofia Reyes", "sofia.reyes@company.com", "People Ops Manager",
     "People Ops", "full_time", "2021-07-19", "Madrid, Spain", None, "active"),
    ("E1004", "Daniel Okafor", "daniel.okafor@company.com", "Software Engineer",
     "Engineering", "full_time", "2025-11-02", "Lagos, Nigeria", "E1001", "active"),
]

EMPLOYEE_LEAVES = [
    # leave_id, employee_id, leave_year, available_leaves, used_leaves,
    # sick_leaves_available, sick_leaves_used, accrual_per_month,
    # carry_forward_days, last_updated
    ("EL1001-2026", "E1001", 2026, 12.5, 8.5, 5.0, 2.0, 1.75, 3.0, "2026-08-01"),
    ("EL1002-2026", "E1002", 2026, 4.0, 2.0, 3.0, 1.0, 1.75, 0.0, "2026-08-01"),
    ("EL1003-2026", "E1003", 2026, 18.0, 3.0, 6.0, 0.0, 1.75, 5.0, "2026-08-01"),
    ("EL1004-2026", "E1004", 2026, 2.0, 0.0, 1.0, 0.0, 1.75, 0.0, "2026-08-01"),
]

LEAVE_REQUESTS = [
    # request_id, employee_id, leave_type, start_date, end_date, status, requested_on, approved_by
    ("REQ001", "E1001", "PTO", "2026-09-01", "2026-09-05", "approved", "2026-08-01", "E1003"),
    ("REQ002", "E1002", "PTO", "2026-10-10", "2026-10-12", "pending", "2026-08-20", None),
    ("REQ003", "E1004", "sick", "2026-08-15", "2026-08-16", "approved", "2026-08-14", "E1001"),
]

COMPENSATION = [
    # comp_id, employee_id, base_salary, currency, pay_band, effective_date
    ("COMP1001", "E1001", 145000.0, "USD", "E4", "2025-04-01"),
    ("COMP1002", "E1002", 78000.0, "USD", "S2", "2026-01-10"),
    ("COMP1003", "E1003", 132000.0, "USD", "M3", "2024-07-19"),
    ("COMP1004", "E1004", 105000.0, "USD", "E2", "2025-11-02"),
]

EXPENSE_REPORTS = [
    # expense_id, employee_id, category, amount, currency, status, submitted_date, approver_id
    ("EXP001", "E1002", "travel", 450.0, "USD", "approved", "2026-07-01", "E1003"),
    ("EXP002", "E1001", "equipment", 620.0, "USD", "pending", "2026-08-20", None),
    ("EXP003", "E1004", "meals", 85.0, "USD", "reimbursed", "2026-06-15", "E1001"),
]


def seed():
    EMPLOYEE_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(EMPLOYEE_DB_PATH)
    try:
        for table in ("employees", "employee_leaves", "leave_requests", "compensation", "expense_reports"):
            conn.execute(f"DROP TABLE IF EXISTS {table}")
        conn.executescript(SCHEMA)

        conn.executemany(
            "INSERT INTO employees "
            "(employee_id, full_name, email, job_title, department, employment_type, "
            "start_date, location, manager_id, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            EMPLOYEES,
        )
        conn.executemany(
            "INSERT INTO employee_leaves "
            "(leave_id, employee_id, leave_year, available_leaves, used_leaves, "
            "sick_leaves_available, sick_leaves_used, accrual_per_month, "
            "carry_forward_days, last_updated) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            EMPLOYEE_LEAVES,
        )
        conn.executemany(
            "INSERT INTO leave_requests "
            "(request_id, employee_id, leave_type, start_date, end_date, status, requested_on, approved_by) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            LEAVE_REQUESTS,
        )
        conn.executemany(
            "INSERT INTO compensation "
            "(comp_id, employee_id, base_salary, currency, pay_band, effective_date) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            COMPENSATION,
        )
        conn.executemany(
            "INSERT INTO expense_reports "
            "(expense_id, employee_id, category, amount, currency, status, submitted_date, approver_id) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            EXPENSE_REPORTS,
        )
        conn.commit()
    finally:
        conn.close()
    print(f"Seeded {len(EMPLOYEES)} employees across 5 tables into {EMPLOYEE_DB_PATH}")


if __name__ == "__main__":
    seed()
