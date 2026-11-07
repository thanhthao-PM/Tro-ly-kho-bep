import pytest

pytest.importorskip("fastapi")
from app.services.common import request_hash  # noqa: E402


def test_request_hash_is_stable_and_sensitive():
    a = request_hash("POST", "/api/v1/batches", {"b": 1, "a": 2})
    assert a == request_hash("POST", "/api/v1/batches", {"a": 2, "b": 1})      # key order irrelevant
    assert a != request_hash("POST", "/api/v1/batches", {"a": 2, "b": 2})
    assert a != request_hash("POST", "/api/v1/batches/x/disposals", {"a": 2, "b": 1})
