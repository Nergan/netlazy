import base64
import hashlib
import logging
from fastapi import Request, Header, HTTPException
from app.application.auth_service import AuthService, AuthenticationError
from app.application.profile_service import ProfileService
from app.application.tag_service import TagService
from app.application.feed_service import FeedService
from app.application.inbox_service import InboxService
from app.config import settings
from app.domain.models import User
from app.infrastructure.cloudinary_adapter import CloudinaryMediaStorage
from app.infrastructure.mongo_repo import (
    MongoHandshakeRepository,
    MongoNonceRepository,
    MongoProfileRepository,
    MongoTagRepository,
    MongoUserRepository,
)

AUTH_ERROR = HTTPException(status_code=401, detail="Invalid authentication credentials")

# Composition root: initialize repos
user_repo = MongoUserRepository()
nonce_repo = MongoNonceRepository()
tag_repo = MongoTagRepository()
profile_repo = MongoProfileRepository()
handshake_repo = MongoHandshakeRepository()
media_storage = CloudinaryMediaStorage()

# Composition root: initialize services
auth_service = AuthService(user_repo=user_repo, nonce_repo=nonce_repo)

tag_service = TagService(tag_repo=tag_repo)

profile_service = ProfileService(
    profile_repo=profile_repo,
    tag_repo=tag_repo,
    media_storage=media_storage,
    max_media_items=settings.max_media_items,
    max_bio_length=settings.max_bio_length,
    max_upload_bytes=settings.max_upload_bytes,
    image_max_dimension=settings.image_max_dimension,
    audio_bitrate=settings.audio_bitrate,
)

feed_service = FeedService(
    profile_repo=profile_repo,
    handshake_repo=handshake_repo
)

inbox_service = InboxService(
    handshake_repo=handshake_repo,
    profile_repo=profile_repo
)


async def verify_request_signature(
    request: Request,
    x_user_id: str = Header(...),
    x_timestamp: int = Header(...),
    x_nonce: str = Header(...),
    x_signature: str = Header(...),
) -> User:
    
    body_bytes = await request.body()
    body_hash = hashlib.sha256(body_bytes).hexdigest()
    query_string = request.url.query

    canonical_payload = (
        f"{request.method}\n{request.url.path}\n{query_string}\n"
        f"{x_timestamp}\n{x_nonce}\n{body_hash}"
    ).encode('utf-8')

    try:
        signature_bytes = base64.b64decode(x_signature)
    except Exception:
        raise AUTH_ERROR

    try:
        user = await auth_service.authenticate_request(
            user_id=x_user_id,
            timestamp=x_timestamp,
            nonce=x_nonce,
            signature=signature_bytes,
            canonical_payload=canonical_payload,
        )
    except AuthenticationError:
        raise AUTH_ERROR
    except Exception as e:
        logging.error(f"Unexpected error during signature verification: {e}")
        raise AUTH_ERROR

    return user