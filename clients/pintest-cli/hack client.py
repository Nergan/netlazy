#!/usr/bin/env python3
"""
NetLazy Hacker Client
Консольный клиент для тестирования NetLazy API с поддержкой криптографической подписи Ed25519.
"""

import os
import sys
import json
import time
import uuid
import shlex
import base64
import hashlib
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple

import requests
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives import hashes
from cryptography.exceptions import InvalidSignature

# ------------------------------------------------------------
# Конфигурация
# ------------------------------------------------------------
DEFAULT_URL = "http://localhost:8000"
KEYS_DIR = Path(__file__).parent / "keys"
KEYS_DIR.mkdir(exist_ok=True)

# ------------------------------------------------------------
# Управление профилями (ключами)
# ------------------------------------------------------------
class ProfileManager:
    def __init__(self):
        self.current_login: Optional[str] = None
        self.private_key: Optional[ed25519.Ed25519PrivateKey] = None
        self.public_key_pem: Optional[str] = None

    def load_profile(self, login: str) -> bool:
        """Загружает приватный ключ из файла keys/<login>.pem"""
        key_path = KEYS_DIR / f"{login}.pem"
        if not key_path.exists():
            print(f"Key file not found: {key_path}")
            return False
        try:
            with open(key_path, "rb") as f:
                pem_data = f.read()
            self.private_key = serialization.load_pem_private_key(pem_data, password=None)
            if not isinstance(self.private_key, ed25519.Ed25519PrivateKey):
                print("Key is not Ed25519")
                return False
            self.current_login = login
            # сохраняем публичный ключ для отображения
            public_key = self.private_key.public_key()
            self.public_key_pem = public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            ).decode('utf-8')
            return True
        except Exception as e:
            print(f"Failed to load key: {e}")
            return False

    def generate_and_save(self, login: str) -> bool:
        """Генерирует новую ключевую пару и сохраняет в keys/<login>.pem"""
        private_key = ed25519.Ed25519PrivateKey.generate()
        pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        key_path = KEYS_DIR / f"{login}.pem"
        with open(key_path, "wb") as f:
            f.write(pem)
        print(f"Private key saved to {key_path}")
        return self.load_profile(login)

    def list_profiles(self) -> List[str]:
        """Возвращает список логинов из папки keys"""
        profiles = []
        for f in KEYS_DIR.glob("*.pem"):
            profiles.append(f.stem)
        return profiles

# ------------------------------------------------------------
# Подпись запросов
# ------------------------------------------------------------
def sign_request(
    method: str,
    path: str,
    body: Optional[bytes],
    private_key: ed25519.Ed25519PrivateKey,
    login: str
) -> Dict[str, str]:
    """
    Формирует заголовки для подписанного запроса.
    body должен быть байтовой строкой (например, json.dumps().encode()).
    """
    timestamp = str(int(time.time()))
    nonce = str(uuid.uuid4())
    # body hash
    if body:
        body_hash = hashlib.sha256(body).hexdigest()
    else:
        body_hash = ""
    # каноническая строка
    canonical = f"{method}\n{path}\n{timestamp}\n{nonce}\n{body_hash}"
    # подпись
    signature = private_key.sign(canonical.encode())
    signature_b64 = base64.b64encode(signature).decode()
    return {
        "X-Login": login,
        "X-Timestamp": timestamp,
        "X-Nonce": nonce,
        "X-Body-Hash": body_hash,
        "X-Signature": signature_b64,
    }

# ------------------------------------------------------------
# Отправка запросов
# ------------------------------------------------------------
class NetLazyClient:
    def __init__(self, base_url: str, profile_mgr: ProfileManager):
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
                '/' + path.lstrip('/'),  # путь с ведущим слешем
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

    def print_response(self, resp: requests.Response):
        """Красивый вывод ответа"""
        print(f"\nStatus: {resp.status_code} {resp.reason}")
        print("Headers:")
        for k, v in resp.headers.items():
            print(f"  {k}: {v}")
        print("Body:")
        try:
            data = resp.json()
            print(json.dumps(data, indent=2, ensure_ascii=False))
        except:
            print(resp.text)
        print()

# ------------------------------------------------------------
# Команды
# ------------------------------------------------------------
def cmd_seturl(args: List[str], client: NetLazyClient):
    if not args:
        print(f"Current URL: {client.base_url}")
    else:
        client.base_url = args[0].rstrip('/')
        print(f"URL set to {client.base_url}")

def cmd_genkey(args: List[str], client: NetLazyClient):
    """genkey [algorithm] - генерирует ключевую пару и выводит (не сохраняет)"""
    alg = args[0] if args else "Ed25519"
    if alg != "Ed25519":
        print("Only Ed25519 supported")
        return
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    pub_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode()
    priv_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    ).decode()
    print("Generated Ed25519 key pair:")
    print("Public key:")
    print(pub_pem)
    print("Private key (save this if needed):")
    print(priv_pem)

def cmd_register(args: List[str], client: NetLazyClient):
    """register <login> [key_file] - регистрация нового пользователя"""
    if len(args) < 1:
        print("Usage: register <login> [key_file]")
        return
    login = args[0]
    key_file = args[1] if len(args) > 1 else None

    if key_file:
        # загружаем публичный ключ из файла
        try:
            with open(key_file, "rb") as f:
                pem_data = f.read()
            public_key = serialization.load_pem_public_key(pem_data)
            if not isinstance(public_key, ed25519.Ed25519PublicKey):
                print("Key is not Ed25519")
                return
            pub_pem = public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            ).decode()
        except Exception as e:
            print(f"Failed to load public key: {e}")
            return
    else:
        # генерируем новую пару и сохраняем
        private_key = ed25519.Ed25519PrivateKey.generate()
        public_key = private_key.public_key()
        pub_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode()
        # сохраняем приватный ключ
        priv_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        key_path = KEYS_DIR / f"{login}.pem"
        with open(key_path, "wb") as f:
            f.write(priv_pem)
        print(f"Private key saved to {key_path}")

    # отправляем запрос на регистрацию
    payload = {
        "login": login,
        "public_key": pub_pem,
        "key_algorithm": "Ed25519"
    }
    resp = client.request("POST", "/auth/register", json_body=payload, signed=False)
    if resp and resp.status_code == 200:
        print("Registration successful.")
        # автоматически загружаем профиль
        if client.profile.load_profile(login):
            print(f"Now using profile {login}.")
    else:
        if resp:
            client.print_response(resp)
        else:
            print("Registration failed (no response)")

def cmd_use(args: List[str], client: NetLazyClient):
    """use <login> - переключиться на профиль"""
    if not args:
        print("Usage: use <login>")
        return
    login = args[0]
    if client.profile.load_profile(login):
        print(f"Now using profile {login}.")
    else:
        print(f"Failed to load profile {login}.")

def cmd_list_profiles(args: List[str], client: NetLazyClient):
    profiles = client.profile.list_profiles()
    if profiles:
        print("Available profiles:")
        for p in profiles:
            mark = "*" if p == client.profile.current_login else " "
            print(f" {mark} {p}")
    else:
        print("No profiles found.")

def cmd_showkey(args: List[str], client: NetLazyClient):
    if client.profile.public_key_pem:
        print("Public key for current profile:")
        print(client.profile.public_key_pem)
    else:
        print("No active profile.")

def cmd_list_users(args: List[str], client: NetLazyClient):
    """list [tags...] [key=value...]"""
    params = {}
    tags = []
    for arg in args:
        if '=' in arg:
            k, v = arg.split('=', 1)
            if k == 'match_all':
                params['match_all'] = v.lower() == 'true'
            elif k == 'sort_by':
                params['sort_by'] = v
            elif k == 'sort_order':
                params['sort_order'] = v
            elif k == 'limit':
                params['limit'] = int(v)
            elif k == 'offset':
                params['offset'] = int(v)
            else:
                print(f"Ignoring unknown param: {k}")
        else:
            tags.append(arg)
    if tags:
        params['tags'] = tags  # requests обработает как повторяющиеся параметры
    resp = client.request("GET", "/users/list", params=params, signed=False)
    if resp:
        client.print_response(resp)

def cmd_me(args: List[str], client: NetLazyClient):
    """me [update field=value...] - получить или обновить свой профиль"""
    if not args:
        # GET /users/me
        resp = client.request("GET", "/users/me", signed=True)
        if resp:
            client.print_response(resp)
        return
    if args[0] == "update":
        # PATCH /users/me
        update_data = {}
        for item in args[1:]:
            if '=' in item:
                k, v = item.split('=', 1)
                # попытка распарсить JSON
                try:
                    val = json.loads(v)
                except:
                    val = v
                update_data[k] = val
            else:
                print(f"Ignoring {item}, use field=value")
        if not update_data:
            print("No data to update")
            return
        resp = client.request("PATCH", "/users/me", json_body=update_data, signed=True)
        if resp:
            client.print_response(resp)
    else:
        print("Usage: me [update field=value...]")

def cmd_get_user(args: List[str], client: NetLazyClient):
    """get <login> - получить профиль другого пользователя"""
    if not args:
        print("Usage: get <login>")
        return
    login = args[0]
    resp = client.request("GET", f"/users/{login}", signed=False)
    if resp:
        client.print_response(resp)

def cmd_request(args: List[str], client: NetLazyClient):
    """request <target> <type> <request_id> [data_json]"""
    if len(args) < 3:
        print("Usage: request <target> <type> <request_id> [data_json]")
        return
    target = args[0]
    req_type = args[1]
    req_id = args[2]
    data = None
    if len(args) >= 4:
        try:
            data = json.loads(args[3])
        except:
            print("Invalid JSON data, ignoring")
    payload = {
        "target_id": target,
        "type": req_type,
        "request_id": req_id,
        "data": data
    }
    resp = client.request("POST", "/contacts/request", json_body=payload, signed=True)
    if resp:
        client.print_response(resp)

def cmd_check(args: List[str], client: NetLazyClient):
    """check - проверить входящие запросы"""
    resp = client.request("GET", "/contacts/check", signed=True)
    if resp:
        client.print_response(resp)

def cmd_get(args: List[str], client: NetLazyClient):
    """get <path> [key=value...] - произвольный GET-запрос"""
    if not args:
        print("Usage: get <path> [key=value...]")
        return
    path = args[0]
    params = {}
    for item in args[1:]:
        if '=' in item:
            k, v = item.split('=', 1)
            params[k] = v
        else:
            print(f"Ignoring invalid param: {item}")
    resp = client.request("GET", path, params=params, signed=True)  # подписываем, если есть профиль
    if resp:
        client.print_response(resp)

def cmd_post(args: List[str], client: NetLazyClient):
    """post <path> <json>"""
    if len(args) < 2:
        print("Usage: post <path> <json>")
        return
    path = args[0]
    try:
        json_body = json.loads(' '.join(args[1:]))
    except:
        print("Invalid JSON")
        return
    resp = client.request("POST", path, json_body=json_body, signed=True)
    if resp:
        client.print_response(resp)

def cmd_patch(args: List[str], client: NetLazyClient):
    """patch <path> <json>"""
    if len(args) < 2:
        print("Usage: patch <path> <json>")
        return
    path = args[0]
    try:
        json_body = json.loads(' '.join(args[1:]))
    except:
        print("Invalid JSON")
        return
    resp = client.request("PATCH", path, json_body=json_body, signed=True)
    if resp:
        client.print_response(resp)

def cmd_delete(args: List[str], client: NetLazyClient):
    """delete <path>"""
    if not args:
        print("Usage: delete <path>")
        return
    path = args[0]
    resp = client.request("DELETE", path, signed=True)
    if resp:
        client.print_response(resp)

def cmd_raw(args: List[str], client: NetLazyClient):
    """raw <method> <path> [headers...] [--data <json>]"""
    if len(args) < 2:
        print("Usage: raw <method> <path> [headers...] [--data <json>]")
        return
    method = args[0].upper()
    path = args[1]
    headers = {}
    json_body = None
    i = 2
    while i < len(args):
        if args[i] == "--data" and i+1 < len(args):
            try:
                json_body = json.loads(args[i+1])
            except:
                print("Invalid JSON after --data")
                return
            i += 2
        elif ':' in args[i]:
            k, v = args[i].split(':', 1)
            headers[k.strip()] = v.strip()
            i += 1
        else:
            print(f"Ignoring unknown argument: {args[i]}")
            i += 1
    resp = client.request(method, path, json_body=json_body, headers=headers, signed=True)
    if resp:
        client.print_response(resp)

def cmd_env(args: List[str], client: NetLazyClient):
    print(f"URL: {client.base_url}")
    if client.profile.current_login:
        print(f"Active profile: {client.profile.current_login}")
    else:
        print("No active profile.")
    print(f"Keys directory: {KEYS_DIR}")

def cmd_help(args: List[str], client: NetLazyClient):
    print("""
NetLazy Hacker Client Commands:

Connection:
  seturl [url]                Show or set base URL (default: http://localhost:8000)

Profiles & Keys:
  genkey [algorithm]          Generate and display key pair (only Ed25519 supported)
  register <login> [key_file]  Register new user. If key_file omitted, generates new key.
  use <login>                 Switch to profile
  list                        List saved profiles
  showkey                     Show public key of current profile

User endpoints:
  list [tags...] [params]     GET /users/list (params: match_all, sort_by, sort_order, limit, offset)
  me [update field=value...]   GET /users/me or PATCH with updates
  get <login>                 GET /users/{login}

Contact endpoints:
  request <target> <type> <request_id> [data]  POST /contacts/request
  check                       GET /contacts/check

Arbitrary requests (automatically signed if profile active):
  get <path> [params...]      GET with query params
  post <path> <json>          POST with JSON body
  patch <path> <json>         PATCH with JSON body
  delete <path>               DELETE
  raw <method> <path> [headers...] [--data <json>]  Custom request

Utilities:
  env                         Show current settings
  help [command]              This help
  cls                         Clear screen
  exit                        Exit
""")

def cmd_cls(args: List[str], client: NetLazyClient):
    os.system('cls' if os.name == 'nt' else 'clear')

def cmd_exit(args: List[str], client: NetLazyClient):
    sys.exit(0)

# ------------------------------------------------------------
# Главный цикл
# ------------------------------------------------------------
def main():
    profile_mgr = ProfileManager()
    client = NetLazyClient(DEFAULT_URL, profile_mgr)

    commands = {
        "seturl": cmd_seturl,
        "genkey": cmd_genkey,
        "register": cmd_register,
        "use": cmd_use,
        "list": cmd_list_profiles,  # переопределим list для профилей, но также есть list для пользователей
        "showkey": cmd_showkey,
        "listusers": cmd_list_users,  # для списка пользователей используем listusers
        "me": cmd_me,
        "get": cmd_get_user,          # для получения пользователя
        "request": cmd_request,
        "check": cmd_check,
        "getreq": cmd_get,            # произвольный GET
        "post": cmd_post,
        "patch": cmd_patch,
        "delete": cmd_delete,
        "raw": cmd_raw,
        "env": cmd_env,
        "help": cmd_help,
        "cls": cmd_cls,
        "exit": cmd_exit,
    }

    print("NetLazy Hacker Client")
    print("Type 'help' for commands.")

    while True:
        try:
            line = input("netlazy> ").strip()
            if not line:
                continue
            parts = shlex.split(line)
            cmd = parts[0].lower()
            args = parts[1:]

            if cmd in commands:
                commands[cmd](args, client)
            elif cmd == "list" and args and args[0] in ["profiles", "users"]:
                # Для удобства: list profiles / list users
                if args[0] == "profiles":
                    cmd_list_profiles(args[1:], client)
                elif args[0] == "users":
                    cmd_list_users(args[1:], client)
                else:
                    print("Unknown list subcommand. Try 'list profiles' or 'list users'.")
            elif cmd == "list":
                # По умолчанию list users
                cmd_list_users(args, client)
            else:
                print(f"Unknown command: {cmd}")
        except KeyboardInterrupt:
            print("\nUse 'exit' to quit.")
        except EOFError:
            break
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    main()