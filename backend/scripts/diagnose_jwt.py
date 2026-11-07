"""Diagnose Supabase JWT algorithm. Prints header alg/kid and check results only.
NEVER prints the token, password, secret or key material.

Run from backend/ with the venv active:  python scripts/diagnose_jwt.py you@example.com
Needs VITE_SUPABASE_PUBLISHABLE_KEY (env var or ../frontend/.env.local).
"""
import getpass
import json
import os
import sys
import time
import urllib.error
import urllib.request

import jwt

sys.path.insert(0, os.getcwd())
from app.core.auth import verify_token  # noqa: E402
from app.core.config import get_settings  # noqa: E402
from app.core.errors import ApiError  # noqa: E402


def publishable_key() -> str:
    k = os.environ.get("VITE_SUPABASE_PUBLISHABLE_KEY", "")
    p = os.path.join("..", "frontend", ".env.local")
    if not k and os.path.exists(p):
        for line in open(p, encoding="utf-8"):
            if line.startswith("VITE_SUPABASE_PUBLISHABLE_KEY="):
                k = line.split("=", 1)[1].strip().strip('"')
    return k


def http(url, data=None, headers=None):
    req = urllib.request.Request(url, data=data, headers=headers or {})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())


def main():
    if len(sys.argv) < 2:
        sys.exit("usage: python scripts/diagnose_jwt.py <email>")
    s = get_settings()
    base = s.supabase_url.rstrip("/")
    key = publishable_key()
    print(f"SUPABASE_URL set: {bool(base)} | JWT_MODE: {s.jwt_mode} | secret set: {bool(s.supabase_jwt_secret)} | publishable key set: {bool(key)}")
    pw = getpass.getpass("Password (hidden): ")
    try:
        res = http(f"{base}/auth/v1/token?grant_type=password",
                   json.dumps({"email": sys.argv[1], "password": pw}).encode(),
                   {"apikey": key, "Content-Type": "application/json"})
    except urllib.error.HTTPError as e:
        sys.exit(f"Sign-in failed: HTTP {e.code}")
    token = res["access_token"]
    h = jwt.get_unverified_header(token)
    c = jwt.decode(token, options={"verify_signature": False})
    print(f"TOKEN HEADER: alg={h.get('alg')} kid={h.get('kid')} typ={h.get('typ')}")
    print(f"CLAIMS: iss_matches={c.get('iss') == base + '/auth/v1'} aud={c.get('aud')} role={c.get('role')} expires_in={int(c['exp'] - time.time())}s")
    try:
        jw = http(f"{base}/auth/v1/.well-known/jwks.json")
        print("JWKS:", [(k.get("kid"), k.get("alg"), k.get("kty")) for k in jw.get("keys", [])] or "empty")
    except Exception as e:  # noqa: BLE001
        print("JWKS fetch failed:", type(e).__name__)
    for mode in ("auto", "hs256", "jwks"):
        s2 = s.model_copy(update={"jwt_mode": mode})
        try:
            verify_token(token, s2)
            print(f"verify_token mode={mode}: OK")
        except ApiError as e:
            print(f"verify_token mode={mode}: REJECTED {e.detail['code']}")
        except Exception as e:  # noqa: BLE001
            print(f"verify_token mode={mode}: ERROR {type(e).__name__}")


main()
