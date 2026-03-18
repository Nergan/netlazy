"""
Пакет команд. Собирает все команды в единый словарь.
"""
from typing import Callable, Dict

# Словарь команд: имя -> функция
COMMANDS: Dict[str, Callable] = {}

def register(name: str):
    """Декоратор для регистрации команды"""
    def decorator(func):
        COMMANDS[name] = func
        return func
    return decorator

def get_command(name: str):
    return COMMANDS.get(name)

def list_commands():
    return list(COMMANDS.keys())

# Импортируем модули, чтобы команды зарегистрировались
from . import connection, profile_cmds, user_cmds, contact_cmds, arbitrary, misc