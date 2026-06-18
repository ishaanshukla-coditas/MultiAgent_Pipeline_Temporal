import logging
from datetime import timedelta
from dataclasses import dataclass
from temporalio import workflow
from temporalio.common import RetryPolicy
import asyncio
import logging
from datetime import timedelta

with workflow.unsafe.imports_passed_through():
    from agents.research_agent import run_research_agent, ResearchBrief
    from agents.competitor_agent import run_competitor_agent, CompetitorBrief
    from agents.seo_agent import run_seo_agent, SEOBrief
    from agents.writer_agent import run_writer_agent, ArticleOutput

logger = logging.getLogger(__name__)


@dataclass
class PipelineInput:
    topic: str


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
        self._research_done = False
        self._competitor_done = False
        self._seo_brief = None
        self._approved = False
        self._rejection_feedback = None

    # ── SIGNALS ─────────────────────────────────────────

    @workflow.signal
    async def approve_article(self):
        """You send this signal when you approve the article"""
        self._approved = True
        workflow.logger.info("Article approved by user")

    @workflow.signal
    async def reject_article(self, feedback: str):
        """You send this signal to request changes"""
        self._rejection_feedback = feedback
        workflow.logger.info(f"Article rejected: {feedback}")

    # ── QUERIES ─────────────────────────────────────────

    @workflow.query
    def get_status(self) -> str:
        return self._status

    @workflow.query
    def get_seo_brief(self) -> dict:
        return self._seo_brief or {}

    # ── MAIN RUN ────────────────────────────────────────

    @workflow.run
    async def run(self, input: PipelineInput) -> PipelineResult:

        retry_policy = RetryPolicy(
            initial_interval=timedelta(seconds=2),
            backoff_coefficient=2.0,
            maximum_attempts=3,
            maximum_interval=timedelta(seconds=30),
        )

        # ── Step 1: Run Research + Competitor IN PARALLEL ──
        self._status = "running_research_and_competitor"
        workflow.logger.info("Starting Research and Competitor agents in parallel")

        # Start both at the same time
        research_handle = workflow.execute_activity(
            run_research_agent,
            input.topic,
            start_to_close_timeout=timedelta(minutes=5),
            heartbeat_timeout=timedelta(seconds=30),
            retry_policy=retry_policy,
        )

        competitor_handle = workflow.execute_activity(
            run_competitor_agent,
            input.topic,
            start_to_close_timeout=timedelta(minutes=5),
            heartbeat_timeout=timedelta(seconds=30),
            retry_policy=retry_policy,
        )

        
        research_brief, competitor_brief = await asyncio.gather(
            research_handle,
            competitor_handle,
        )

        workflow.logger.info("Both agents completed")
        self._research_done = True
        self._competitor_done = True

        # ── Step 2: Run SEO Agent ─────────────────────────
        self._status = "running_seo_agent"
        workflow.logger.info("Starting SEO agent")

        seo: SEOBrief = await workflow.execute_activity(
            run_seo_agent,
            args=[input.topic, research_brief, competitor_brief],
            start_to_close_timeout=timedelta(minutes=5),
            heartbeat_timeout=timedelta(seconds=30),
            retry_policy=retry_policy,
        )

        self._seo_brief = {
            "primary_keyword": seo.primary_keyword,
            "secondary_keywords": seo.secondary_keywords,
            "search_intent": seo.search_intent,
            "suggested_headings": seo.suggested_headings,
            "meta_description": seo.meta_description,
            "target_word_count": seo.target_word_count,
        }
        workflow.logger.info("SEO agent completed")

        # ── Step 3: Write the article ─────────────────────
        self._status = "writing_article"
        workflow.logger.info("Writer agent starting")

        article: ArticleOutput = await workflow.execute_activity(
            run_writer_agent,
            args=[input.topic, research_brief, competitor_brief, seo],
            start_to_close_timeout=timedelta(minutes=10),
            heartbeat_timeout=timedelta(seconds=60),
            retry_policy=retry_policy,
        )

        # ── Step 4: Pause for human approval ─────────────
        self._status = "waiting_for_approval"
        workflow.logger.info("Waiting for human approval")

        await workflow.wait_condition(
            lambda: self._approved or self._rejection_feedback is not None,
            timeout=timedelta(hours=48),
        )

        if self._rejection_feedback:
            self._status = "rejected"
            workflow.logger.info("Article rejected by user")
        else:
            self._status = "completed"
            workflow.logger.info("Article approved and completed")

        return PipelineResult(
            topic=input.topic,
            title=article.title,
            content=article.content,
            meta_description=article.meta_description,
            word_count=article.word_count,
        )