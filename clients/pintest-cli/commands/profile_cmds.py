import json
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
from . import register
from utils import print_response

@register("genkey")
def genkey(args, client):
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

@register("register")
def register_cmd(args, client):
    """register <login> [key_file] - регистрация нового пользователя"""
    if len(args) < 1:
        print("Usage: register <login> [key_file]")
        return
    login = args[0]
    key_file = args[1] if len(args) > 1 else None

    if key_file:
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
        )
        key_path = client.profile.KEYS_DIR / f"{login}.pem"
        with open(key_path, "wb") as f:
            f.write(priv_pem)
        print(f"Private key saved to {key_path}")

    payload = {
        "login": login,
        "public_key": pub_pem,
        "key_algorithm": "Ed25519"
    }
    
    resp = client.request("POST", "/auth/register", json_body=payload, signed=False)
    if resp is None:
        print("Registration failed: no response")
        return

    if resp.status_code == 200:
        print("Registration successful.")
        if client.profile.load_profile(login):
            print(f"Now using profile {login}.")
    else:
        print(f"Registration failed with status {resp.status_code}")
        # Выводим тело ответа для диагностики
        try:
            error = resp.json()
            print("Error details:", json.dumps(error, indent=2))
        except:
            print(resp.text)

@register("use")
def use(args, client):
    """use <login> - переключиться на профиль"""
    if not args:
        print("Usage: use <login>")
        return
    login = args[0]
    if client.profile.load_profile(login):
        print(f"Now using profile {login}.")
    else:
        print(f"Failed to load profile {login}.")

@register("list")
def list_profiles(args, client):
    """list profiles - показать сохранённые профили"""
    if args and args[0] == "profiles":
        profiles = client.profile.list_profiles()
        if profiles:
            print("Available profiles:")
            for p in profiles:
                mark = "*" if p == client.profile.current_login else " "
                print(f" {mark} {p}")
        else:
            print("No profiles found.")
    else:
        # по умолчанию list users – перенаправим
        from .user_cmds import list_users
        list_users(args, client)

@register("showkey")
def showkey(args, client):
    if client.profile.public_key_pem:
        print("Public key for current profile:")
        print(client.profile.public_key_pem)
    else:
        print("No active profile.")