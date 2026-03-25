import json
import time
from typing import Optional, List, Dict, Any
from pathlib import Path
import requests

from .auth import AuthManager
from .storage import ProfileStorage
from .utils import sign_request, generate_initial_nonce, compute_next_nonce
from .errors import RequestError, NonceConflictError, ProfileNotFoundError
from .models import (
    UserPublic, UserProfileUpdate, ContactRequestInput, ContactRequestOut, UserListResponse
)

class NetLazyClient:
    KEY_ALGORITHM = "Ed25519"  # константа

    def __init__(self, base_url: str, storage_path: Optional[Path] = None):
        """
        base_url: URL сервера (например, http://localhost:8000)
        storage_path: путь к папке для хранения профилей (по умолчанию ./netlazy)
        """
        self.base_url = base_url.rstrip('/')
        if storage_path is None:
            self.storage_path = Path.cwd() / ".netlazy"
        else:
            self.storage_path = storage_path
        self.storage = ProfileStorage(self.storage_path)
        self.auth = AuthManager(self.storage)
        self._session = requests.Session()
        self._last_sent_nonce: Optional[str] = None  # аннотация типа

    # ----- Управление профилями -----

    def register(self, login: str, private_key: Optional[str] = None, public_key: Optional[str] = None) -> str:
        """
        Регистрирует нового пользователя.
        Если ключи не переданы, генерирует новые.
        Возвращает логин (тот же, что передан).
        """
        if private_key and public_key:
            priv_pem = private_key
            pub_pem = public_key
        else:
            from .utils import generate_keypair
            priv_pem, pub_pem = generate_keypair()

        payload = {
            "login": login,
            "public_key": pub_pem,
            "key_algorithm": self.KEY_ALGORITHM,
        }
        resp = self._request("POST", "/auth/register", json=payload, signed=False)
        if resp.status_code != 200:
            self._check_status(resp)

        initial_nonce = generate_initial_nonce()
        self.storage.save_profile(login, priv_pem, pub_pem, initial_nonce)
        self.auth.set_current_profile(login)
        return login

    def load_profile(self, login: str):
        """
        Загружает существующий профиль для использования.
        Выбрасывает ProfileNotFoundError, если профиль не найден в хранилище.
        """
        if not self.storage.load_profile(login):
            raise ProfileNotFoundError(f"Profile {login} not found in storage")
        self.auth.set_current_profile(login)

    def list_profiles(self) -> List[str]:
        """Возвращает список сохранённых логинов."""
        return self.storage.list_profiles()

    def get_current_login(self) -> Optional[str]:
        """Возвращает логин текущего активного профиля или None."""
        return self.auth.current_login

    # ----- Публичные методы API -----

    def list_users(self, tags: Optional[List[str]] = None, match_all: bool = True,
                   sort_by: Optional[str] = None, sort_order: str = "desc",
                   limit: int = 20, offset: int = 0) -> UserListResponse:
        """
        GET /users/list
        Получить список пользователей с фильтрацией по тегам.
        """
        params = {"match_all": str(match_all).lower(), "limit": limit, "offset": offset}
        if tags:
            params["tags"] = tags
        if sort_by:
            params["sort_by"] = sort_by
        if sort_order:
            params["sort_order"] = sort_order
        resp = self._request("GET", "/users/list", params=params, signed=False)
        self._check_status(resp)
        data = resp.json()
        return UserListResponse(**data)

    def get_user(self, login: str) -> UserPublic:
        """GET /users/{login}  Получить публичный профиль другого пользователя."""
        resp = self._request("GET", f"/users/{login}", signed=False)
        self._check_status(resp)
        return UserPublic(**resp.json())

    def get_my_profile(self) -> UserPublic:
        """GET /users/me  Получить свой профиль (требуется аутентификация)."""
        resp = self._request("GET", "/users/me", signed=True)
        self._check_status(resp)
        return UserPublic(**resp.json())

    def update_my_profile(self, update: UserProfileUpdate) -> UserPublic:
        """
        PATCH /users/me  Обновить свой профиль.
        Передаются только указанные поля.
        """
        data = update.model_dump(exclude_unset=True)
        resp = self._request("PATCH", "/users/me", json=data, signed=True)
        self._check_status(resp)
        return UserPublic(**resp.json())

    def send_contact_request(self, target_id: str, req_type: str,
                             request_id: Optional[str] = None,
                             data: Optional[Dict] = None):
        """
        POST /contacts/request  Отправить запрос контакта.
        Если request_id не указан, генерируется случайный.
        """
        if request_id is None:
            import uuid
            request_id = uuid.uuid4().hex
        payload = {
            "target_id": target_id,
            "type": req_type,
            "request_id": request_id,
            "data": data
        }
        resp = self._request("POST", "/contacts/request", json=payload, signed=True)
        self._check_status(resp)  # ожидаем 202
        return resp.json()

    def check_requests(self) -> List[ContactRequestOut]:
        """GET /contacts/check  Получить список входящих запросов."""
        resp = self._request("GET", "/contacts/check", signed=True)
        self._check_status(resp)
        items = resp.json()
        return [ContactRequestOut(**item) for item in items]

    # ----- Внутренние методы -----

    def _request(self, method: str, path: str, **kwargs):
        signed = kwargs.pop("signed", False)
        if signed:
            if not self.auth.current_login:
                raise ValueError("No active profile. Call load_profile() first.")
            profile = self.storage.load_profile(self.auth.current_login)
            if not profile:
                raise ProfileNotFoundError(f"Profile {self.auth.current_login} not found")
            private_key_pem = profile["private_key"]
            current_nonce = profile.get("nonce")
            if current_nonce is None:
                nonce_to_send = generate_initial_nonce()
            else:
                nonce_to_send = compute_next_nonce(current_nonce)
            self._last_sent_nonce = nonce_to_send
            timestamp = str(int(time.time()))
            path_with_slash = '/' + path.lstrip('/')
            body_bytes = None
            if "json" in kwargs:
                body_bytes = json.dumps(kwargs["json"], ensure_ascii=False, sort_keys=True).encode('utf-8')
                kwargs["data"] = body_bytes
                kwargs.pop("json")
            sig_headers = sign_request(
                method, path_with_slash, body_bytes, private_key_pem,
                self.auth.current_login, timestamp, nonce_to_send
            )
            kwargs.setdefault("headers", {})
            kwargs["headers"].update(sig_headers)
            if body_bytes is not None:
                kwargs["headers"]["Content-Type"] = "application/json"

        url = f"{self.base_url}{path}"
        response = self._session.request(method, url, **kwargs)

        if signed and 200 <= response.status_code < 300:
            self.storage.update_nonce(self.auth.current_login, self._last_sent_nonce)
        elif signed and response.status_code == 409:
            raise NonceConflictError("Nonce conflict, please retry")

        return response

    def _check_status(self, resp: requests.Response):
        """Проверяет статус ответа и выбрасывает исключение в случае ошибки."""
        if resp.status_code >= 400:
            try:
                detail = resp.json().get("detail", resp.text)
            except Exception:
                detail = resp.text
            raise RequestError(resp.status_code, detail)