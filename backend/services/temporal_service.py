import os
from typing import Optional
from temporalio.client import Client
from workflows.content_pipeline import (
    ContentPipelineWorkflow,
    PipelineInput,
)

TEMPORAL_HOST = os.getenv("TEMPORAL_HOST", "localhost:7233")
TASK_QUEUE = os.getenv("TEMPORAL_TASK_QUEUE", "content-pipeline-queue")

_client: Optional[Client] = None


async def get_temporal_client() -> Client:
    global _client
    if _client is None:
        _client = await Client.connect(TEMPORAL_HOST)
    return _client


async def start_pipeline_workflow(pipeline_id: str, topic: str) -> str:
    client = await get_temporal_client()
    workflow_id = f"pipeline-{pipeline_id}"

    handle = await client.start_workflow(
        ContentPipelineWorkflow.run,
        PipelineInput(topic=topic),
        id=workflow_id,
        task_queue=TASK_QUEUE,
    )
    return handle.result_run_id


async def get_workflow_status(workflow_id: str) -> Optional[str]:
    try:
        client = await get_temporal_client()
        handle = client.get_workflow_handle(workflow_id)
        return await handle.query(ContentPipelineWorkflow.get_status)
    except Exception:
        return None


async def get_workflow_article(workflow_id: str) -> Optional[dict]:
    try:
        client = await get_temporal_client()
        handle = client.get_workflow_handle(workflow_id)
        return await handle.query(ContentPipelineWorkflow.get_article)
    except Exception:
        return None


async def approve_pipeline(workflow_id: str) -> bool:
    try:
        client = await get_temporal_client()
        handle = client.get_workflow_handle(workflow_id)
        await handle.signal(ContentPipelineWorkflow.approve_article)
        return True
    except Exception:
        return False


async def reject_pipeline(workflow_id: str, feedback: str) -> bool:
    try:
        client = await get_temporal_client()
        handle = client.get_workflow_handle(workflow_id)
        await handle.signal(ContentPipelineWorkflow.reject_article, feedback)
        return True
    except Exception:
        return False