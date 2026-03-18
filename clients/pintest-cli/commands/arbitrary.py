import json
from . import register
from utils import print_response

@register("getreq")
def get_req(args, client):
    """getreq <path> [key=value...] - произвольный GET-запрос"""
    if not args:
        print("Usage: getreq <path> [key=value...]")
        return
    path = args[0]
    params = {}
    for item in args[1:]:
        if '=' in item:
            k, v = item.split('=', 1)
            params[k] = v
        else:
            print(f"Ignoring invalid param: {item}")
    resp = client.request("GET", path, params=params, signed=True)
    if resp:
        print_response(resp)

@register("post")
def post_req(args, client):
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
        print_response(resp)

@register("patch")
def patch_req(args, client):
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
        print_response(resp)

@register("delete")
def delete_req(args, client):
    """delete <path>"""
    if not args:
        print("Usage: delete <path>")
        return
    path = args[0]
    resp = client.request("DELETE", path, signed=True)
    if resp:
        print_response(resp)

@register("raw")
def raw_req(args, client):
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
        print_response(resp)