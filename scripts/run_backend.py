#!/usr/bin/env python
"""
Run the GridironIQ FastAPI backend with uvicorn.

Usage (from repo root):

    python scripts/run_backend.py
"""

import uvicorn

try:
    from pathlib import Path

    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass


def main() -> None:
    uvicorn.run("gridironiq.api:app", host="127.0.0.1", port=8000, reload=True)


if __name__ == "__main__":
    main()

