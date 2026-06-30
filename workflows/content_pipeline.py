import asyncio
import logging
from datetime import timedelta
from dataclasses import dataclass
from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from agents.research_agent import (
        fetch_industry_trends,
        fetch_key_facts,
        fetch_recent_news,
        aggregate_research,
        ResearchBrief,
    )
    from agents.competitor_agent import run_competitor_agent, CompetitorBrief
    from agents.writer_agent import run_writer_agent, ArticleOutput
    from agents.event_publisher import publish_pipeline_event
    from queues import RESEARCH_QUEUE, COMPETITOR_QUEUE, WRITER_QUEUE, NOTIFICATION_QUEUE

logger = logging.getLogger(__name__)

MAX_REWRITES = 3


@dataclass
class PipelineInput:
    topic: str
    simulate_writer_failure: bool = False


@dataclass
class PipelineResult:
    topic: str
    title: str
    content: str
    meta_description: str
    word_count: int


@workflow.defn
class ContentPipelineWorkflow:

    def __init__(self):
        self._status = "started"
        self._article: ArticleOutput | None = None
        self._approved = False
        self._rejection_feedback: str | None = None

    # ── Signals ──────────────────────────────────────────────

    @workflow.signal
    async def approve_article(self):
        self._approved = True
        workflow.logger.info("Article approved")

    @workflow.signal
    async def reject_article(self, feedback: str):
        self._rejection_feedback = feedback
        workflow.logger.info(f"Article rejected: {feedback}")

    # ── Queries ───────────────────────────────────────────────

    @workflow.query
    def get_status(self) -> str:
        return self._status

    @workflow.query
    def get_article(self) -> dict:
        if self._article is None:
            return {}
        return {
            "title": self._article.title,
            "content": self._article.content,
            "meta_description": self._article.meta_description,
            "word_count": self._article.word_count,
        }

    # ── Main run ──────────────────────────────────────────────

    @workflow.run
    async def run(self, input: PipelineInput) -> PipelineResult:
        agent_retry_policy = RetryPolicy(
            initial_interval=timedelta(seconds=30),
            backoff_coefficient=2.0,
            maximum_attempts=3,
            maximum_interval=timedelta(minutes=5),
        )

        writer_retry_policy = RetryPolicy(
            initial_interval=timedelta(seconds=30),
            backoff_coefficient=2.0,
            maximum_attempts=5,
            maximum_interval=timedelta(minutes=5),
        )

        _notify_opts = dict(
            task_queue=NOTIFICATION_QUEUE,
            start_to_close_timeout=timedelta(seconds=30),
        )

        # Step 1 — Research (3 parallel fetches) + Competitor, all in parallel
        self._status = "running_research_and_competitor"
        workflow.logger.info("Research (fan-out) and Competitor starting in parallel")

        _activity_opts = dict(
            task_queue=RESEARCH_QUEUE,
            start_to_close_timeout=timedelta(minutes=5),
            heartbeat_timeout=timedelta(seconds=60),
            retry_policy=agent_retry_policy,
        )

        trends_text, facts_text, news_raw, competitor_brief = await asyncio.gather(
            workflow.execute_activity(fetch_industry_trends, input.topic, **_activity_opts),
            workflow.execute_activity(fetch_key_facts, input.topic, **_activity_opts),
            workflow.execute_activity(fetch_recent_news, input.topic, **_activity_opts),
            workflow.execute_activity(
                run_competitor_agent,
                input.topic,
                task_queue=COMPETITOR_QUEUE,
                start_to_close_timeout=timedelta(minutes=10),
                heartbeat_timeout=timedelta(seconds=60),
                retry_policy=agent_retry_policy,
            ),
        )

        workflow.logger.info("Research fetches and Competitor completed — aggregating research")

        # Step 1b — Aggregate the 3 research results into one brief
        research_brief: ResearchBrief = await workflow.execute_activity(
            aggregate_research,
            args=[input.topic, trends_text, facts_text, news_raw],
            task_queue=RESEARCH_QUEUE,
            start_to_close_timeout=timedelta(minutes=10),
            heartbeat_timeout=timedelta(seconds=60),
            retry_policy=agent_retry_policy,
        )

        workflow.logger.info("Research aggregation completed")

        # Step 2 — Write article (loops on rejection, up to MAX_REWRITES times)
        feedback: str | None = None
        rewrite_count = 0

        while True:
            if feedback:
                self._status = "rewriting_article"
                workflow.logger.info(f"Rewriting article (attempt {rewrite_count}/{MAX_REWRITES})")
            else:
                self._status = "writing_article"
                workflow.logger.info("Writer Agent starting")

            article: ArticleOutput = await workflow.execute_activity(
                run_writer_agent,
                args=[input.topic, research_brief, competitor_brief, input.simulate_writer_failure, feedback],
                task_queue=WRITER_QUEUE,
                start_to_close_timeout=timedelta(minutes=15),
                heartbeat_timeout=timedelta(seconds=60),
                retry_policy=writer_retry_policy,
            )

            self._article = article
            workflow.logger.info(f"Article ready: {article.title} ({article.word_count} words)")

            # Notify RabbitMQ — fire and forget
            await workflow.execute_activity(
                publish_pipeline_event,
                args=["article.ready", {"topic": input.topic, "title": article.title}],
                **_notify_opts,
            )

            # Wait for human decision (up to 48 hours)
            self._status = "waiting_for_approval"
            self._approved = False
            self._rejection_feedback = None
            workflow.logger.info("Waiting for human approval")

            await workflow.wait_condition(
                lambda: self._approved or self._rejection_feedback is not None,
                timeout=timedelta(hours=48),
            )

            if self._approved:
                # Approved — publish and exit loop
                await workflow.execute_activity(
                    publish_pipeline_event,
                    args=["article.approved", {"topic": input.topic, "title": article.title}],
                    **_notify_opts,
                )
                self._status = "completed"
                workflow.logger.info("Pipeline completed — article approved")
                break

            # Rejected — check if we've hit the rewrite limit
            rewrite_count += 1
            feedback = self._rejection_feedback
            workflow.logger.info(f"Article rejected (rewrite {rewrite_count}/{MAX_REWRITES}): {feedback}")

            if rewrite_count >= MAX_REWRITES:
                # Max rewrites reached — end the workflow as rejected
                await workflow.execute_activity(
                    publish_pipeline_event,
                    args=["article.rejected", {
                        "topic": input.topic,
                        "title": article.title,
                        "feedback": feedback,
                    }],
                    **_notify_opts,
                )
                self._status = "rejected"
                workflow.logger.info(f"Pipeline rejected after {MAX_REWRITES} rewrites")
                break

            # Publish rejected event and loop back to rewrite
            await workflow.execute_activity(
                publish_pipeline_event,
                args=["article.rejected", {
                    "topic": input.topic,
                    "title": article.title,
                    "feedback": feedback,
                }],
                **_notify_opts,
            )

        return PipelineResult(
            topic=input.topic,
            title=article.title,
            content=article.content,
            meta_description=article.meta_description,
            word_count=article.word_count,
        )
