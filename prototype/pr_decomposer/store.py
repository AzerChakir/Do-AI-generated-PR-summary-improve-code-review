"""Report storage for the dashboard API.

Stores decomposition reports as JSON files under <prototype>/data/reports so
the web dashboard can list and re-read past analyses without re-running the
LLM. Zero external dependencies (plain stdlib json + pathlib).

Layout
------
    data/reports/<report_id>.json      full report payload (json-serializable)
    data/reports/<report_id>.meta.json  { report_id, title, repo, pr, verdict,
                                         analyzed_at_iso, concerns, flags }
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

DATA_ROOT = Path(__file__).resolve().parent.parent / "data" / "reports"


class ReportNotFoundError(Exception):
    pass


def _slug(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-")
    return value or "anonymous"


def make_report_id(owner: str = "", repo: str = "", pr_number: int | None = None) -> str:
    parts = [p for p in (_slug(owner), _slug(repo)) if p]
    if pr_number is not None:
        parts.append(f"pr{pr_number}")
    return "-".join(parts) or f"pr-{int(datetime.now(timezone.utc).timestamp())}"


def save_report(report: dict, report_id: str | None = None) -> str:
    """Persist a report payload dict; returns its report_id."""
    report_id = report_id or make_report_id(
        repo=report.get("repo", ""), pr_number=report.get("pr_number"),
    )
    DATA_ROOT.mkdir(parents=True, exist_ok=True)
    payload = dict(report)
    payload["report_id"] = report_id
    payload["analyzed_at_iso"] = report.get(
        "analyzed_at_iso", datetime.now(timezone.utc).isoformat(),
    )
    (DATA_ROOT / f"{report_id}.json").write_text(
        json.dumps(payload, indent=2, default=str), encoding="utf-8",
    )
    meta = {
        "report_id": report_id,
        "title": report.get("title", ""),
        "repo": report.get("repo", ""),
        "pr_number": report.get("pr_number"),
        "verdict": report.get("verdict", ""),
        "concerns": len(report.get("concerns", [])),
        "flags": len(report.get("flags", [])),
        "model": report.get("model", ""),
        "analyzed_at_iso": payload["analyzed_at_iso"],
    }
    (DATA_ROOT / f"{report_id}.meta.json").write_text(
        json.dumps(meta, indent=2, default=str), encoding="utf-8",
    )
    return report_id


def load_report(report_id: str) -> dict:
    path = DATA_ROOT / f"{report_id}.json"
    if not path.exists():
        raise ReportNotFoundError(report_id)
    return json.loads(path.read_text(encoding="utf-8"))


def list_reports() -> list[dict]:
    if not DATA_ROOT.exists():
        return []
    metas = []
    for path in sorted(DATA_ROOT.glob("*.meta.json"), reverse=True):
        metas.append(json.loads(path.read_text(encoding="utf-8")))
    metas.sort(key=lambda m: m.get("analyzed_at_iso", ""), reverse=True)
    return metas


def delete_report(report_id: str) -> None:
    for suffix in (".json", ".meta.json"):
        path = DATA_ROOT / f"{report_id}{suffix}"
        if path.exists():
            path.unlink()