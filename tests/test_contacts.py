import sys
from pathlib import Path

# Добавляем папку server в путь (нужно для импорта через monkeypatch)
sys.path.insert(0, str(Path(__file__).parent.parent / "server"))

import pytest
from conftest import generate_ed25519_keypair, make_signed_request


def test_send_swap_request(client, user_alice):
    # Создадим пользователя bob
    pub_bob, priv_bob = generate_ed25519_keypair()
    client.post("/auth/register", json={"login": "bob", "public_key": pub_bob})

    login_alice = user_alice["login"]
    priv_alice = user_alice["private_key"]
    request_id = "req_001"
    resp = make_signed_request(
        client, "POST", "/contacts/request",
        login=login_alice, private_key_pem=priv_alice,
        body={
            "target_id": "bob",
            "type": "swap",
            "request_id": request_id
        }
    )
    assert resp.status_code == 202
    assert resp.json() == {"status": "request sent"}

    # Проверим, что у bob появился запрос
    resp2 = make_signed_request(client, "GET", "/contacts/requests",
                                login="bob", private_key_pem=priv_bob)
    assert resp2.status_code == 200
    requests = resp2.json()
    assert len(requests) == 1
    assert requests[0]["request_id"] == request_id
    assert requests[0]["type"] == "swap"
    assert requests[0]["from_id"] == "alice"


def test_send_duplicate_swap_request(client, user_alice):
    pub_bob, priv_bob = generate_ed25519_keypair()
    client.post("/auth/register", json={"login": "bob", "public_key": pub_bob})
    login_alice = user_alice["login"]
    priv_alice = user_alice["private_key"]
    request_id = "req_002"
    # Первый запрос
    make_signed_request(client, "POST", "/contacts/request", login_alice, priv_alice,
                        body={"target_id": "bob", "type": "swap", "request_id": request_id})
    # Второй такой же (swap от того же отправителя)
    resp2 = make_signed_request(client, "POST", "/contacts/request", login_alice, priv_alice,
                                body={"target_id": "bob", "type": "swap", "request_id": "another_id"})
    assert resp2.status_code == 400
    assert "already exists" in resp2.text


def test_delete_request(client, user_alice):
    pub_bob, priv_bob = generate_ed25519_keypair()
    client.post("/auth/register", json={"login": "bob", "public_key": pub_bob})
    login_alice = user_alice["login"]
    priv_alice = user_alice["private_key"]
    req_id = "req_del"
    make_signed_request(client, "POST", "/contacts/request", login_alice, priv_alice,
                        body={"target_id": "bob", "type": "swap", "request_id": req_id})
    # Удаляем запрос от лица bob
    resp_del = make_signed_request(client, "DELETE", f"/contacts/requests/{req_id}",
                                   login="bob", private_key_pem=priv_bob)
    assert resp_del.status_code == 204
    # Проверяем, что запросов больше нет
    resp_get = make_signed_request(client, "GET", "/contacts/requests",
                                   login="bob", private_key_pem=priv_bob)
    assert resp_get.json() == []


@pytest.mark.skip(reason="Requires modification of global state; can be fixed by reloading module or using monkeypatch")
def test_request_queue_size_limit(client, user_alice):
    pass