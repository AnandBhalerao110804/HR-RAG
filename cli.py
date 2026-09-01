"""HR Portal RAG prototype -- CLI entrypoint.

Simulates authentication by having the user pick an employee id at startup;
the pipeline scopes every employee_db query to that id (PRD section 4).
"""

import sys

from hr_rag import pipeline
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
    print(f"\nLogged in as {employee_id}. Ask an HR question (Ctrl+D to quit).\n")

    while True:
        try:
            query = input("> ").strip()
        except EOFError:
            print()
            break
        if not query:
            continue

        result = pipeline.run(employee_id, query)
        print(f"\n{result.answer}\n")
        tag = " (escalated)" if result.escalated else ""
        print(f"[sources: {', '.join(result.sources_selected) or 'none'}{tag}]\n")


if __name__ == "__main__":
    sys.exit(main())
