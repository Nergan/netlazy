from typing import List
from fastapi import APIRouter, Query
from pydantic import BaseModel
from app.presentation.dependencies import tag_service

router = APIRouter(prefix="/tags", tags=["Tags"])

class TagResponse(BaseModel):
    name: str

@router.get("/search", response_model=List[TagResponse])
async def search_tags(
    q: str = Query("", description="Search text. Empty returns browsable (non-hidden) tags. Prefix a term with '-' to exclude matches.")
):
    if q.strip() == "":
        tags = await tag_service.browse()
    else:
        tags = await tag_service.search(q)
    return [TagResponse(name=t.name) for t in tags]