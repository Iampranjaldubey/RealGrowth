# syntax=docker/dockerfile:1

# ---- deps: install once, cached independently of source changes -----------
FROM python:3.11-slim AS deps
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ---- build: create the SQLite warehouse from the raw CSVs -----------------
# Building the database in the image means the running container never
# depends on pandas or a build toolchain, and the ETL is reproducible from the
# same source tree that gets deployed. The ETL itself is stdlib-only, so this
# stage needs no pip install at all.
FROM python:3.11-slim AS build
WORKDIR /build
COPY backend/src ./backend/src
COPY data/raw ./data/raw
COPY data/reference ./data/reference
RUN PYTHONPATH=backend/src python -m realgrowth.etl \
        --raw-dir data/raw \
        --reference data/reference/countries.csv \
        --output data/realgrowth.db \
        --strict \
        --report data/quality-report.json

# ---- runtime: slim, non-root, no build tools -------------------------------
FROM python:3.11-slim AS runtime
WORKDIR /app

RUN groupadd --system app && useradd --system --gid app --home-dir /app app

COPY --from=deps /install /usr/local
COPY backend/src ./src
COPY --from=build /build/data/realgrowth.db ./data/realgrowth.db
COPY --from=build /build/data/quality-report.json ./data/quality-report.json

ENV PYTHONPATH=/app/src \
    PYTHONUNBUFFERED=1 \
    REALGROWTH_DATABASE_PATH=/app/data/realgrowth.db \
    REALGROWTH_ENVIRONMENT=production

RUN chown -R app:app /app
USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request as u; u.urlopen('http://localhost:8000/api/v1/meta/health', timeout=3)" || exit 1

CMD ["uvicorn", "realgrowth.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
