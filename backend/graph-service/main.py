from fastapi import FastAPI

app = FastAPI(title="LinkNote graph service")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "graph-service"}


@app.get("/ready")
def ready() -> dict[str, str]:
    return {"status": "ready", "service": "graph-service"}
