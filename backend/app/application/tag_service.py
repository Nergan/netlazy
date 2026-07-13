from typing import List
from app.domain.models import Tag
from app.domain.repository import TagRepository
from app.infrastructure.yaml_loader import load_tags_from_yaml

class TagService:
    def __init__(self, tag_repo: TagRepository):
        self._tag_repo = tag_repo

    async def sync_from_yaml(self, yaml_path: str) -> int:
        """Loads tags.yaml and syncs the registry (upsert + stale cleanup on
        both the tags collection and existing profile documents). Returns the
        number of tags synced. No-op if the file is missing or empty."""
        tags = load_tags_from_yaml(yaml_path)
        if tags:
            await self._tag_repo.sync(tags)
        return len(tags)

    async def browse(self) -> List[Tag]:
        return await self._tag_repo.list_visible()

    async def search(self, query: str) -> List[Tag]:
        return await self._tag_repo.search(query)