import asyncio
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.config import settings
from app.presentation.dependencies import security_service

router = APIRouter(prefix="/security", tags=["Security"])

class ChallengeResponse(BaseModel):
    challenge_id: str
    difficulty: int

@router.get("/challenge", response_model=ChallengeResponse)
async def get_challenge():
    """Returns a signed PoW challenge target to be solved by the client."""
    await asyncio.sleep(settings.bot_protection_delay)
    data = await security_service.generate_challenge()
    return ChallengeResponse(**data)

@router.post("/ban/{user_id}")
async def cascade_ban_user(user_id: str):
    """
    Administrative Endpoint: Triggers a cascade ban globally blocking all known IPs 
    and hardware footprints associated with this user ID.
    (In a real production environment, this should be protected by Admin Auth).
    """
    try:
        await security_service.cascade_ban_user(user_id)
        return {"message": f"User {user_id} and all network footprints banned permanently."}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))