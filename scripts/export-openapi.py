"""Writes each service's OpenAPI document to docs/api/<service>.json.

Usage (from the repo root, with the backend requirements installed):
    python scripts/export-openapi.py

The documents are generated from the FastAPI apps, so they cannot drift from the code. The apps are
imported but not started: no database or Redis is contacted.
"""

import importlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"
OUT = ROOT / "docs" / "api"

SERVICES = {
    "auth-service": "auth_service.main",
    "note-service": "note_service.main",
    "link-service": "link_service.main",
    "graph-service": "graph_service.main",
}

# Settings validation needs these; the values are placeholders and never used to sign anything real.
os.environ.setdefault("DATABASE_URL", "postgresql://openapi:openapi@localhost:5432/openapi")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379")
os.environ.setdefault("JWT_SECRET_KEY", "openapi-export-placeholder-not-a-secret-000000")

for path in [BACKEND, *(BACKEND / name for name in SERVICES)]:
    sys.path.insert(0, str(path))


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, module_name in SERVICES.items():
        app = importlib.import_module(module_name).app
        document = json.dumps(app.openapi(), indent=2, sort_keys=True) + "\n"
        (OUT / f"{name}.json").write_text(document, encoding="utf-8", newline="\n")
        print(f"wrote docs/api/{name}.json ({len(app.openapi()['paths'])} paths)")


if __name__ == "__main__":
    main()
