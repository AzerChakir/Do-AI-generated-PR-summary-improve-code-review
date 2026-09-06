"""FastAPI webhook handler for the PR decomposer GitHub App.

Phase 2 skeleton: verifies the GitHub webhook signature, reacts to
`pull_request` events (`opened` / `reopened` / `synchronize`), runs the
decomposition pipeline, and posts (or idempotently updates) a PR comment.

Inert by default: without `GITHUB_APP_ENABLED=1` and the GitHub secrets, the
endpoint logs events and returns without calling GitHub, so running the server
is a safe way to inspect payloads during development.

Run:
    uvicorn github_app.app:app --reload --port 8000
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging

from fastapi import FastAPI, Request, Response, status

from pr_decomposer import run_pipeline
from pr_decomposer.config import PROTOTYPE_ROOT, load_config
from github_client import (
    GithubApiDiffSource,
    GithubApiError,
    find_bot_comment,
    post_pr_comment,
    prepare_comment_body,
    update_pr_comment,
)

log = logging.getLogger("pr-decomposer")
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="PR Decomposer")


def _verify_signature(payload: bytes, signature_header: str, secret: str) -> bool:
    if not signature_header or not secret:
        return False
    digest = "sha256=" + hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(digest, signature_header)


def _read_event(request: Request) -> dict:
    try:
        return json.loads(request.body())
    except json.JSONDecodeError:
        return {}


def _handle_pull_request(payload: dict, config) -> dict:
    action = payload.get("action")
    if action not in ("opened", "reopened", "synchronize"):
        return {"handled": False, "reason": f"action '{action}' ignored"}

    pr = payload.get("pull_request") or {}
    repo = payload.get("repository") or {}
    number = pr.get("number")
    owner = (repo.get("owner") or {}).get("login") or repo.get("full_name", "").split("/")[0]
    name = repo.get("name") or repo.get("full_name", "").split("/")[1]
    if not number or not owner or not name:
        return {"handled": False, "reason": "missing pull_request/repository metadata"}

    diff_source = GithubApiDiffSource(config.github_token, owner, name, number)
    diff = diff_source.fetch()
    report = run_pipeline(diff, config=config)
    body = prepare_comment_body(report)

    existing = find_bot_comment(config.github_token, owner, name, number,
                                config.github_bot_username)
    if existing:
        update_pr_comment(config.github_token, owner, name, existing, body)
        route = "updated"
    else:
        post_pr_comment(config.github_token, owner, name, number, body)
        route = "posted"
    return {"handled": True, "route": route, "pr": number}


@app.post("/webhook")
async def webhook(request: Request) -> Response:
    config = load_config(PROTOTYPE_ROOT / ".env")
    payload = await request.body()
    event = request.headers.get("X-GitHub-Event", "")
    signature = request.headers.get("X-Hub-Signature-256", "")

    if not config.github_app_enabled:
        log.info("github app disabled (GITHUB_APP_ENABLED=0); event=%s ignored", event)
        return Response(status_code=200, content="{}")

    if not _verify_signature(payload, signature, config.github_webhook_secret):
        return Response(status_code=status.HTTP_401_UNAUTHORIZED,
                        content="invalid signature")

    data = json.loads(payload or b"{}")
    if event == "ping":
        return Response(status_code=200, content='{"ping": "pong"}')

    if event == "pull_request" and config.github_token:
        try:
            result = _handle_pull_request(data, config)
        except (GithubApiError, Exception) as exc:
            log.exception("failed to process pull_request event")
            return Response(status_code=500,
                            content=json.dumps({"error": str(exc)}, default=str))
        return Response(status_code=200, content=json.dumps(result, default=str))

    return Response(status_code=200, content='{"handled": false}')


@app.get("/health")
async def health() -> dict:
    config = load_config(PROTOTYPE_ROOT / ".env")
    return {"status": "ok", "github_app_enabled": config.github_app_enabled,
            "model": config.model,
            "has_api_key": bool(config.has_api_key)}