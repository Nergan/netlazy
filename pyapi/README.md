**Mini-documentation for the `api` library**

### 1. Client Initialization
```python
from pyapi import NetLazyClient

client = NetLazyClient("http://localhost:8000")
```
By default, profiles are stored in the `.netlazy` folder of the current working directory. You can specify a different path using the `storage_path` parameter.

### 2. Profile Management

**Register a new user**
```python
client.register("alice") # generates keys
client.register("alice", private_key_pem, public_key_pem)  # with existing keys
```

**Load an existing profile**
```python
client.load_profile("alice")
```

**List saved profiles**
```python
client.list_profiles() # returns a list of logins
```

**Current active profile**
```python
client.get_current_login() # login or None
```

### 3. Working with Users

**Get your own profile** (requires authentication)
```python
me = client.get_my_profile()
print(me.name)
```

**Update your profile** (requires authentication)
```python
from pyapi import UserProfileUpdate

update = UserProfileUpdate(name="<name>", tags=["it", "coffee"])
updated = client.update_my_profile(update)
```

**Get another user's profile**
```python
user = client.get_user("<name>")
```

**List users with filtering**
```python
result = client.list_users(
    tags=["<tag>"], 
    match_all=False, 
    sort_by="created_at",
    limit=10
)
for user in result.items:
    print(user.name, user.tags)
```

### 4. Contact Requests

**Send a request** (requires authentication)
```python
client.send_contact_request(
    target_id="<id>",
    req_type="swap",  # "swap", "give", "get"
    data={"message": "Hello!"}  # optional
)
```

**Check incoming requests** (requires authentication)
```python
requests = client.check_requests()
for req in requests:
    print(req.from_id, req.type, req.data)
```

### 5. Exceptions
- `RequestError` – HTTP error (4xx/5xx status)
- `NonceConflictError` – nonce conflict (retry the request)
- `AuthError` – authentication issues
- `ProfileNotFoundError` – profile not found in storage

---

**Example of a complete session**
```python
client = NetLazyClient("http://localhost:8000")

# Registration
client.register("alice")

# Update profile
update = UserProfileUpdate(name="Alice", tags=["it"])
client.update_my_profile(update)

# Search for users
users = client.list_users(tags=["coffee"])
print(f"Found: {users.total}")

# Send a request
client.send_contact_request("bob", "swap")

# Check incoming requests
incoming = client.check_requests()
```