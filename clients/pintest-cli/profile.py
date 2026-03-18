import os
from pathlib import Path
from typing import Optional, List

from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization

KEYS_DIR = Path(__file__).parent / "keys"
KEYS_DIR.mkdir(exist_ok=True)

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