from typing import List
from fastapi import APIRouter, HTTPException, status, Depends
from models.request import ContactRequestInput, ContactRequestOut
from services import contacts as contacts_service
from core.deps import current_user_required

router = APIRouter()


@router.post("/request", status_code=status.HTTP_202_ACCEPTED)
async def send_contact_request(
    request_data: ContactRequestInput,
    login: str = Depends(current_user_required)
):
    """
    Отправить запрос на обмен контактами другому пользователю.

    - **swap**: предложение обменяться контактами (взаимный обмен)
    - **give**: отправить свои контакты (требуется поле `data`)
    - **get**: запросить публичные контакты
    """
    try:
        await contacts_service.send_request(
            from_login=login,
            target_login=request_data.target_id,
            req_type=request_data.type,
            request_id=request_data.request_id,
            data=request_data.data
        )
        return {"status": "request sent"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/requests", response_model=List[ContactRequestOut])
async def get_requests(
    login: str = Depends(current_user_required)
):
    """
    Получить список всех входящих запросов (без удаления).
    """
    try:
        requests = await contacts_service.get_pending_requests(login)
        return requests
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/requests/{request_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_request(
    request_id: str,
    login: str = Depends(current_user_required)
):
    """
    Удалить конкретный входящий запрос по его request_id.
    """
    try:
        deleted = await contacts_service.delete_request(login, request_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Request not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/check", response_model=List[ContactRequestOut])
async def check_requests(
    login: str = Depends(current_user_required)
):
    """
    Устаревший эндпоинт, возвращает список запросов (как GET /requests).
    """
    try:
        requests = await contacts_service.get_pending_requests(login)
        return requests
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))