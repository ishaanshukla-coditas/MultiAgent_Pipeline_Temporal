import uuid
from sqlalchemy.orm import Session
from backend.models import Pipeline
from backend.services.temporal_service import (
    start_pipeline_workflow,
    get_workflow_status,
    get_workflow_article,
    approve_pipeline,
    reject_pipeline,
)


ARTICLE_STATUSES = {"waiting_for_approval", "completed", "rejected"}
TERMINAL_STATUSES = {"completed", "rejected", "failed"}


async def _sync_article(pipeline: Pipeline, db: Session) -> None:
    """Fetch article content from Temporal and persist it if not already saved."""
    if pipeline.status in ARTICLE_STATUSES and not pipeline.title:
        article = await get_workflow_article(pipeline.temporal_workflow_id)
        if article and article.get("title"):
            pipeline.title = article["title"]
            pipeline.content = article["content"]
            pipeline.meta_description = article["meta_description"]
            pipeline.word_count = article["word_count"]
            db.commit()
            db.refresh(pipeline)


async def create_pipeline(
    topic: str,
    db: Session,
    simulate_writer_failure: bool = False,
) -> Pipeline:
    pipeline_id = str(uuid.uuid4())[:8].upper()

    pipeline = Pipeline(
        pipeline_id=pipeline_id,
        topic=topic,
        status="started",
        simulate_writer_failure=simulate_writer_failure,
    )
    db.add(pipeline)
    db.commit()
    db.refresh(pipeline)

    run_id = await start_pipeline_workflow(pipeline_id, topic, simulate_writer_failure)

    pipeline.temporal_workflow_id = f"pipeline-{pipeline_id}"
    pipeline.temporal_run_id = run_id
    db.commit()
    db.refresh(pipeline)

    return pipeline


async def list_pipelines(db: Session) -> list[Pipeline]:
    pipelines = db.query(Pipeline).order_by(
        Pipeline.created_at.desc()
    ).all()

    for pipeline in pipelines:
        if pipeline.status not in TERMINAL_STATUSES:
            live_status = await get_workflow_status(
                pipeline.temporal_workflow_id
            )
            if live_status and live_status != pipeline.status:
                pipeline.status = live_status
                db.commit()

    return pipelines


async def get_pipeline(pipeline_id: str, db: Session) -> Pipeline:
    pipeline = db.query(Pipeline).filter(
        Pipeline.pipeline_id == pipeline_id
    ).first()

    if not pipeline:
        return None

    if pipeline.status not in TERMINAL_STATUSES:
        live_status = await get_workflow_status(
            pipeline.temporal_workflow_id
        )
        if live_status:
            pipeline.status = live_status
            db.commit()
            db.refresh(pipeline)

    await _sync_article(pipeline, db)
    return pipeline


async def approve_pipeline_article(pipeline_id: str, db: Session) -> bool:
    pipeline = db.query(Pipeline).filter(
        Pipeline.pipeline_id == pipeline_id
    ).first()

    if not pipeline:
        return False

    success = await approve_pipeline(pipeline.temporal_workflow_id)
    if success:
        pipeline.status = "completed"
        db.commit()

    return success


async def reject_pipeline_article(
    pipeline_id: str,
    feedback: str,
    db: Session
) -> bool:
    pipeline = db.query(Pipeline).filter(
        Pipeline.pipeline_id == pipeline_id
    ).first()

    if not pipeline:
        return False

    success = await reject_pipeline(pipeline.temporal_workflow_id, feedback)
    if success:
        pipeline.status = "rejected"
        db.commit()

    return success