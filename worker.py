import asyncio
import logging
import os
from dotenv import load_dotenv
load_dotenv()

from temporalio.client import Client
from temporalio.worker import Worker

from workflows.content_pipeline import ContentPipelineWorkflow
from agents.research_agent import run_research_agent
from agents.competitor_agent import run_competitor_agent
from agents.seo_agent import run_seo_agent
from agents.writer_agent import run_writer_agent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TEMPORAL_HOST = os.getenv("TEMPORAL_HOST", "localhost:7233")
TASK_QUEUE = os.getenv("TEMPORAL_TASK_QUEUE", "content-pipeline-queue")


async def main():
    client = await Client.connect(TEMPORAL_HOST)

    worker = Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[ContentPipelineWorkflow],
        activities=[
            run_research_agent,
            run_competitor_agent,
            run_seo_agent,
            run_writer_agent,
        ],
    )

    logger.info(f"Worker started on queue: {TASK_QUEUE}")
    logger.info("Open http://localhost:8233 to see workflows")
    await worker.run()


asyncio.run(main())