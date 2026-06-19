import logging
from dataclasses import dataclass
from agents.llm_client import call_llm_json
from agents.research_agent import ResearchBrief
from agents.competitor_agent import CompetitorBrief
from temporalio import activity
from temporalio.exceptions import ApplicationError

logger = logging.getLogger(__name__)


@dataclass
class ArticleOutput:
    topic: str
    title: str
    meta_description: str
    content: str
    word_count: int


# Stable system prompt — same text for every write request so provider-side
# prefix caching applies. All dynamic data goes in the user prompt only.
_SYSTEM = (
    "You are an expert content writer and SEO strategist. "
    "You write articles that rank in both traditional search and AI-generated answers. "
    "Use clear extractable content blocks, direct answers, and specific facts. "
    "Always respond with valid JSON only."
)


@activity.defn
async def run_writer_agent(
    topic: str,
    research: ResearchBrief,
    competitor: CompetitorBrief,
    simulate_failure: bool = False,
) -> ArticleOutput:
    """
    Generates SEO strategy + article title + full article body in a single
    structured JSON call. Replaces the previous separate SEO agent (3 calls)
    and writer agent (2 calls) — now 1 call total.
    """
    attempt = activity.info().attempt
    logger.info(f"Writer Agent starting for topic: {topic} (attempt {attempt})")

    # Simulated failure on first attempt — Temporal retries only this activity;
    # research and competitor results are replayed from event history, not re-run.
    if simulate_failure and attempt == 1:
        logger.warning("Simulated failure on attempt 1 — Temporal will retry this activity")
        raise ApplicationError(
            "Simulated writer failure on attempt 1",
            non_retryable=False,
        )

    prompt = f"""Topic: {topic}

RESEARCH FINDINGS:
{research.key_facts}

COMPETITOR CONTENT GAPS:
{competitor.content_gaps}

UNIQUE ANGLES TO COVER:
{competitor.opportunities}

You are both the SEO strategist and the article writer. Produce both in a single response.

Return a JSON object with exactly these keys:
{{
  "primary_keyword": "the main keyword phrase to target (2-4 words)",
  "meta_description": "SEO meta description under 155 characters that includes the primary keyword and makes people want to click",
  "title": "compelling article title under 60 characters that includes the primary keyword naturally",
  "content": "the full article in Markdown — minimum 800 words, with ## headings (5-6 sections), short paragraphs (2-3 sentences), specific facts from the research, and a strong introduction and conclusion"
}}

Content requirements:
- Each ## section directly answers a specific reader question
- Address every competitor gap identified above
- Include at least 3 specific statistics or concrete facts from the research
- Clear definitions for key terms
- Short paragraphs — maximum 3 sentences each
- Strong actionable conclusion with key takeaways"""

    data = await call_llm_json(prompt=prompt, system=_SYSTEM)

    # Coerce any fields the LLM may have returned as lists instead of strings
    def _to_str(val, sep="\n") -> str:
        if isinstance(val, list):
            return sep.join(str(v) for v in val)
        return str(val) if val else ""

    content = _to_str(data.get("content", ""))
    word_count = len(content.split())

    logger.info(
        f"Writer Agent completed (1 LLM call, was 5). "
        f"Title: {data.get('title', '')} | Words: {word_count}"
    )

    return ArticleOutput(
        topic=topic,
        title=_to_str(data.get("title", topic)),
        meta_description=_to_str(data.get("meta_description", "")),
        content=content,
        word_count=word_count,
    )
