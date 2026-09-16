"""Vercel serverless entry — adapts the FastAPI app to a serverless handler.

Vercel runs this file from the ``deploy/api/`` folder. The backend code lives
in ``deploy/backend/`` (it uses top-level sibling imports), so ``backend/`` is
put on ``sys.path`` before importing it.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from mangum import Mangum  # noqa: E402

from api import app  # noqa: E402  (deploy/backend/api.py)

handler = Mangum(app)