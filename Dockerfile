FROM python:3.11-slim AS builder

WORKDIR /app
COPY pyproject.toml .
COPY src/ src/
RUN pip install --no-cache-dir .

FROM python:3.11-slim

LABEL org.opencontainers.image.title="CineMatch-AI" \
      org.opencontainers.image.description="Movie recommendation engine" \
      security.non-root="true"

WORKDIR /app
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY src/ src/
COPY alembic.ini .

RUN groupadd -r cinematch && useradd -r -g cinematch -u 1000 -d /app cinematch \
    && chown -R cinematch:cinematch /app

ENV PYTHONPATH=/app/src
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"]

USER 1000

# Run migrations then start server
CMD ["sh", "-c", "alembic upgrade head && uvicorn cinematch.main:app --host 0.0.0.0 --port 8000"]
