import asyncio
import time
from dotenv import load_dotenv
load_dotenv()

from temporalio.client import Client
from workflows.content_pipeline import ContentPipelineWorkflow, PipelineInput


async def main():
    client = await Client.connect("localhost:7233")

    # Unique ID every run
    workflow_id = f"test-pipeline-{int(time.time())}"

    handle = await client.start_workflow(
        ContentPipelineWorkflow.run,
        PipelineInput(topic="AI Agents in production 2025"),
        id=workflow_id,
        task_queue="content-pipeline-queue",
    )

    print(f"Workflow started: {handle.id}")
    print(f"Check: http://localhost:8233")

    for i in range(60):
        status = await handle.query(ContentPipelineWorkflow.get_status)
        print(f"  Status: {status}")
        if status in ["waiting_for_approval", "completed", "rejected"]:
            print("Reached approval stage — send signal to approve")
            break
        await asyncio.sleep(5)


asyncio.run(main())