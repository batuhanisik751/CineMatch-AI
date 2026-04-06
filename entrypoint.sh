#!/bin/sh
set -e

# Render provides DATABASE_URL in postgres:// format.
# Transform it into the two variants the app needs:
#   CINEMATCH_DATABASE_URL      = postgresql+asyncpg://...  (async driver)
#   CINEMATCH_DATABASE_URL_SYNC = postgresql://...          (sync driver / Alembic)
# If these are already set explicitly, skip the transformation.
if [ -n "$DATABASE_URL" ] && [ -z "$CINEMATCH_DATABASE_URL" ]; then
  case "$DATABASE_URL" in
    postgres://*|postgresql://*)
      export CINEMATCH_DATABASE_URL_SYNC=$(echo "$DATABASE_URL" | sed 's|^postgres://|postgresql://|')
      export CINEMATCH_DATABASE_URL=$(echo "$DATABASE_URL" | sed 's|^postgres://|postgresql+asyncpg://|')
      ;;
    *)
      echo "ERROR: DATABASE_URL must start with postgres:// or postgresql://" >&2
      exit 1
      ;;
  esac
fi

# Run database migrations then start the server
alembic upgrade head
exec uvicorn cinematch.main:app --host 0.0.0.0 --port 8000
