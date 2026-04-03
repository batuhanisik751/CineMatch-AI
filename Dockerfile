FROM python:3.11-slim AS builder

WORKDIR /app
COPY pyproject.toml .
RUN pip install --no-cache-dir .

FROM python:3.11-slim

WORKDIR /app
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY src/ src/
COPY alembic/ alembic/
COPY alembic.ini .

ENV PYTHONPATH=/app/src
EXPOSE 8000

# Run migrations then start server
CMD ["sh", "-c", "alembic upgrade head && uvicorn cinematch.main:app --host 0.0.0.0 --port 8000"]
