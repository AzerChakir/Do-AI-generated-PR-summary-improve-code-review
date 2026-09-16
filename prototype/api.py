"""Dashboard REST API for the PR decomposer.

Serves the Angular dashboard: triggers analysis of a GitHub PR, stores the
report, lists past reports, and returns full reports. CORS is enabled for the
Angular dev server (http://localhost:4200).

Run:
    uvicorn api:app --reload --port 8000
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, Response
from pydantic import BaseModel

from github_client import (
    GithubApiDiffSource,
    GithubApiError,
    list_open_prs,
    post_comment_from_payload,
    pr_states,
)
from github_oauth import (
    OAuthError,
    OAuthNotConfigured,
    SESSION_COOKIE,
    SESSION_MAX_AGE,
    build_authorize_url,
    connected_user_by_cookie,
    connected_users,
    create_session,
    delete_github_user,
    destroy_session,
    exchange_code,
    fetch_user,
    resolve_token,
    save_github_user,
    verify_state,
)
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
    report_owner,
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
    post_comment: bool = False


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
def analyze(req: AnalyzeRequest, request: Request) -> AnalyzeResponse:
    # Real LLM by default. Mock is an explicit dev/test opt-in only — never a
    # silent fallback, so a missing key surfaces as a clear configuration error.
    analyzer_uses_mock = req.mock
    auth_user = connected_user_by_cookie(request.cookies.get(SESSION_COOKIE))
    try:
        token = resolve_token(auth_user)
    except OAuthError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    try:
        diff_source = GithubApiDiffSource(
            token=token, owner=req.owner, repo=req.repo,
            pr_number=req.pr_number,
        )
        diff = diff_source.fetch()
    except Exception as exc:
        detail = str(exc)
        if "GITHUB_TOKEN is required" in detail or not token:
            detail = ("no GitHub access — connect your GitHub account in the "
                      "dashboard, or set GITHUB_TOKEN in .env.")
        raise HTTPException(status_code=400, detail=detail)

    requirements = ""
    if not analyzer_uses_mock:
        try:
            repo_block = fetch_repo_requirements(req.owner, req.repo, token)
            requirements = compose_requirements(
                repo_block=repo_block, manual=req.requirements,
            )
        except Exception:
            requirements = req.requirements

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
    owner_login = auth_user.get("login", "") if auth_user else ""
    report_id = make_report_id(req.owner, req.repo, req.pr_number)
    if owner_login:
        report_id = f"{owner_login}-{report_id}"
    payload["report_id"] = report_id
    payload["owner"] = owner_login
    payload["repo"] = f"{req.owner}/{req.repo}"
    payload["pr_number"] = req.pr_number
    payload["analyzed_at_iso"] = datetime.now(timezone.utc).isoformat()
    payload["requested_mock"] = analyzer_uses_mock
    payload["effort"] = report.effort

    report_id = save_report(payload, report_id)

    comment_posted = False
    if req.post_comment and not analyzer_uses_mock:
        try:
            post_comment_from_payload(token, req.owner, req.repo,
                                      req.pr_number, payload)
            comment_posted = True
        except GithubApiError as exc:
            raise HTTPException(
                status_code=502,
                detail=f"analysis saved ({report_id}) but posting the PR "
                       f"comment failed: {exc}",
            )

    return AnalyzeResponse(
        report_id=report_id,
        analyzed_at_iso=payload["analyzed_at_iso"],
        report=payload,
    )


# ── GitHub "Connect your account" (OAuth) ────────────────────────────────────

FRONTEND_URL = "http://localhost:4200"


@app.get("/api/auth/status")
def auth_status(request: Request) -> dict:
    user = connected_user_by_cookie(request.cookies.get(SESSION_COOKIE))
    if user:
        return {
            "connected": True,
            "username": user.get("login", ""),
            "display_name": user.get("name", ""),
            "avatar_url": user.get("avatar_url", ""),
            "oauth_configured": bool(CONFIG.github_client_id and CONFIG.github_client_secret),
        }
    return {
        "connected": False,
        "username": "",
        "display_name": "",
        "avatar_url": "",
        "oauth_configured": bool(CONFIG.github_client_id and CONFIG.github_client_secret),
    }


@app.get("/api/auth/login")
def auth_login() -> RedirectResponse:
    redirect_uri = CONFIG.github_redirect_uri
    try:
        url = build_authorize_url(CONFIG.github_client_id, redirect_uri)
    except OAuthNotConfigured as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return RedirectResponse(url=url)


@app.get("/api/auth/callback")
def auth_callback(code: str = "", state: str = "", error: str = "") -> RedirectResponse:
    if error or not code or not verify_state(state):
        return RedirectResponse(url=f"{FRONTEND_URL}/?gh=error")
    try:
        token = exchange_code(CONFIG.github_client_id, CONFIG.github_client_secret,
                              code, CONFIG.github_redirect_uri)
        user = fetch_user(token)
        save_github_user(user, token)
        session_id = create_session(user["login"])
    except (OAuthError, OAuthNotConfigured) as exc:
        return RedirectResponse(url=f"{FRONTEND_URL}/?gh=error")
    response = RedirectResponse(
        url=f"{FRONTEND_URL}/?gh=connected&user={user['login']}"
    )
    response.set_cookie(
        SESSION_COOKIE, session_id,
        max_age=SESSION_MAX_AGE,
        httponly=True,
        samesite="lax",
        path="/",
    )
    return response


@app.post("/api/auth/logout")
def auth_logout(request: Request, response: Response) -> dict:
    session_id = request.cookies.get(SESSION_COOKIE)
    if session_id:
        destroy_session(session_id)
    response.delete_cookie(SESSION_COOKIE, path="/")
    return {"connected": False}


@app.get("/api/users")
def users() -> dict:
    """Pending/connected GitHub accounts stored on this dashboard instance."""
    return connected_users()


@app.post("/api/auth/disconnect")
def auth_disconnect(request: Request, response: Response) -> dict:
    """Sign out AND drop this GitHub account + token from the dashboard."""
    user = connected_user_by_cookie(request.cookies.get(SESSION_COOKIE))
    if user:
        delete_github_user(user.get("login", ""))
    session_id = request.cookies.get(SESSION_COOKIE)
    if session_id:
        destroy_session(session_id)
    response.delete_cookie(SESSION_COOKIE, path="/")
    return {"connected": False}


@app.get("/api/prs")
def open_prs(request: Request) -> list[dict]:
    auth_user = connected_user_by_cookie(request.cookies.get(SESSION_COOKIE))
    try:
        token = resolve_token(auth_user)
        prs = list_open_prs(token)
    except OAuthError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except GithubApiError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    # Only non-reviewed PRs: drop any that already have a stored report
    # owned by this user.
    owner = auth_user.get("login", "") if auth_user else ""
    reviewed = {
        f"{r.get('repo', '')}#{r.get('pr_number')}"
        for r in list_reports(owner=owner)
        if isinstance(r.get("pr_number"), int) and r.get("repo")
    }
    return [
        pr for pr in prs
        if f"{pr.get('repo_full', '')}#{pr.get('pr_number')}" not in reviewed
    ]


@app.get("/api/reports")
def reports(request: Request) -> list[dict]:
    auth_user = connected_user_by_cookie(request.cookies.get(SESSION_COOKIE))
    if not auth_user:
        return []
    return list_reports(owner=auth_user.get("login", ""))


@app.get("/api/reports/states")
def reports_states(request: Request) -> dict:
    """Live GitHub state (merged?) for the signed-in user's reports."""
    auth_user = connected_user_by_cookie(request.cookies.get(SESSION_COOKIE))
    try:
        token = resolve_token(auth_user)
    except OAuthError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    owner = auth_user.get("login", "") if auth_user else ""
    repo_prs = [
        {"repo": r.get("repo", ""), "pr_number": r.get("pr_number")}
        for r in list_reports(owner=owner)
        if isinstance(r.get("pr_number"), int) and r.get("repo")
    ]
    return pr_states(token, repo_prs)


def _require_owner(request: Request, report_id: str) -> str:
    """Session login must own the report, or the report is not found for them."""
    owner = report_owner(report_id)
    if not owner:
        return ""
    auth_user = connected_user_by_cookie(request.cookies.get(SESSION_COOKIE))
    login = auth_user.get("login", "") if auth_user else ""
    if owner != login:
        raise HTTPException(status_code=404, detail=f"report '{report_id}' not found")
    return login


@app.get("/api/reports/{report_id}")
def report(report_id: str, request: Request) -> dict:
    _require_owner(request, report_id)
    try:
        return load_report(report_id)
    except ReportNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"report '{exc}' not found")


@app.get("/api/reports/{report_id}/export")
def export_report(report_id: str, request: Request, format: str = "html") -> Response:
    """Download a stored report as standalone HTML, Markdown, or a PDF."""
    _require_owner(request, report_id)
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
def remove(report_id: str, request: Request) -> dict:
    _require_owner(request, report_id)
    if not (PROTOTYPE_ROOT / "data" / "reports" / f"{report_id}.json").exists():
        raise HTTPException(status_code=404, detail=f"report '{report_id}' not found")
    delete_report(report_id)
    return {"deleted": report_id}