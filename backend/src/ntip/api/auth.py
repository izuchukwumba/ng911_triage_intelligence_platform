"""Authentication and role-based access for the /v1 API (design v1.2, sections 2.3 and 13.2).

Bearer tokens map to a principal and a role. Each route declares the
permission it needs. Authentication can only be switched off explicitly
(NTIP_AUTH_DISABLED=1, for an isolated local demo); a server with neither
tokens nor that flag refuses to start (see ``Settings.from_env``).

The authenticated principal, not the request body, identifies who reviewed
an incident or requested a replay, so audit entries cannot be attributed to
someone else.
"""

import hmac
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import Annotated

from fastapi import Header, Request
from fastapi.exceptions import RequestValidationError


class Role(StrEnum):
    VIEWER = "viewer"  # read incidents, assessments, audit, replays
    OPERATOR = "operator"  # + submit messages and record reviews
    ANALYST = "analyst"  # + run replays
    ADMIN = "admin"  # everything


class Permission(StrEnum):
    READ = "read"
    INGEST = "ingest"
    REVIEW = "review"
    REPLAY = "replay"


ROLE_PERMISSIONS: dict[Role, frozenset[Permission]] = {
    Role.VIEWER: frozenset({Permission.READ}),
    Role.OPERATOR: frozenset({Permission.READ, Permission.INGEST, Permission.REVIEW}),
    Role.ANALYST: frozenset({Permission.READ, Permission.REPLAY}),
    Role.ADMIN: frozenset(Permission),
}


@dataclass(frozen=True)
class Principal:
    principal_id: str
    role: Role
    authenticated: bool = True

    def can(self, permission: Permission) -> bool:
        return permission in ROLE_PERMISSIONS[self.role]


# Used only when authentication is explicitly disabled.
LOCAL_DEMO = Principal("local-demo", Role.ADMIN, authenticated=False)


class Unauthenticated(Exception):
    pass


class Forbidden(Exception):
    def __init__(self, permission: Permission) -> None:
        super().__init__(permission)
        self.permission = permission


def authenticate(request: Request, authorization: str | None) -> Principal:
    if request.app.state.auth_disabled:
        return LOCAL_DEMO
    tokens: dict[str, Principal] = request.app.state.api_tokens
    presented = (authorization or "").removeprefix("Bearer ").strip()
    for token, principal in tokens.items():
        # Constant-time comparison for every configured token.
        if presented and hmac.compare_digest(presented.encode(), token.encode()):
            return principal
    raise Unauthenticated


def require(permission: Permission) -> Callable[..., Principal]:
    """A route dependency that authenticates and checks one permission."""

    def dependency(
        request: Request, authorization: Annotated[str | None, Header()] = None
    ) -> Principal:
        principal = authenticate(request, authorization)
        if not principal.can(permission):
            raise Forbidden(permission)
        request.state.principal = principal
        return principal

    return dependency


def acting_as(principal: Principal, claimed: str | None, field: str) -> str:
    """Who acted: the token's principal, or (auth disabled) the name stated in the body."""
    if principal.authenticated:
        return principal.principal_id
    if claimed is None:
        raise RequestValidationError(
            [
                {
                    "loc": ("body", field),
                    "msg": "required when authentication is disabled",
                    "type": "missing",
                }
            ]
        )
    return claimed
