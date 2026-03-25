class NetLazyError(Exception):
    """Базовое исключение библиотеки."""
    pass

class AuthError(NetLazyError):
    """Ошибка аутентификации (неверная подпись, нет профиля)."""
    pass

class RequestError(NetLazyError):
    """Ошибка HTTP-запроса (статус >=400)."""
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"HTTP {status_code}: {detail}")

class ProfileNotFoundError(NetLazyError):
    """Профиль не найден в локальном хранилище."""
    pass

class NonceConflictError(NetLazyError):
    """Конфликт nonce (требуется повтор)."""
    pass