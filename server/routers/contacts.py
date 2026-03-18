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

@router.get("/check", response_model=List[ContactRequestOut])
async def check_requests(
    login: str = Depends(current_user_required)
):
    try:
        requests = await contacts_service.check_requests(login)
        return requests
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))