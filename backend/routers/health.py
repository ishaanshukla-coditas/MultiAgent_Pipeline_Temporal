from fastapi import APIRouter
from backend.services.temporal_service import get_temporal_client

router = APIRouter()


@router.get("/api/health")
async def health():
    try:
        await get_temporal_client()
        return {"status": "ok", "temporal": "connected"}
    except Exception as e:
        return {"status": "error", "temporal": str(e)}