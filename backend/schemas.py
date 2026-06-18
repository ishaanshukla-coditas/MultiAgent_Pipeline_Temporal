from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class CreatePipelineRequest(BaseModel):
    topic: str


class PipelineResponse(BaseModel):
    pipeline_id: str
    topic: str
    status: str
    temporal_workflow_id: Optional[str] = None
    title: Optional[str] = None
    content: Optional[str] = None
    meta_description: Optional[str] = None
    word_count: Optional[int] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class SignalRequest(BaseModel):
    feedback: Optional[str] = None