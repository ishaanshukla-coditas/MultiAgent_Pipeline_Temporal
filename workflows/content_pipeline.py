import asyncio
import logging
from datetime import timedelta
from dataclasses import dataclass
from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from agents.research_agent import run_research_agent, ResearchBrief
    from agents.competitor_agent import run_competitor_agent, CompetitorBrief
    from agents.writer_agent import run_writer_agent, ArticleOutput

logger = logging.getLogger(__name__)


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
        # Short 429s (≤60s) are handled inside the activity via sleep+heartbeat.
        # Long 429s (quota exhaustion) surface here as ApplicationError so Temporal
        # retries with backoff — initial_interval gives the first breathing room.
        agent_retry_policy = RetryPolicy(
            initial_interval=timedelta(seconds=30),
            backoff_coefficient=2.0,
            maximum_attempts=3,
            maximum_interval=timedelta(minutes=5),
        )

        # Writer gets more Temporal-level attempts to accommodate the simulated
        # failure scenario (attempt 1 = artificial fail, attempt 2 = real call).
        writer_retry_policy = RetryPolicy(
            initial_interval=timedelta(seconds=30),
            backoff_coefficient=2.0,
            maximum_attempts=5,
            maximum_interval=timedelta(minutes=5),
        )

        # Step 1 — Research + Competitor in parallel
        self._status = "running_research_and_competitor"
        workflow.logger.info("Research and Competitor agents starting in parallel")

        research_brief, competitor_brief = await asyncio.gather(
            workflow.execute_activity(
                run_research_agent,
                input.topic,
                start_to_close_timeout=timedelta(minutes=10),
                heartbeat_timeout=timedelta(seconds=60),
                retry_policy=agent_retry_policy,
            ),
            workflow.execute_activity(
                run_competitor_agent,
                input.topic,
                start_to_close_timeout=timedelta(minutes=10),
                heartbeat_timeout=timedelta(seconds=60),
                retry_policy=agent_retry_policy,
            ),
        )

        workflow.logger.info("Research and Competitor completed")

        # Step 2 — Writer agent (SEO strategy + article in one call)
        self._status = "writing_article"
        workflow.logger.info("Writer Agent starting (SEO + article, 1 LLM call)")

        article: ArticleOutput = await workflow.execute_activity(
            run_writer_agent,
            args=[input.topic, research_brief, competitor_brief, input.simulate_writer_failure],
            start_to_close_timeout=timedelta(minutes=15),
            heartbeat_timeout=timedelta(seconds=60),
            retry_policy=writer_retry_policy,
        )

        self._article = article
        workflow.logger.info(f"Article ready: {article.title}")

        # Step 3 — Human approval gate
        self._status = "waiting_for_approval"
        workflow.logger.info("Waiting for human approval")

        await workflow.wait_condition(
            lambda: self._approved or self._rejection_feedback is not None,
            timeout=timedelta(hours=48),
        )

        self._status = "rejected" if self._rejection_feedback else "completed"
        workflow.logger.info(f"Pipeline finished with status: {self._status}")

        return PipelineResult(
            topic=input.topic,
            title=article.title,
            content=article.content,
            meta_description=article.meta_description,
            word_count=article.word_count,
        )
