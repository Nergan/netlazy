import asyncio
import cloudinary
import cloudinary.uploader
from app.config import settings
from app.domain.repository import MediaStorage

cloudinary.config(
    cloud_name=settings.cloudinary_cloud_name,
    api_key=settings.cloudinary_api_key,
    api_secret=settings.cloudinary_api_secret,
    secure=True,
)

# Cloudinary has no distinct "audio" resource type; audio files are uploaded
# and delivered under "video" (its encoder pipeline handles audio codecs too).
_RESOURCE_TYPE_MAP = {"image": "image", "video": "video", "audio": "video"}

class CloudinaryMediaStorage(MediaStorage):
    async def upload(self, file_bytes: bytes, media_type: str, public_id_hint: str) -> str:
        resource_type = _RESOURCE_TYPE_MAP.get(media_type, "auto")
        # cloudinary's SDK is synchronous/blocking; offload it so it doesn't
        # block the event loop.
        result = await asyncio.to_thread(
            cloudinary.uploader.upload,
            file_bytes,
            resource_type=resource_type,
            public_id=public_id_hint,
            overwrite=True,
        )
        return result["secure_url"]