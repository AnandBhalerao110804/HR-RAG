"""CLI to (re-)index policy documents into the Chroma vector store.

Usage: python -m hr_rag.ingest data/policies/
"""

import sys
from pathlib import Path

from hr_rag.sources.vector_store import index_policy_docs


def main():
    if len(sys.argv) != 2:
        print("Usage: python -m hr_rag.ingest <policies_dir>")
        sys.exit(1)

    policies_dir = Path(sys.argv[1])
    if not policies_dir.is_dir():
        print(f"Not a directory: {policies_dir}")
        sys.exit(1)

    count = index_policy_docs(policies_dir)
    print(f"Indexed {count} policy chunks from {policies_dir}")


if __name__ == "__main__":
    main()
