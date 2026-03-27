# NetLazy

The service for.. ee.. dating?

## Architecture

The project is built on a modular principle: the server acts only as a layer between clients and the database. Clients (web, Telegram bot, desktop app, whatever) interact with the server through a single API.

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Clients    │── ─▶│    Server    │───▶│   MongoDB    │
│    (any)     │     │   FastAPI    │     │              │
│              │     │   + Motor    │     │              │
└──────────────┘     └──────────────┘     └──────────────┘
```

## Tech Stack

- **Language**: Python 3.14
- **Web Framework**: FastAPI (PyAPI)
- **Database**: MongoDB (asynchronous Motor driver)
- **Cryptography**: `cryptography` (Ed25519 for request signing)
- **Validation**: Pydantic v2
- **Configuration**: Pydantic Settings

## Authentication

The project implements **asymmetric cryptographic authentication** without transmitting secrets over the network:

- The client generates an Ed25519 key pair and sends the public key during registration.
- Each request to protected endpoints is signed with a private key. The signature is calculated from a canonical string including the method, full path (with sorted query parameters), timestamp, nonce, and hash of the request body.
- The server verifies the signature using the stored public key.
- A nonce is used to protect against replay attacks (stored in an in-memory cache for the duration of the signature).

This approach eliminates the need to transmit passwords or tokens and does not require session management.

## User Document Structure

```json
{
  "public": { // Public data, visible to everyone
    "id": "alice", // unique login
    "name": "Alice", // optional
    "sex": "female", // optional
    "desc": "...", // optional
    "img": "base64...", // optional
    "location": { // optional
      "precise": { // GeoJSON Point
        "type": "Point",
        "coordinates": [37.6173, 55.7558]
      },
      "exemplary": ["Moscow"]
    },
    "tags": ["it", "coffee"] // optional
  },
  "protect": { // Data with a custom access level
    "is_online": false
  },
  "private": { // For internal use only
    "public_key": "-----BEGIN PUBLIC KEY-----...",
    "key_algorithm": "Ed25519",
    "requests": [ // incoming request queue
      {
        "request_id": "abc-123",
        "type": "swap",
        "from_id": "bob",
        "data": { "message": "hi" },
        "timestamp": 1712345678
      }
    ],
    "requests_size_bytes": 1234, // total size of the requests array in bytes
    "created_at": 1712345678,
    "last_online": 1712345678
  }
}
```

## Request system (contact exchange)

- Requests from one user to another are stored in the recipient's `private.requests` field.
- The client can fetch the list of incoming requests via `GET /contacts/requests`. Each request has a unique `request_id`.
- After processing a request, the client must delete it by calling `DELETE /contacts/requests/{request_id}`. This design prevents accidental loss of requests.
- For backward compatibility, `GET /contacts/check` returns the list (but does **not** clear it).
- Request types:
  - `swap` – offer to exchange contacts
  - `give` – send your contacts (requires `data` field)
  - `get` – request public contacts

## MongoDB Indexes

- Unique index on `public.id`
- Multi-key index on `public.tags`
- 2dsphere geoindex on `public.location.precise`
- Index on `private.created_at` for sorting
- Composite index `(public.tags, private.created_at)` for optimized filtering
- Index on `private.requests.request_id` for duplicate checks
- Compound index on `(private.requests.from_id, private.requests.type)` to enforce per‑type limits

## API (Main Endpoints)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/register` | Register with a public key |
| POST | `/auth/change-key` | Change the key (requires a signature from the old one) |
| GET | `/users/list` | User list with tag filtering, sorting, and pagination |
| GET | `/users/{login}` | Public user profile |
| GET | `/users/me` | Your profile (requires authentication) |
| PATCH | `/users/me` | Update your profile |
| POST | `/contacts/request` | Send a contact request (swap/give/get) |
| GET | `/contacts/requests` | Get the list of incoming requests (without deletion) |
| DELETE | `/contacts/requests/{request_id}` | Delete a processed request |
| GET | `/contacts/check` | (deprecated) Returns the list of requests (same as `/requests`) |

## Implementation Features

- All secure endpoints require signature headers: `X-Login`, `X-Timestamp`, `X-Nonce`, `X-Body-Hash`, `X-Signature`.
- The signature is verified by a dependency, which also updates `last_online` on each successful request.
- Images are stored in MongoDB as binary data (base64 during transfer), limited to 5 MB.
- Date of birth (`dob`) is validated as `YYYY-MM-DD`.
- The `sex` field only accepts `male` or `female` values.
- Rate limiting is applied per IP (configurable via environment variables).
- Request queue size is limited by total bytes (configurable, default 15 MB) to prevent document overflow.

## Development

The project is divided into modules:

- `core/` – settings, database connection, dependencies (signature verification), rate limiting
- `models/` – Pydantic models
- `services/` – business logic
- `routers/` – FastAPI endpoints
- `main.py` – entry point

The server is implemented with **FastAPI (PyAPI)** and can be deployed as a standalone application. Clients can be written in any language that supports Ed25519 signature generation.