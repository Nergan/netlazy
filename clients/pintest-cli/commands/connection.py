from . import register
from utils import print_response

@register("seturl")
def seturl(args, client):
    if not args:
        print(f"Current URL: {client.base_url}")
    else:
        client.base_url = args[0].rstrip('/')
        print(f"URL set to {client.base_url}")

@register("env")
def env(args, client):
    print(f"URL: {client.base_url}")
    if client.profile.current_login:
        print(f"Active profile: {client.profile.current_login}")
    else:
        print("No active profile.")
    print(f"Keys directory: {client.profile.KEYS_DIR}")