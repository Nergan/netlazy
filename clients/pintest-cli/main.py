#!/usr/bin/env python3
"""
NetLazy Hacker Client – точка входа.
"""
import sys
import shlex
from pathlib import Path

# Добавляем путь к проекту, чтобы импорты работали
sys.path.insert(0, str(Path(__file__).parent))

from client import NetLazyClient
from profile import ProfileManager
from commands import get_command, list_commands, COMMANDS

def main():
    profile_mgr = ProfileManager()
    client = NetLazyClient("http://localhost:8000", profile_mgr)

    print("NetLazy Hacker Client")
    print("Type 'help' for commands.")

    while True:
        try:
            line = input("netlazy> ").strip()
            if not line:
                continue
            parts = shlex.split(line)
            cmd_name = parts[0].lower()
            args = parts[1:]

            cmd_func = get_command(cmd_name)
            if cmd_func:
                # Все команды принимают (args, client)
                cmd_func(args, client)
            else:
                print(f"Unknown command: {cmd_name}")
        except KeyboardInterrupt:
            print("\nquit...")
            return
        except EOFError:
            break
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    main()