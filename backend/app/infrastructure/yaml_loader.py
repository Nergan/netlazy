from pathlib import Path
from typing import List
import yaml
from app.domain.models import Tag

def load_tags_from_yaml(path: str) -> List[Tag]:
    """Parses tags.yaml into a list of domain Tag objects. Returns an empty
    list if the file doesn't exist, so the app can still boot without a
    registry present (e.g. first-time local setup)."""
    file_path = Path(path)
    if not file_path.exists():
        return []

    with open(file_path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    tags = []
    for entry in raw.get("tags", []):
        tags.append(Tag(
            name=entry["name"],
            category=entry.get("category", "uncategorized"),
            aliases=entry.get("aliases", []),
            hidden=entry.get("hidden", False),
        ))
    return tags