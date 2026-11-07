"""Local verification of Supabase access tokens (iss, aud, exp, role, sub).

The algorithm is NEVER taken blindly from the token. The unverified header is
read only to choose the key family, and the choice is checked against a fixed
allow-list for the configured JWT_MODE:

  hs256 -> HS256 only, key = SUPABASE_JWT_SECRET (legacy shared secret)
  jwks  -> ES256 / RS256 only, key = public key from the project JWKS
  auto  -> HS256 (secret) or ES256/RS256 (JWKS), chosen by header alg

"none", HS384/HS512, PS*, ES384... are always rejected. A symmetric secret is
never used to verify an asymmetric alg and vice versa (algorithm confusion).
Tokens, secrets and passwords are never logged: only the reason code, alg, kid.
"""
import logging
from dataclasses import dataclass
from functools import lru_cache

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient

from app.core.config import Settings, get_settings
from app.core.errors import ApiError

log = logging.getLogger("kitchen.auth")
_bearer = HTTPBearer(auto_error=False)

SYMMETRIC = {"HS256"}
ASYMMETRIC = {"ES256", "RS256"}
ALLOWED_BY_MODE = {
    "hs256": SYMMETRIC,
    "jwks": ASYMMETRIC,
    "auto": SYMMETRIC | ASYMMETRIC,
}


@dataclass(frozen=True)
class AuthUser:
    user_id: str  # JWT "sub"
    email: str | None


@lru_cache
def _jwks(url: str) -> PyJWKClient:
    return PyJWKClient(url, cache_keys=True, lifespan=600)


def _reject(status: int, code: str, message: str, **ctx) -> ApiError:
    log.warning("auth rejected: %s %s", code, ctx)  # ctx never contains token/secret
    return ApiError(status, code, message)


def verify_token(token: str, s: Settings) -> AuthUser:
    issuer = f"{s.supabase_url.rstrip('/')}/auth/v1"
    try:
        header = jwt.get_unverified_header(token)
    except jwt.PyJWTError:
        raise _reject(401, "INVALID_TOKEN", "Invalid or expired token", reason="malformed")
    alg, kid = header.get("alg"), header.get("kid")

    if alg not in ALLOWED_BY_MODE[s.jwt_mode]:
        raise _reject(
            401, "ALGORITHM_NOT_ALLOWED", "Token algorithm is not allowed",
            alg=alg, kid=kid, mode=s.jwt_mode,
        )

    try:
        if alg in SYMMETRIC:
            if not s.supabase_jwt_secret:
                raise _reject(500, "AUTH_NOT_CONFIGURED", "JWT secret is not configured")
            key = s.supabase_jwt_secret
        else:
            if not kid:
                raise _reject(401, "INVALID_TOKEN", "Invalid or expired token", reason="no_kid")
            key = _jwks(f"{issuer}/.well-known/jwks.json").get_signing_key_from_jwt(token).key
        claims = jwt.decode(
            token, key, algorithms=[alg], audience="authenticated", issuer=issuer,
            options={"require": ["exp", "iss", "aud", "sub"]},
        )
    except ApiError:
        raise
    except jwt.PyJWTError as e:
        raise _reject(401, "INVALID_TOKEN", "Invalid or expired token",
                      reason=type(e).__name__, alg=alg, kid=kid)

    if claims.get("role") != "authenticated":
        raise _reject(403, "INVALID_ROLE", "Token role is not allowed", alg=alg)
    return AuthUser(user_id=str(claims["sub"]), email=claims.get("email"))


def current_user(
    cred: HTTPAuthorizationCredentials | None = Depends(_bearer),
    s: Settings = Depends(get_settings),
) -> AuthUser:
    if cred is None:
        raise ApiError(401, "MISSING_TOKEN", "Authorization header required")
    return verify_token(cred.credentials, s)
