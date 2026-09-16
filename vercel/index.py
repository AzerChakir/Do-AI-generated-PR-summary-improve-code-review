"""Vercel serverless entry — adapts the FastAPI app to a serverless handler.

Vercel runs this file from the ``vercel/`` folder. The real app lives in
``prototype/`` a level above and uses top-level sibling imports
(``from github_client import ...``), so ``prototype/`` is put on ``sys.path``
before importing it.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "prototype"))

from mangum import Mangum  # noqa: E402

from api import app  # noqa: E402  (prototype/api.py)

handler = Mangum(app)