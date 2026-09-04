"""Golden evaluation set for policy retrieval (Precision@k / Recall@k).

Every expected_chunk_ids entry was verified against the actually-ingested
Chroma collection (data/chroma_store, 106 chunks across 6 policy docs,
heading-based chunk ids like "policy_pto-8") -- not invented. If the policy
corpus under data/policies/ changes, this set needs re-checking against the
new chunk ids (see the ids/section-title dump in TECHNICAL_OVERVIEW.md's
retrieval section, or just inspect the collection directly).
"""

GOLDEN_SET = [
    {"query": "How many PTO days can I carry forward to next year?", "expected_chunk_ids": ["policy_pto-8"]},
    {"query": "What happens to my unused leave if I resign?", "expected_chunk_ids": ["policy_pto-14"]},
    {"query": "What's the annual PTO accrual rate?", "expected_chunk_ids": ["policy_pto-2"]},
    {"query": "What are the expense approval tiers?", "expected_chunk_ids": ["policy_expense_reimbursement-3"]},
    {"query": "What if I lose a receipt for an expense?", "expected_chunk_ids": ["policy_expense_reimbursement-8"]},
    {"query": "How long do I have to submit an expense report?", "expected_chunk_ids": ["policy_expense_reimbursement-9"]},
    {"query": "What's the corporate card policy?", "expected_chunk_ids": ["policy_expense_reimbursement-10"]},
    {"query": "What are the India statutory maternity benefits?", "expected_chunk_ids": ["policy_parental_leave-4"]},
    {"query": "How much notice do I need to give before parental leave?", "expected_chunk_ids": ["policy_parental_leave-8"]},
    {"query": "What support is there for nursing mothers returning to work?", "expected_chunk_ids": ["policy_parental_leave-11"]},
    {"query": "Am I eligible to work remotely from another country?", "expected_chunk_ids": ["policy_remote_work-6"]},
    {"query": "What's the home office equipment stipend?", "expected_chunk_ids": ["policy_remote_work-9"]},
    {"query": "What are the core working hours policy?", "expected_chunk_ids": ["policy_remote_work-4"]},
    {"query": "How do I report a workplace harassment concern?", "expected_chunk_ids": ["policy_code_of_conduct-7"]},
    {"query": "What are the POSH provisions for India?", "expected_chunk_ids": ["policy_code_of_conduct-5"]},
    {"query": "What counts as bereavement leave?", "expected_chunk_ids": ["policy_employee_leave_and_time_off-8"]},
    {"query": "What is compensatory off and when can I take it?", "expected_chunk_ids": ["policy_employee_leave_and_time_off-12"]},
    {
        "query": "What happens to my leave request if I'm on my notice period?",
        "expected_chunk_ids": ["policy_pto-9", "policy_employee_leave_and_time_off-14"],
    },
]
