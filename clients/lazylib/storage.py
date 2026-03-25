import json
import os
import sys
from pathlib import Path
from typing import Optional, Dict

# Определяем доступные механизмы блокировки
if sys.platform != 'win32':
    import fcntl
    LOCK_TYPE = 'fcntl'
else:
    import msvcrt
    LOCK_TYPE = 'msvcrt'


class ProfileStorage:
    """Хранилище профилей (ключи и nonce) в JSON-файле с кросс-платформенной блокировкой."""

    def __init__(self, storage_path: Path):
        self.storage_path = storage_path
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.profiles_file = self.storage_path / "profiles.json"
        self.lock_file = self.storage_path / "profiles.lock"
        self._lock_fd = None
        self._data = self._load()

    def _lock(self):
        """Блокирует доступ к хранилищу."""
        if LOCK_TYPE == 'fcntl':
            self._lock_fd = open(self.lock_file, 'w')
            fcntl.flock(self._lock_fd, fcntl.LOCK_EX)
        else:  # Windows
            # Создаём файл блокировки, если его нет
            if not self.lock_file.exists():
                self.lock_file.touch()
            self._lock_fd = open(self.lock_file, 'rb+')
            msvcrt.locking(self._lock_fd.fileno(), msvcrt.LK_LOCK, 1)

    def _unlock(self):
        """Снимает блокировку."""
        if LOCK_TYPE == 'fcntl':
            if self._lock_fd:
                fcntl.flock(self._lock_fd, fcntl.LOCK_UN)
                self._lock_fd.close()
                self._lock_fd = None
        else:  # Windows
            if self._lock_fd:
                msvcrt.locking(self._lock_fd.fileno(), msvcrt.LK_UNLCK, 1)
                self._lock_fd.close()
                self._lock_fd = None

    def _load(self) -> Dict:
        if self.profiles_file.exists():
            with open(self.profiles_file, "r") as f:
                return json.load(f)
        return {}

    def _save(self):
        self._lock()
        try:
            # Пишем во временный файл для атомарности
            tmp = self.profiles_file.with_suffix('.tmp')
            with open(tmp, 'w') as f:
                json.dump(self._data, f, indent=2)
            os.replace(tmp, self.profiles_file)
        finally:
            self._unlock()

    def save_profile(self, login: str, private_key_pem: str, public_key_pem: str, nonce: Optional[str] = None):
        self._data[login] = {
            "private_key": private_key_pem,
            "public_key": public_key_pem,
            "nonce": nonce,
        }
        self._save()

    def load_profile(self, login: str) -> Optional[Dict]:
        return self._data.get(login)

    def update_nonce(self, login: str, nonce: str):
        if login in self._data:
            self._data[login]["nonce"] = nonce
            self._save()

    def delete_profile(self, login: str):
        if login in self._data:
            del self._data[login]
            self._save()

    def list_profiles(self) -> list:
        return list(self._data.keys())