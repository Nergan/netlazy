import requests
import json
from typing import Optional, Dict, Any

from signature import sign_request

class NetLazyClient:
    def __init__(self, base_url: str, profile_mgr):
        self.base_url = base_url.rstrip('/')
        self.profile = profile_mgr
        self.session = requests.Session()

    def request(
        self,
        method: str,
        path: str,
        params: Optional[Dict] = None,
        json_body: Any = None,
        headers: Optional[Dict] = None,
        signed: bool = False
    ) -> Optional[requests.Response]:
        """Универсальный метод отправки запроса"""
        url = f"{self.base_url}/{path.lstrip('/')}"
        req_headers = headers.copy() if headers else {}

        # Подготовка тела
        body_bytes = None
        if json_body is not None:
            body_bytes = json.dumps(json_body, ensure_ascii=False).encode('utf-8')
            req_headers.setdefault("Content-Type", "application/json")

        # Если требуется подпись и есть активный профиль
        if signed and self.profile.private_key:
            sig_headers = sign_request(
                method,
                '/' + path.lstrip('/'),
                body_bytes,
                self.profile.private_key,
                self.profile.current_login
            )
            req_headers.update(sig_headers)
        elif signed:
            print("Warning: Signed request requested but no active profile. Skipping signature.")

        try:
            response = self.session.request(
                method,
                url,
                params=params,
                data=body_bytes,
                headers=req_headers
            )
            return response
        except Exception as e:
            print(f"Request failed: {e}")
            return None