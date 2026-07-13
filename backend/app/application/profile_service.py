from datetime import datetime, timezone
from typing import List
from app.domain.models import Contact, MediaItem, Profile
from app.domain.repository import MediaStorage, ProfileRepository, TagRepository
from app.infrastructure import media_processor

class InvalidTagError(Exception):
    def __init__(self, unknown_tags: List[str]):
        self.unknown_tags = unknown_tags
        super().__init__(f"Unknown tags: {', '.join(unknown_tags)}")

class MediaLimitExceededError(Exception):
    pass

class UnsupportedMediaTypeError(Exception):
    pass

class MediaProcessingError(Exception):
    pass

class MediaNotFoundError(Exception):
    pass

class ProfileService:
    def __init__(
        self,
        profile_repo: ProfileRepository,
        tag_repo: TagRepository,
        media_storage: MediaStorage,
        max_media_items: int,
        max_bio_length: int,
        max_upload_bytes: int,
        image_max_dimension: int,
        audio_bitrate: str,
    ):
        self._profile_repo = profile_repo
        self._tag_repo = tag_repo
        self._media_storage = media_storage
        self._max_media_items = max_media_items
        self._max_bio_length = max_bio_length
        self._max_upload_bytes = max_upload_bytes
        self._image_max_dimension = image_max_dimension
        self._audio_bitrate = audio_bitrate

    async def get_or_create_profile(self, user_id: str) -> Profile:
        profile = await self._profile_repo.get_by_user_id(user_id)
        if profile:
            return profile
        return Profile(user_id=user_id)

    async def update_profile(
        self,
        user_id: str,
        bio: str,
        tags: List[str],
        contacts: List[Contact],
    ) -> Profile:
        valid_names = set(await self._tag_repo.get_all_names())
        unknown = [t for t in tags if t not in valid_names]
        if unknown:
            raise InvalidTagError(unknown)

        profile = await self.get_or_create_profile(user_id)
        profile.bio = bio[: self._max_bio_length]
        profile.tags = tags
        profile.contacts = contacts
        profile.updated_at = datetime.now(timezone.utc)

        await self._profile_repo.upsert(profile)
        return profile

    async def upload_media(self, user_id: str, raw_bytes: bytes) -> Profile:
        if len(raw_bytes) > self._max_upload_bytes:
            raise MediaProcessingError("File exceeds maximum upload size")

        mime_type = media_processor.sniff_mime_type(raw_bytes)
        try:
            media_type = media_processor.classify_media_type(mime_type)
        except media_processor.UnsupportedMediaTypeError as e:
            raise UnsupportedMediaTypeError(str(e)) from e

        profile = await self.get_or_create_profile(user_id)

        if media_type in ("image", "video") and len(profile.media) >= self._max_media_items:
            raise MediaLimitExceededError(f"Maximum of {self._max_media_items} media items reached")

        try:
            if media_type == "image":
                processed = await media_processor.process_image(raw_bytes, self._image_max_dimension)
            elif media_type == "audio":
                processed = await media_processor.process_audio(raw_bytes, self._audio_bitrate)
            else:  # video: bypass local transcoding per plan.md memory safeguard
                processed = raw_bytes
        except media_processor.MediaProcessingError as e:
            raise MediaProcessingError(str(e)) from e

        public_id_hint = f"{user_id}/{media_type}_{int(datetime.now(timezone.utc).timestamp() * 1000)}"
        url = await self._media_storage.upload(processed, media_type, public_id_hint)
        item = MediaItem(url=url, media_type=media_type, blur=False)

        if media_type == "audio":
            profile.audio = item
        else:
            profile.media.append(item)

        profile.updated_at = datetime.now(timezone.utc)
        await self._profile_repo.upsert(profile)
        return profile

    async def remove_media(self, user_id: str, media_url: str) -> Profile:
        profile = await self.get_or_create_profile(user_id)
        before = len(profile.media)
        profile.media = [m for m in profile.media if m.url != media_url]
        if len(profile.media) == before:
            raise MediaNotFoundError(f"No media item with url {media_url}")

        profile.updated_at = datetime.now(timezone.utc)
        await self._profile_repo.upsert(profile)
        return profile

    async def clear_audio(self, user_id: str) -> Profile:
        profile = await self.get_or_create_profile(user_id)
        profile.audio = None
        profile.updated_at = datetime.now(timezone.utc)
        await self._profile_repo.upsert(profile)
        return profile

    async def set_media_blur(self, user_id: str, media_url: str, blur: bool) -> Profile:
        profile = await self.get_or_create_profile(user_id)
        found = False
        for m in profile.media:
            if m.url == media_url:
                m.blur = blur
                found = True
                break
        if not found and profile.audio and profile.audio.url == media_url:
            profile.audio.blur = blur
            found = True
        if not found:
            raise MediaNotFoundError(f"No media item with url {media_url}")

        profile.updated_at = datetime.now(timezone.utc)
        await self._profile_repo.upsert(profile)
        return profile

    async def reorder_media(self, user_id: str, ordered_urls: List[str]) -> Profile:
        profile = await self.get_or_create_profile(user_id)
        current_urls = {m.url for m in profile.media}
        
        if set(ordered_urls) != current_urls or len(ordered_urls) != len(profile.media):
            raise ValueError("Payload must contain the exact current URLs for reordering")

        url_to_media = {m.url: m for m in profile.media}
        profile.media = [url_to_media[url] for url in ordered_urls]
        profile.updated_at = datetime.now(timezone.utc)
        await self._profile_repo.upsert(profile)
        return profile