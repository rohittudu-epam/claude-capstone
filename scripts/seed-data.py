#!/usr/bin/env python3
"""Seed the database with sample notes, tags, and links for testing and demonstration.

Usage:
    python scripts/seed-data.py --email user@example.com

This creates a demo user (if it doesn't exist) and populates their account with:
- 18 sample notes across various topics (AI, testing, productivity)
- Tags for organization
- Accepted links between related notes
- One rejected suggestion for testing

The seed operation is idempotent - safe to run multiple times.
"""

import argparse
import sys
from pathlib import Path

# Add backend to path
BACKEND_DIR = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from shared.seed_utils import run_seed


def main():
    """CLI entry point for manual seeding."""
    parser = argparse.ArgumentParser(
        description="Seed database with sample notes and links (idempotent)"
    )
    parser.add_argument(
        "--email",
        default="demo@example.com",
        help="Email for demo user (default: demo@example.com)",
    )
    parser.add_argument(
        "--password",
        default="demo123456",
        help="Password for demo user (default: demo123456)",
    )
    args = parser.parse_args()

    try:
        summary = run_seed(email=args.email, password=args.password)
        print(f"   Access the app at http://localhost:3000")
        print()
        return 0
    except Exception as e:
        print(f"\n❌ Seed failed: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
