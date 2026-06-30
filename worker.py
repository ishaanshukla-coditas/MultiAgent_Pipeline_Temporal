import asyncio
import logging
import os
from dotenv import load_dotenv
load_dotenv()

from temporalio.client import Client
from temporalio.worker import Worker

from queues import ORCHESTRATOR_QUEUE, RESEARCH_QUEUE, COMPETITOR_QUEUE, WRITER_QUEUE, NOTIFICATION_QUEUE
from workflows.content_pipeline import ContentPipelineWorkflow
from agents.research_agent import (
    fetch_industry_trends,
    fetch_key_facts,
    fetch_recent_news,
    aggregate_research,
)
from agents.competitor_agent import run_competitor_agent
from agents.writer_agent import run_writer_agent
from agents.event_publisher import publish_pipeline_event

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TEMPORAL_HOST = os.getenv("TEMPORAL_HOST", "localhost:7233")

# Role → (task_queue, workflows, activities)
ROLES = {
    "orchestrator": {
        "task_queue": ORCHESTRATOR_QUEUE,
        "workflows": [ContentPipelineWorkflow],
        "activities": [],
    },
    "research": {
        "task_queue": RESEARCH_QUEUE,
        "workflows": [],
        "activities": [fetch_industry_trends, fetch_key_facts, fetch_recent_news, aggregate_research],
    },
    "competitor": {
        "task_queue": COMPETITOR_QUEUE,
        "workflows": [],
        "activities": [run_competitor_agent],
    },
    "writer": {
        "task_queue": WRITER_QUEUE,
        "workflows": [],
        "activities": [run_writer_agent],
    },
    "notification": {
        "task_queue": NOTIFICATION_QUEUE,
        "workflows": [],
        "activities": [publish_pipeline_event],
    },
}


async def main():
    role = os.getenv("WORKER_ROLE", "orchestrator")
    if role not in ROLES:
        raise ValueError(f"Unknown WORKER_ROLE={role!r}. Valid roles: {list(ROLES)}")

    cfg = ROLES[role]
    client = await Client.connect(TEMPORAL_HOST)

    worker = Worker(
        client,
        task_queue=cfg["task_queue"],
        workflows=cfg["workflows"],
        activities=cfg["activities"],
    )

    logger.info(f"Worker [{role}] started on queue: {cfg['task_queue']}")
    await worker.run()


asyncio.run(main())
