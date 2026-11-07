import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec

from app.core import auth
from app.core.auth import verify_token
from app.core.config import Settings
from app.core.errors import ApiError

SECRET = "x" * 40
URL = "https://abc.supabase.co"
ISS = f"{URL}/auth/v1"
EC_KEY = ec.generate_private_key(ec.SECP256R1())
OTHER_EC = ec.generate_private_key(ec.SECP256R1())


def S(mode="auto"):
    return Settings(supabase_url=URL, jwt_mode=mode, supabase_jwt_secret=SECRET)


def claims(**o):
    c = {"sub": "u1", "aud": "authenticated", "role": "authenticated", "iss": ISS,
         "exp": int(time.time()) + 600, "email": "a@b.c"}
    c.update(o)
    return c


def hs(**o):
    return jwt.encode(claims(**o), SECRET, algorithm="HS256")


def es(key=EC_KEY, **o):
    return jwt.encode(claims(**o), key, algorithm="ES256", headers={"kid": "k1"})


@pytest.fixture(autouse=True)
def fake_jwks(monkeypatch):
    class Key:  # stands in for PyJWK
        key = EC_KEY.public_key()

    class Client:
        def get_signing_key_from_jwt(self, token):
            return Key()

    monkeypatch.setattr(auth, "_jwks", lambda url: Client())


def status(token, mode):
    with pytest.raises(ApiError) as e:
        verify_token(token, S(mode))
    return e.value.status_code, e.value.detail["code"]


# --- valid ---
@pytest.mark.parametrize("mode", ["auto", "hs256"])
def test_valid_hs256(mode):
    assert verify_token(hs(), S(mode)).user_id == "u1"


@pytest.mark.parametrize("mode", ["auto", "jwks"])
def test_valid_es256(mode):
    assert verify_token(es(), S(mode)).email == "a@b.c"


# --- the reported bug: ES256 token against hs256-only config ---
def test_es256_token_rejected_in_hs256_mode_with_clear_code():
    assert status(es(), "hs256") == (401, "ALGORITHM_NOT_ALLOWED")


def test_hs256_token_rejected_in_jwks_mode():
    assert status(hs(), "jwks") == (401, "ALGORITHM_NOT_ALLOWED")


# --- invalid ---
@pytest.mark.parametrize("o", [{"exp": 1}, {"aud": "x"}, {"iss": "https://evil/auth/v1"}])
def test_bad_claims(o):
    assert status(hs(**o), "auto")[0] == 401
    assert status(es(**o), "auto")[0] == 401


def test_wrong_role():
    assert status(hs(role="anon"), "auto")[0] == 403


def test_missing_sub():
    c = claims(); del c["sub"]
    assert status(jwt.encode(c, SECRET, algorithm="HS256"), "auto")[0] == 401


def test_wrong_hs_secret():
    t = jwt.encode(claims(), "y" * 40, algorithm="HS256")
    assert status(t, "auto")[0] == 401


def test_es256_signed_by_other_key():
    assert status(es(key=OTHER_EC), "auto")[0] == 401


def test_alg_none_rejected():
    t = jwt.encode(claims(), None, algorithm="none")
    assert status(t, "auto") == (401, "ALGORITHM_NOT_ALLOWED")


@pytest.mark.parametrize("alg", ["HS384", "HS512"])
def test_other_hs_rejected(alg):
    t = jwt.encode(claims(), SECRET, algorithm=alg)
    assert status(t, "auto") == (401, "ALGORITHM_NOT_ALLOWED")


def test_garbage():
    assert status("not.a.jwt", "auto")[0] == 401


def test_es256_without_kid_rejected():
    t = jwt.encode(claims(), EC_KEY, algorithm="ES256")
    assert status(t, "auto")[0] == 401


def test_no_secret_logged(caplog):
    with caplog.at_level("WARNING"):
        status(es(), "hs256")
        status(hs(exp=1), "auto")
    assert SECRET not in caplog.text
