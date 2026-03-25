from typing import Optional
from .storage import ProfileStorage

class AuthManager:
    """Управление текущим активным профилем."""

    def __init__(self, storage: ProfileStorage):
        self.storage = storage
        self.current_login: Optional[str] = None

    def set_current_profile(self, login: str):
        """Устанавливает активный профиль, предварительно проверив его существование."""
        if not self.storage.load_profile(login):
            raise ValueError(f"Profile {login} not found")
        self.current_login = login