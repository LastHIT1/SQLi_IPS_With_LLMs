#!/bin/sh

echo "Waiting for postgres..."

while ! nc -z database 5432; do
  sleep 0.1
done

echo "PostgreSQL started"

# Skip guardrail during migrations to avoid false positive SQL injection detection
SKIP_GUARDRAIL=1 uv run manage.py migrate --noinput

exec "$@"