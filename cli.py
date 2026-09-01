"""HR Portal RAG -- terminal dev/test harness.

Fast way to exercise hr_rag/agent.py without the web layer -- skips real
login (just picks an employee id like v1's CLI did), but the underlying
agent.run_turn() is exactly what api.py calls, so behavior matches the
web UI including multi-turn memory within one run of this script.
"""

import secrets
import sys

import anthropic
from langgraph.errors import GraphRecursionError

from hr_rag import agent
from hr_rag.guardrails import ASSISTANT_UNAVAILABLE_ANSWER
from hr_rag.logging_util import log_error
from hr_rag.sources.employee_db import get_my_record

SAMPLE_IDS = ["E1001", "E1002", "E1003", "E1004"]


def pick_employee() -> str:
    print("Sample employees:")
    for eid in SAMPLE_IDS:
        record = get_my_record(eid)
        name = record["full_name"] if record else "(not found)"
        print(f"  {eid} - {name}")
    while True:
        choice = input("Log in as employee id: ").strip().upper()
        if get_my_record(choice):
            return choice
        print("Unknown employee id, try again.")


def main():
    employee_id = pick_employee()
    token = secrets.token_urlsafe(16)  # local thread_id for this run only, no real session
    print(f"\nLogged in as {employee_id}. Ask an HR question (Ctrl+D to quit).\n")

    while True:
        try:
            query = input("> ").strip()
        except EOFError:
            print()
            break
        if not query:
            continue

        try:
            result = agent.run_turn(token, employee_id, query)
        except (anthropic.AnthropicError, GraphRecursionError) as e:
            log_error(employee_id=employee_id, query=query, error=e)
            print(f"\n{ASSISTANT_UNAVAILABLE_ANSWER}\n")
            continue

        print(f"\n{result.answer}\n")
        tag = " (escalated)" if result.escalated else ""
        print(f"[tools used: {', '.join(result.tools_used) or 'none'}{tag}]\n")


if __name__ == "__main__":
    sys.exit(main())
