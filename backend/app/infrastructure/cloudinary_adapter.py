import asyncio
import re
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

_RESOURCE_TYPE_MAP = {"image": "image", "video": "video", "audio": "video"}

class CloudinaryMediaStorage(MediaStorage):
    async def upload(self, file_bytes: bytes, media_type: str, public_id_hint: str) -> str:
        resource_type = _RESOURCE_TYPE_MAP.get(media_type, "auto")
        result = await asyncio.to_thread(
            cloudinary.uploader.upload,
            file_bytes,
            resource_type=resource_type,
            public_id=public_id_hint,
            overwrite=True,
        )
        return result["secure_url"]

    async def delete(self, url: str) -> None:
        match = re.search(r'/upload/(?:v\d+/)?(.+?)\.[a-zA-Z0-9]+$', url)
        if match:
            public_id = match.group(1)
            resource_type = "image" if "image" in url else "video"
            await asyncio.to_thread(cloudinary.uploader.destroy, public_id, resource_type=resource_type)