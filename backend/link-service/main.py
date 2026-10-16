from fastapi import FastAPI

app = FastAPI(title="LinkNote link service")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "link-service"}


@app.get("/ready")
def ready() -> dict[str, str]:
    return {"status": "ready", "service": "link-service"}
