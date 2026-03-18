import json
from . import register
from utils import print_response

@register("listusers")
def list_users(args, client):
    """list [tags...] [key=value...]"""
    params = {}
    tags = []
    for arg in args:
        if '=' in arg:
            k, v = arg.split('=', 1)
            if k == 'match_all':
                params['match_all'] = v.lower() == 'true'
            elif k == 'sort_by':
                params['sort_by'] = v
            elif k == 'sort_order':
                params['sort_order'] = v
            elif k == 'limit':
                params['limit'] = int(v)
            elif k == 'offset':
                params['offset'] = int(v)
            else:
                print(f"Ignoring unknown param: {k}")
        else:
            tags.append(arg)
    if tags:
        params['tags'] = tags
    resp = client.request("GET", "/users/list", params=params, signed=False)
    if resp:
        print_response(resp)

@register("me")
def me(args, client):
    """me [update field=value...] - получить или обновить свой профиль"""
    if not args:
        # GET /users/me
        resp = client.request("GET", "/users/me", signed=True)
        if resp:
            print_response(resp)
        return
    if args[0] == "update":
        # PATCH /users/me
        update_data = {}
        for item in args[1:]:
            if '=' in item:
                k, v = item.split('=', 1)
                try:
                    val = json.loads(v)
                except:
                    val = v
                update_data[k] = val
            else:
                print(f"Ignoring {item}, use field=value")
        if not update_data:
            print("No data to update")
            return
        resp = client.request("PATCH", "/users/me", json_body=update_data, signed=True)
        if resp:
            print_response(resp)
    else:
        print("Usage: me [update field=value...]")

@register("get")
def get_user(args, client):
    """get <login> - получить профиль другого пользователя"""
    if not args:
        print("Usage: get <login>")
        return
    login = args[0]
    resp = client.request("GET", f"/users/{login}", signed=False)
    if resp:
        print_response(resp)