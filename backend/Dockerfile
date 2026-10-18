# One image definition for every backend service.
#   docker build -f backend/Dockerfile --build-arg SERVICE=note-service backend
# The build context is backend/ so each service can import the shared package.
FROM python:3.14-slim

ARG SERVICE
RUN test -n "$SERVICE" || (echo "build with --build-arg SERVICE=<service dir>" && false)

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY shared ./shared
COPY alembic.ini ./
COPY migrations ./migrations
COPY scripts ./scripts
COPY ${SERVICE}/ ./

RUN useradd --system --uid 10001 app && chown -R app /app
USER app

EXPOSE 8000
# Each service directory holds one package named after it (note-service -> note_service).
ENV SERVICE_DIR=${SERVICE}
CMD ["sh", "-c", "exec uvicorn $(echo $SERVICE_DIR | tr - _).main:app --host 0.0.0.0 --port 8000 --no-access-log"]
