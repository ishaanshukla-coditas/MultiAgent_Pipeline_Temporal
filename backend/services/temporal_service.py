import os
from typing import Optional
from temporalio.client import Client
from workflows.content_pipeline import (
    ContentPipelineWorkflow,
    PipelineInput,
)
from queues import ORCHESTRATOR_QUEUE

TEMPORAL_HOST = os.getenv("TEMPORAL_HOST", "localhost:7233")
TASK_QUEUE = os.getenv("TEMPORAL_TASK_QUEUE", ORCHESTRATOR_QUEUE)

_client: Optional[Client] = None


async def get_temporal_client() -> Client:
    global _client
    if _client is None:
        _client = await Client.connect(TEMPORAL_HOST)
    return _client


async def start_pipeline_workflow(
    pipeline_id: str,
    topic: str,
    simulate_writer_failure: bool = False,
) -> str:
    client = await get_temporal_client()
    workflow_id = f"pipeline-{pipeline_id}"

    handle = await client.start_workflow(
        ContentPipelineWorkflow.run,
        PipelineInput(topic=topic, simulate_writer_failure=simulate_writer_failure),
        id=workflow_id,
        task_queue=TASK_QUEUE,
    )
    return handle.result_run_id


_FAILED_EXECUTION_STATES = {"FAILED", "TIMED_OUT", "CANCELED", "TERMINATED"}


async def get_workflow_status(workflow_id: str) -> Optional[str]:
    try:
        client = await get_temporal_client()
        handle = client.get_workflow_handle(workflow_id)

        desc = await handle.describe()
        # desc.status is a proto enum — check its name to avoid import coupling
        execution_state = desc.status.name.upper()
        if any(s in execution_state for s in _FAILED_EXECUTION_STATES):
            return "failed"

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