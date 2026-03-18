import json
import requests

def print_response(resp: requests.Response):
    """Красивый вывод ответа"""
    print(f"\nStatus: {resp.status_code} {resp.reason}")
    print("Headers:")
    for k, v in resp.headers.items():
        print(f"  {k}: {v}")
    print("Body:")
    try:
        data = resp.json()
        print(json.dumps(data, indent=2, ensure_ascii=False))
    except:
        print(resp.text)
    print()