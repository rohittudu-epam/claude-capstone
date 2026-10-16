from fastapi import FastAPI

app = FastAPI(title="LinkNote note service")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "note-service"}


@app.get("/ready")
def ready() -> dict[str, str]:
    return {"status": "ready", "service": "note-service"}
