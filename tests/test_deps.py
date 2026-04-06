import pytest
pytestmark = pytest.mark.anyio
import time
import hashlib
import pytest
from conftest import make_signed_request, sign_request


def test_missing_headers(client, user_alice):
    resp = client.get("/users/me")  # нет заголовков
    print("Status:", resp.status_code)
    print("Response:", resp.text)
    assert resp.status_code == 401


def test_expired_timestamp(client, user_alice):
    login = user_alice["login"]
    priv = user_alice["private_key"]
    # Формируем запрос с просроченным timestamp вручную
    from conftest import sign_request
    import json
    body = None
    body_bytes = b''
    timestamp = int(time.time()) - 400  # 400 секунд назад
    nonce = "test_nonce"
    path = "/users/me"
    method = "GET"
    body_hash = hashlib.sha256(body_bytes).hexdigest()
    signature = sign_request(priv, method, path, timestamp, nonce, body_bytes)
    headers = {
        "X-Login": login,
        "X-Timestamp": str(timestamp),
        "X-Nonce": nonce,
        "X-Body-Hash": body_hash,
        "X-Signature": signature,
    }
    resp = client.get(path, headers=headers)
    print("Status:", resp.status_code)
    print("Response:", resp.text)
    assert resp.status_code == 401
    assert "expired" in resp.text


def test_reused_nonce(client, user_alice):
    login = user_alice["login"]
    priv = user_alice["private_key"]
    # Первый запрос с nonce
    resp1 = make_signed_request(client, "GET", "/users/me", login, priv, body=None)
    print("Status:", resp.status_code)
    print("Response:", resp.text)
    assert resp1.status_code == 200
    # Второй с тем же nonce (нужно извлечь nonce из первого запроса? проще сгенерировать тот же)
    # Для теста сгенерируем одинаковый nonce, зафиксировав время.
    import time
    fixed_ts = int(time.time())
    fixed_nonce = "same_nonce"
    body_bytes = b''
    body_hash = hashlib.sha256(body_bytes).hexdigest()
    from conftest import sign_request
    signature = sign_request(priv, "GET", "/users/me", fixed_ts, fixed_nonce, body_bytes)
    headers = {
        "X-Login": login,
        "X-Timestamp": str(fixed_ts),
        "X-Nonce": fixed_nonce,
        "X-Body-Hash": body_hash,
        "X-Signature": signature,
    }
    # Первый раз с этим nonce
    resp2 = client.get("/users/me", headers=headers)
    print("Status:", resp.status_code)
    print("Response:", resp.text)
    assert resp2.status_code == 200
    # Второй раз с тем же nonce (даже timestamp тот же) – должен отклониться
    resp3 = client.get("/users/me", headers=headers)
    print("Status:", resp.status_code)
    print("Response:", resp.text)
    assert resp3.status_code == 409
    assert "Nonce already used" in resp3.text
    
    
def test_reused_nonce(client, user_alice):
    login = user_alice["login"]
    priv = user_alice["private_key"]
    # Первый запрос с обычным nonce
    resp1 = make_signed_request(client, "GET", "/users/me", login, priv, body=None)
    assert resp1.status_code == 200

    # Второй запрос с фиксированным nonce (повторно используем тот же nonce)
    fixed_ts = int(time.time())
    fixed_nonce = "fixed_nonce_123"
    body_bytes = b''
    body_hash = hashlib.sha256(body_bytes).hexdigest()
    signature = sign_request(priv, "GET", "/users/me", fixed_ts, fixed_nonce, body_bytes)
    headers = {
        "X-Login": login,
        "X-Timestamp": str(fixed_ts),
        "X-Nonce": fixed_nonce,
        "X-Body-Hash": body_hash,
        "X-Signature": signature,
    }
    resp2 = client.get("/users/me", headers=headers)
    assert resp2.status_code == 200  # первый раз с этим nonce

    resp3 = client.get("/users/me", headers=headers)
    assert resp3.status_code == 409
    assert "Nonce already used" in resp3.text