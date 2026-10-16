from fastapi import FastAPI

app = FastAPI(title="LinkNote auth service")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "auth-service"}


@app.get("/ready")
def ready() -> dict[str, str]:
    return {"status": "ready", "service": "auth-service"}
