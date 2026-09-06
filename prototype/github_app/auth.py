"""Auth-provider seam for GitHub access.

Phase 2 ships `AppAuth`/token-based access; Phase 3 (production) will add
`UserOAuth` for GitHub/Google "connect your account" flows. Every provider
exposes `get_token()` so a `GithubApiDiffSource` can be built regardless of who
is authenticated. Keeping this isolated is what lets the analysis core stay
auth-agnostic forever.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class AuthProvider(ABC):
    name: str = "base"

    @abstractmethod
    def get_token(self) -> str:
        """Return a usable GitHub access token or raise NotConfigured."""

    def describe(self) -> str:
        return f"{self.name}: {self.get_token()[:12]}..." if self.get_token() else self.name


class NotConfigured(RuntimeError):
    pass


class TokenAuth(AuthProvider):
    """Phase 2 — a static token from `.env` (user PAT or an App token)."""

    name = "token"

    def __init__(self, token: str):
        self._token = token

    def get_token(self) -> str:
        if not self._token:
            raise NotConfigured("no GITHUB_TOKEN set in .env")
        return self._token


class UserOAuth(AuthProvider):
    """Phase 3 — placeholder for a user's own GitHub/Google-connected token.

    When the multi-tenant platform ships, this provider will exchange the
    platform session for a scoped token per user (e.g. via GitHub Device Flow
    or Google Identity + GitHub API), keeping `GithubApiDiffSource` untouched.
    """

    name = "user-oauth"

    def __init__(self, session_token: str = ""):
        self._session = session_token

    def get_token(self) -> str:
        raise NotConfigured(
            "User OAuth is not wired yet (Phase 3). Authenticate with a "
            "GITHUB_TOKEN in .env for now."
        )


class AppAuth(AuthProvider):
    """Phase 2 — GitHub App installation tokens (SSE/per-org installs).

    Placeholder: production wiring will install the private key from
    `GITHUB_PRIVATE_KEY_PATH`, request a JWT, and exchange it for an
    installation access token. Kept here so the seam is visible from day one.
    """

    name = "github-app"

    def __init__(self, app_id: str = "", private_key_path: str = ""):
        self._app_id = app_id
        self._key_path = private_key_path

    def get_token(self) -> str:
        raise NotConfigured(
            "GitHub App token exchange is not wired yet. Set GITHUB_TOKEN in "
            ".env (Phase 2 token mode) or wait for Phase 3 OAuth."
        )


def resolve_auth_provider(config) -> AuthProvider:
    """Pick the best configured provider for the current runtime."""
    if config.github_token:
        return TokenAuth(config.github_token)
    if config.github_app_enabled:
        return AppAuth(config.github_app_id, config.github_private_key_path)
    return TokenAuth("")