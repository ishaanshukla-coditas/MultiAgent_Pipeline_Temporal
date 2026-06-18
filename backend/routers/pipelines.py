from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.schemas import CreatePipelineRequest, PipelineResponse, SignalRequest
from backend.services import pipeline_service

router = APIRouter()


@router.post("/api/pipelines", response_model=PipelineResponse)
async def create_pipeline(
    request: CreatePipelineRequest,
    db: Session = Depends(get_db)
):
    pipeline = await pipeline_service.create_pipeline(request.topic, db)
    return pipeline


@router.get("/api/pipelines", response_model=list[PipelineResponse])
async def list_pipelines(db: Session = Depends(get_db)):
    return await pipeline_service.list_pipelines(db)


@router.get("/api/pipelines/{pipeline_id}", response_model=PipelineResponse)
async def get_pipeline(pipeline_id: str, db: Session = Depends(get_db)):
    pipeline = await pipeline_service.get_pipeline(pipeline_id, db)
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    return pipeline


@router.post("/api/pipelines/{pipeline_id}/approve")
async def approve_pipeline(pipeline_id: str, db: Session = Depends(get_db)):
    success = await pipeline_service.approve_pipeline_article(pipeline_id, db)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to approve")
    return {"success": True, "message": "Article approved"}


@router.post("/api/pipelines/{pipeline_id}/reject")
async def reject_pipeline(
    pipeline_id: str,
    request: SignalRequest,
    db: Session = Depends(get_db)
):
    success = await pipeline_service.reject_pipeline_article(
        pipeline_id,
        request.feedback or "No feedback provided",
        db
    )
    if not success:
        raise HTTPException(status_code=400, detail="Failed to reject")
    return {"success": True, "message": "Article rejected"}