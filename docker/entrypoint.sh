#!/bin/sh
set -e

# Idempotent first-boot seeding: only seed/ingest if not already present, so
# a restart of an already-seeded volume never wipes data. See
# TECHNICAL_OVERVIEW.md / the AWS deployment plan for why this is a fresh
# regenerate from source (seed_employees.py + data/policies/*.md) rather
# than a migration of any pre-existing database file.

if [ ! -f /app/data/employees.db ]; then
    echo "No employees.db found -- seeding..."
    python data/seed_employees.py
fi

if [ ! -d /app/data/chroma_store ] || [ -z "$(ls -A /app/data/chroma_store 2>/dev/null)" ]; then
    echo "No chroma_store found -- ingesting policy docs..."
    python -m hr_rag.ingest data/policies/
fi

exec uvicorn api:app --host 0.0.0.0 --port 8000
