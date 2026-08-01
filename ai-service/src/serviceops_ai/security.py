from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Annotated, Any

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import InvalidTokenError

JWT_SECRET = os.getenv(
    "SERVICEOPS_AUTH_JWT_SECRET",
    "local-development-signing-key-change-me-2026",
)
JWT_ISSUER = os.getenv("SERVICEOPS_AUTH_ISSUER", "serviceops-local")
JWT_AUDIENCE = os.getenv("SERVICEOPS_AUTH_AUDIENCE", "serviceops-api")
SUPPORTED_ROLES = frozenset({"VIEWER", "OPERATOR"})

if len(JWT_SECRET.encode("utf-8")) < 32:
    raise RuntimeError("SERVICEOPS_AUTH_JWT_SECRET must contain at least 32 UTF-8 bytes")

bearer = HTTPBearer(auto_error=False)
BearerCredentials = Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]


@dataclass(frozen=True)
class AuthenticatedUser:
    username: str
    roles: frozenset[str]


def authenticated_user(credentials: BearerCredentials) -> AuthenticatedUser:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise _unauthorized()
    try:
        claims: dict[str, Any] = jwt.decode(
            credentials.credentials,
            JWT_SECRET,
            algorithms=["HS256"],
            audience=JWT_AUDIENCE,
            issuer=JWT_ISSUER,
            options={"require": ["exp", "iat", "iss", "aud", "sub", "roles"]},
        )
    except InvalidTokenError as exception:
        raise _unauthorized() from exception

    username = claims.get("sub")
    raw_roles = claims.get("roles")
    if not isinstance(username, str) or not username.strip():
        raise _unauthorized()
    if not isinstance(raw_roles, list) or not all(isinstance(role, str) for role in raw_roles):
        raise _unauthorized()
    roles = frozenset(raw_roles) & SUPPORTED_ROLES
    if not roles:
        raise _unauthorized()
    return AuthenticatedUser(username=username, roles=roles)


def viewer_or_operator(
    user: Annotated[AuthenticatedUser, Depends(authenticated_user)],
) -> AuthenticatedUser:
    return user


def operator(user: Annotated[AuthenticatedUser, Depends(authenticated_user)]) -> AuthenticatedUser:
    if "OPERATOR" not in user.roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The authenticated role cannot perform this operation",
        )
    return user


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="A valid bearer token is required",
        headers={"WWW-Authenticate": "Bearer"},
    )
