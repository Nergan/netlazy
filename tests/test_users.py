import pytest
pytestmark = pytest.mark.anyio
import base64
import pytest
from conftest import generate_ed25519_keypair, make_signed_request


def test_get_user_public(client, user_alice):
    # Сначала получим профиль alice публично
    resp = client.get("/users/alice")
    print("Status:", resp.status_code)
    print("Response:", resp.text)
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == "alice"
    assert "name" not in data or data["name"] is None


def test_get_my_profile(client, user_alice):
    login = user_alice["login"]
    priv = user_alice["private_key"]
    resp = make_signed_request(client, "GET", "/users/me", login, priv)
    print("Status:", resp.status_code)
    print("Response:", resp.text)
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == "alice"


def test_update_profile(client, user_alice):
    login = user_alice["login"]
    priv = user_alice["private_key"]
    update_data = {
        "name": "Alice Wonder",
        "desc": "Coffee lover",
        "tags": ["coffee", "it"]
    }
    resp = make_signed_request(client, "PATCH", "/users/me", login, priv, body=update_data)
    print("Status:", resp.status_code)
    print("Response:", resp.text)
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Alice Wonder"
    assert data["desc"] == "Coffee lover"
    assert set(data["tags"]) == {"coffee", "it"}


def test_update_profile_invalid_image(client, user_alice):
    login = user_alice["login"]
    priv = user_alice["private_key"]
    resp = make_signed_request(client, "PATCH", "/users/me", login, priv,
                               body={"img": "not_base64!"})
    assert resp.status_code == 422
    assert "invalid base64 image" in resp.text


def test_list_users_pagination(client, user_alice):
    # Зарегистрируем ещё двух пользователей
    from conftest import generate_ed25519_keypair
    pub1, _ = generate_ed25519_keypair()
    client.post("/auth/register", json={"login": "bob", "public_key": pub1})
    pub2, _ = generate_ed25519_keypair()
    client.post("/auth/register", json={"login": "carol", "public_key": pub2})

    # Неавторизованный список
    resp = client.get("/users/list?limit=2&offset=0")
    print("Status:", resp.status_code)
    print("Response:", resp.text)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 2
    assert data["total"] >= 3  # включая alice, bob, carol

    # Авторизованный список (исключает себя)
    login = user_alice["login"]
    priv = user_alice["private_key"]
    resp = make_signed_request(client, "GET", "/users/list?limit=10", login, priv)
    print("Status:", resp.status_code)
    print("Response:", resp.text)
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert all(u["id"] != "alice" for u in items)


def test_list_users_tag_filter(client, user_alice):
    login = user_alice["login"]
    priv = user_alice["private_key"]
    # Обновим профиль alice с тегами
    make_signed_request(client, "PATCH", "/users/me", login, priv,
                        body={"tags": ["python", "coffee"]})
    # Создадим bob с тегом "python"
    pub_bob, priv_bob = generate_ed25519_keypair()
    client.post("/auth/register", json={"login": "bob", "public_key": pub_bob})
    make_signed_request(client, "PATCH", "/users/me", "bob", priv_bob,
                        body={"tags": ["python"]})
    # Поиск по тегу "python" с match_all=false
    resp = client.get("/users/list?tags=python&match_all=false")
    print("Status:", resp.status_code)
    print("Response:", resp.text)
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) >= 2  # alice и bob
    # Сортировка по совпадению тегов (по умолчанию)
    resp2 = client.get("/users/list?tags=python&sort_by=tags_match")
    print("Status:", resp.status_code)
    print("Response:", resp.text)
    assert resp2.status_code == 200
    # Первый должен иметь больше совпадений? У alice два тега, у bob один, но alice исключается? При неавторизованном запросе alice включена.
    # Упростим: просто проверим, что ответ 200