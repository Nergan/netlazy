import pytest
pytestmark = pytest.mark.anyio
import pytest
from conftest import generate_ed25519_keypair, make_signed_request


def test_register_success(client):
    pub, _ = generate_ed25519_keypair()
    resp = client.post("/auth/register", json={
        "login": "bob",
        "public_key": pub,
        "key_algorithm": "Ed25519"
    })
    print("Status:", resp.status_code)
    print("Response:", resp.text)
    assert resp.status_code == 200
    assert resp.json() == {"status": "registered", "login": "bob"}


def test_register_duplicate_login(client, user_alice):
    pub, _ = generate_ed25519_keypair()
    resp = client.post("/auth/register", json={
        "login": "alice",
        "public_key": pub,
        "key_algorithm": "Ed25519"
    })
    print("Status:", resp.status_code)
    print("Response:", resp.text)
    assert resp.status_code == 400
    assert "already exists" in resp.text


def test_register_invalid_public_key(client):
    resp = client.post("/auth/register", json={
        "login": "badkey",
        "public_key": "not a valid key",
        "key_algorithm": "Ed25519"
    })
    print("Status:", resp.status_code)
    print("Response:", resp.text)
    assert resp.status_code == 400
    assert "Invalid public key" in resp.text


def test_change_key_success(client, user_alice):
    login = user_alice["login"]
    old_priv = user_alice["private_key"]
    new_pub, new_priv = generate_ed25519_keypair()  # new_priv не используется, но сгенерируем

    # Смена ключа должна быть подписана старым ключом
    resp = make_signed_request(
        client, "POST", "/auth/change-key",
        login=login, private_key_pem=old_priv,
        body={"new_public_key": new_pub, "new_algorithm": "Ed25519"}
    )
    print("Status:", resp.status_code)
    print("Response:", resp.text)
    assert resp.status_code == 200
    assert resp.json() == {"status": "key changed"}

    # Проверяем, что старый ключ больше не работает
    # Попробуем запрос к /users/me с новым ключом (но старым логином) – должно пройти
    # А со старым ключом – не пройдёт. Но сначала нужно обновить ключ в БД.
    # Убедимся, что новый ключ сохранён. Для этого запросим защищённый ресурс с новым ключом.
    # Сгенерируем приватный ключ, соответствующий новому публичному (new_priv).
    # Для проверки: делаем GET /users/me с подписью от нового ключа.
    resp2 = make_signed_request(
        client, "GET", "/users/me",
        login=login, private_key_pem=new_priv,
        body=None
    )
    print("Status:", resp.status_code)
    print("Response:", resp.text)
    assert resp2.status_code == 200
    # Старый ключ уже не должен работать
    resp3 = make_signed_request(
        client, "GET", "/users/me",
        login=login, private_key_pem=old_priv,
        body=None
    )
    print("Status:", resp.status_code)
    print("Response:", resp.text)
    assert resp3.status_code == 401  # Invalid signature


def test_change_key_requires_auth(client, user_alice):
    # Отсутствие заголовков
    resp = client.post("/auth/change-key", json={"new_public_key": "some", "new_algorithm": "Ed25519"})
    print("Status:", resp.status_code)
    print("Response:", resp.text)
    assert resp.status_code == 401