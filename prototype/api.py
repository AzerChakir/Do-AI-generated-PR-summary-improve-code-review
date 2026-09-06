"""Dashboard REST API for the PR decomposer.

Serves the Angular dashboard: triggers analysis of a GitHub PR, stores the
report, lists past reports, and returns full reports. CORS is enabled for the
Angular dev server (http://localhost:4200).

Run:
    uvicorn api:app --reload --port 8000
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel

from github_client import GithubApiDiffSource
from pr_decomposer import ConfigError, run_pipeline
from pr_decomposer.config import PROTOTYPE_ROOT, load_config
from pr_decomposer.models import available_models
from pr_decomposer.report_export import build_html, build_markdown, build_pdf
from pr_decomposer.repo_context import compose_requirements, fetch_repo_requirements
from pr_decomposer.store import (
    ReportNotFoundError,
    delete_report,
    list_reports,
    load_report,
    make_report_id,
    save_report,
)

app = FastAPI(title="PR Decomposer API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200", "http://127.0.0.1:4200"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

CONFIG = load_config(PROTOTYPE_ROOT / ".env")


class AnalyzeRequest(BaseModel):
    owner: str
    repo: str
    pr_number: int
    mock: bool = False
    model: str | None = None
    effort: str = "deep"
    requirements: str = ""


class AnalyzeResponse(BaseModel):
    report_id: str
    analyzed_at_iso: str
    report: dict


@app.get("/api/health")
def health() -> dict:
    return {
        "status": "ok",
        "model": CONFIG.model,
        "default_model": CONFIG.model,
        "models": available_models(CONFIG),
        "has_api_key": CONFIG.has_api_key,
        "github_configured": bool(CONFIG.github_token),
        "reports": len(list_reports()),
    }


@app.get("/api/models")
def models() -> list[dict]:
    return available_models(CONFIG)


@app.post("/api/analyze", response_model=AnalyzeResponse)
def analyze(req: AnalyzeRequest) -> AnalyzeResponse:
    # Real LLM by default. Mock is an explicit dev/test opt-in only — never a
    # silent fallback, so a missing key surfaces as a clear configuration error.
    analyzer_uses_mock = req.mock
    try:
        diff_source = GithubApiDiffSource(
            token=CONFIG.github_token, owner=req.owner, repo=req.repo,
            pr_number=req.pr_number,
        )
        diff = diff_source.fetch()
    except Exception as exc:
        detail = str(exc)
        if not CONFIG.github_token:
            detail = ("no GITHUB_TOKEN configured in .env — "
                      "the dashboard analyzes GitHub PRs through the API.")
        raise HTTPException(status_code=400, detail=detail)

    requirements = ""
    if not analyzer_uses_mock and CONFIG.github_token:
        repo_block = fetch_repo_requirements(req.owner, req.repo, CONFIG.github_token)
        requirements = compose_requirements(repo_block=repo_block, manual=req.requirements)

    try:
        report = run_pipeline(
            diff, config=CONFIG, mock=analyzer_uses_mock,
            model=req.model, effort=req.effort, requirements=requirements,
        )
    except ConfigError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"LLM analysis failed: {exc}")

    payload = report.to_dict()
    payload["report_id"] = make_report_id(req.owner, req.repo, req.pr_number)
    payload["repo"] = f"{req.owner}/{req.repo}"
    payload["pr_number"] = req.pr_number
    payload["analyzed_at_iso"] = datetime.now(timezone.utc).isoformat()
    payload["requested_mock"] = analyzer_uses_mock
    payload["effort"] = report.effort

    report_id = save_report(payload, payload["report_id"])
    return AnalyzeResponse(
        report_id=report_id,
        analyzed_at_iso=payload["analyzed_at_iso"],
        report=payload,
    )


@app.get("/api/reports")
def reports() -> list[dict]:
    return list_reports()


@app.get("/api/reports/{report_id}")
def report(report_id: str) -> dict:
    try:
        return load_report(report_id)
    except ReportNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"report '{exc}' not found")


@app.get("/api/reports/{report_id}/export")
def export_report(report_id: str, format: str = "html") -> Response:
    """Download a stored report as standalone HTML, Markdown, or a PDF."""
    export_format = (format or "html").lower()
    if export_format == "markdown":
        export_format = "md"
    if export_format not in ("html", "md", "pdf"):
        raise HTTPException(
            status_code=400,
            detail="format must be 'html', 'md', or 'pdf'",
        )
    try:
        payload = load_report(report_id)
    except ReportNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"report '{exc}' not found")

    filename = f"{report_id}.{export_format}"
    export_formats = {
        "html": ("text/html; charset=utf-8", build_html(payload).encode("utf-8")),
        "md": ("text/markdown; charset=utf-8", build_markdown(payload).encode("utf-8")),
        "pdf": ("application/pdf", _build_pdf_bytes(payload)),
    }
    media_type, body = export_formats[export_format]
    return Response(
        content=body,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _build_pdf_bytes(payload: dict) -> bytes:
    try:
        return bytes(build_pdf(payload))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {exc}")


@app.delete("/api/reports/{report_id}")
def remove(report_id: str) -> dict:
    if not (PROTOTYPE_ROOT / "data" / "reports" / f"{report_id}.json").exists():
        raise HTTPException(status_code=404, detail=f"report '{report_id}' not found")
    delete_report(report_id)
    return {"deleted": report_id}