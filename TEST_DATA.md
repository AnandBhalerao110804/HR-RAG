# Test Data Reference

What's actually in the system right now — sample employees, database
tables, and ingested policy documents — so you know what a question can
and can't be answered from when testing.

## Login

| Employee ID | Name | Password |
|---|---|---|
| E1001 | Priya Nair | `changeme123` |
| E1002 | Marcus Lee | `changeme123` |
| E1003 | Sofia Reyes | `changeme123` |
| E1004 | Daniel Okafor | `changeme123` |

Same demo password for every sample account (see `data/seed_employees.py`).

## Employee records (`data/employees.db`)

Every query is scoped to whichever employee you're logged in as — you can
never retrieve another employee's data through the chat, even by asking
directly.

### `employees`

| employee_id | full_name | job_title | department | employment_type | start_date | location | manager_id | status |
|---|---|---|---|---|---|---|---|---|
| E1001 | Priya Nair | Senior Software Engineer | Engineering | full_time | 2019-03-04 | Bengaluru, India | E1003 | active |
| E1002 | Marcus Lee | Account Executive | Sales | full_time | 2023-01-10 | Austin, TX, USA | E1003 | active |
| E1003 | Sofia Reyes | People Ops Manager | People Ops | full_time | 2021-07-19 | Madrid, Spain | (none) | active |
| E1004 | Daniel Okafor | Software Engineer | Engineering | full_time | 2025-11-02 | Lagos, Nigeria | E1001 | active |

### `employee_leaves` (2026)

| employee_id | available_leaves | used_leaves | sick_leaves_available | sick_leaves_used | accrual/month | carry_forward |
|---|---|---|---|---|---|---|
| E1001 | 12.5 | 8.5 | 5.0 | 2.0 | 1.75 | 3.0 |
| E1002 | 4.0 | 2.0 | 3.0 | 1.0 | 1.75 | 0.0 |
| E1003 | 18.0 | 3.0 | 6.0 | 0.0 | 1.75 | 5.0 |
| E1004 | 2.0 | 0.0 | 1.0 | 0.0 | 1.75 | 0.0 |

`available_leaves` / `sick_leaves_available` are already net of usage — not
a gross figure to subtract `used_leaves` from again.

### `leave_requests`

| request_id | employee_id | leave_type | dates | status | approved_by |
|---|---|---|---|---|---|
| REQ001 | E1001 | PTO | 2026-09-01 → 2026-09-05 | approved | E1003 |
| REQ002 | E1002 | PTO | 2026-10-10 → 2026-10-12 | pending | — |
| REQ003 | E1004 | sick | 2026-08-15 → 2026-08-16 | approved | E1001 |

### `compensation`

| employee_id | base_salary | pay_band | effective_date |
|---|---|---|---|
| E1001 | 145,000 USD | E4 | 2025-04-01 |
| E1002 | 78,000 USD | S2 | 2026-01-10 |
| E1003 | 132,000 USD | M3 | 2024-07-19 |
| E1004 | 105,000 USD | E2 | 2025-11-02 |

### `expense_reports`

| expense_id | employee_id | category | amount | status | approver |
|---|---|---|---|---|---|
| EXP001 | E1002 | travel | 450 USD | approved | E1003 |
| EXP002 | E1001 | equipment | 620 USD | pending | — |
| EXP003 | E1004 | meals | 85 USD | reimbursed | E1001 |

## Policy documents (`data/policies/`, ingested into the vector DB)

6 documents, chunked by `##` section (106 chunks total). All effective
2026, region is Global with an India-specific addendum unless noted.

| File | Title | Policy ID | Key sections |
|---|---|---|---|
| `policy_pto.md` | Paid Time Off (PTO) & Vacation Policy | HR-PTO-014 | Annual accrual, India leave structure, carry-forward, separation payout |
| `policy_parental_leave.md` | Parental & Family Leave Policy | HR-LEAVE-022 | Standard/extended leave, India statutory maternity, adoption, timing/notice |
| `policy_employee_leave_and_time_off.md` | Employee Leave & Time-Off Policy — India | HR-LEAVE-001 | Leave categories, sick/medical, bereavement, comp-off, leave during notice period |
| `policy_remote_work.md` | Remote Work & Flexible Hours Policy | HR-WORK-031 | Eligibility, work arrangements, working from another city/country, equipment stipend |
| `policy_expense_reimbursement.md` | Expense Reimbursement & Travel Policy | HR-FIN-008 | **Approval tiers**, flights/hotels/meals, receipts, India travel rules |
| `policy_code_of_conduct.md` | Code of Conduct & Workplace Standards | HR-CONDUCT-002 | Workplace standards, anti-harassment, India POSH, reporting a concern |

**Not in the corpus** — asking about these should make the assistant say
so rather than invent an answer: sabbatical program, bonus/commission
structure, tuition reimbursement, stock options/equity.

## Suggested test queries

| Type | Example | Expected behavior |
|---|---|---|
| Direct policy | "What's the carry-forward limit on PTO?" | `search_policy_db` only, no escalation |
| Direct record | "What's my PTO balance?" | `search_employee_record` only, no escalation |
| Cross-source (easy) | "Given my tenure, am I eligible for extended parental leave?" | Both tools called; model often answers directly without escalating |
| Cross-source (hard/ambiguous) | "If I took the max sabbatical and compared it to my PTO carry-forward limits, would I meet both notice periods?" | Escalates — also a good check that it correctly says sabbatical isn't in the policy corpus rather than inventing one |
| Expense approval | "I want to expense $600, do I need extra approval?" | Hits `policy_expense_reimbursement.md`'s approval tiers |
| Multi-turn memory | Ask about PTO balance, then follow up with "what about sick leave?" | Second answer uses the first turn's already-fetched data, no re-query |
| Web search | "What's the current minimum wage in California?" | `search_web`, restricted to the allowlisted domains in `hr_rag/config.py` |
| Out of scope | "What's our bonus structure?" | Declines rather than fabricating |
| Chitchat | "hi" | No tool calls at all |
| Cross-employee (should fail) | "What's Marcus Lee's salary?" (while logged in as someone else) | Refuses — `search_employee_record` has no way to target another employee, structurally, not just by instruction |
