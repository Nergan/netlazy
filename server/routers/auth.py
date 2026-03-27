from fastapi import APIRouter, HTTPException, Body, Depends
from services import auth as auth_service
from core.deps import current_user_required

router = APIRouter()


@router.post("/register")
async def register(
    login: str = Body(...),
    public_key: str = Body(...),
    key_algorithm: str = Body("Ed25519")
):
    """
    Регистрация нового пользователя с публичным ключом.
    """
    try:
        await auth_service.register_user(login, public_key, key_algorithm)
        return {"status": "registered", "login": login}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/change-key")
async def change_key(
    new_public_key: str = Body(...),
    new_algorithm: str = Body("Ed25519"),
    login: str = Depends(current_user_required)
):
    """
    Смена ключа (требуется подпись старым ключом).
    """
    try:
        await auth_service.change_key(login, new_public_key, new_algorithm)
        return {"status": "key changed"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))