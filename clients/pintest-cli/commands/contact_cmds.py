import json
from . import register
from utils import print_response

@register("request")
def request_cmd(args, client):
    """request <target> <type> <request_id> [data_json]"""
    if len(args) < 3:
        print("Usage: request <target> <type> <request_id> [data_json]")
        return
    target = args[0]
    req_type = args[1]
    req_id = args[2]
    data = None
    if len(args) >= 4:
        try:
            data = json.loads(args[3])
        except:
            print("Invalid JSON data, ignoring")
    payload = {
        "target_id": target,
        "type": req_type,
        "request_id": req_id,
        "data": data
    }
    resp = client.request("POST", "/contacts/request", json_body=payload, signed=True)
    if resp:
        print_response(resp)

@register("check")
def check(args, client):
    """check - проверить входящие запросы"""
    resp = client.request("GET", "/contacts/check", signed=True)
    if resp:
        print_response(resp)