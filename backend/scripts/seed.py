"""Seed database with demo data.

This module is invoked by Docker Compose's seed service.
It respects the SEED_ON_START environment variable.
"""

import os
import sys

# Ensure shared module is importable
from shared.seed_utils import run_seed


def main() -> int:
    """Run seeding if SEED_ON_START is true."""
    seed_on_start = os.getenv("SEED_ON_START", "false").lower() in ("true", "1", "yes")

    if not seed_on_start:
        print("ℹ️  SEED_ON_START=false, skipping seed")
        return 0

    email = os.getenv("SEED_DEMO_EMAIL", "demo@linknote.local")
    password = os.getenv("SEED_DEMO_PASSWORD", "demo123456")

    try:
        run_seed(email=email, password=password)
        return 0
    except Exception as e:
        print(f"❌ Seed failed: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
