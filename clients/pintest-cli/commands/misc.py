import os
import sys
from . import register

@register("help")
def help_cmd(args, client):
    """help [command] - показать справку"""
    if args:
        # Можно добавить детальную справку по командам, но пока общая
        print(f"No detailed help for '{args[0]}' yet.")
    else:
        print("""
NetLazy Hacker Client Commands:

Connection:
  seturl [url]                Show or set base URL
  env                         Show current settings

Profiles & Keys:
  genkey [algorithm]          Generate and display key pair
  register <login> [key_file]  Register new user
  use <login>                 Switch to profile
  list profiles               List saved profiles
  showkey                     Show public key of current profile

User endpoints:
  list [tags...] [params]     GET /users/list
  me [update field=value...]  GET /users/me or PATCH
  get <login>                 GET /users/{login}

Contact endpoints:
  request <target> <type> <request_id> [data]  POST /contacts/request
  check                       GET /contacts/check

Arbitrary requests (automatically signed if profile active):
  getreq <path> [params...]   GET with query params
  post <path> <json>          POST with JSON
  patch <path> <json>         PATCH with JSON
  delete <path>               DELETE
  raw <method> <path> [headers...] [--data <json>]  Custom request

Utilities:
  help [command]              This help
  cls                         Clear screen
  exit                        Exit
""")

@register("cls")
def cls(args, client):
    os.system('cls' if os.name == 'nt' else 'clear')

@register("exit")
def exit_cmd(args, client):
    sys.exit(0)