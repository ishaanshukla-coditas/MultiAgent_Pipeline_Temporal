import logging
from dataclasses import dataclass
from agents.llm_client import call_llm_json
from agents.research_agent import ResearchBrief
from agents.competitor_agent import CompetitorBrief
from temporalio import activity
from temporalio.exceptions import ApplicationError

logger = logging.getLogger(__name__)

MIN_WORD_COUNT = 750
MAX_WRITE_ATTEMPTS = 3


@dataclass
class ArticleOutput:
    topic: str
    title: str
    meta_description: str
    content: str
    word_count: int


_SYSTEM = (
    "You are an expert content writer and SEO strategist. "
    "You write articles that rank in both traditional search and AI-generated answers. "
    "Use clear extractable content blocks, direct answers, and specific facts. "
    "Always respond with valid JSON only."
)


def _build_prompt(
    topic: str,
    research: ResearchBrief,
    competitor: CompetitorBrief,
    feedback: str | None,
) -> str:
    feedback_section = ""
    if feedback:
        feedback_section = f"""
REVISION FEEDBACK FROM EDITOR:
{feedback}

Address every point in the feedback. The previous version was rejected — this rewrite must fix those issues.
"""

    return f"""Topic: {topic}

RESEARCH FINDINGS:
{research.key_facts}

COMPETITOR CONTENT GAPS:
{competitor.content_gaps}

UNIQUE ANGLES TO COVER:
{competitor.opportunities}
{feedback_section}
You are both the SEO strategist and the article writer. Produce both in a single response.

Return a JSON object with exactly these keys:
{{
  "primary_keyword": "the main keyword phrase to target (2-4 words)",
  "meta_description": "SEO meta description under 155 characters that includes the primary keyword and makes people want to click",
  "title": "compelling article title under 60 characters that includes the primary keyword naturally",
  "content": "the full article in Markdown — YOU MUST WRITE AT LEAST 800 WORDS. Use 6 sections with ## headings, 3-4 paragraphs per section, specific facts from the research, and a strong introduction and conclusion. Do not stop early."
}}

Content requirements — ALL are mandatory:
- Minimum 800 words. Count them. If your draft is under 800 words, keep writing.
- 6 sections with ## headings, each directly answering a specific reader question
- Address every competitor gap identified above
- At least 5 specific statistics or concrete facts from the research
- Clear definitions for key terms in the introduction
- Strong actionable conclusion with 3-5 key takeaways"""


@activity.defn
async def run_writer_agent(
    topic: str,
    research: ResearchBrief,
    competitor: CompetitorBrief,
    simulate_failure: bool = False,
    feedback: str | None = None,
) -> ArticleOutput:
    attempt = activity.info().attempt
    logger.info(f"Writer Agent starting for topic: {topic} (attempt {attempt}, feedback={'yes' if feedback else 'no'})")

    if simulate_failure and attempt == 1:
        logger.warning("Simulated failure on attempt 1 — Temporal will retry this activity")
        raise ApplicationError(
            "Simulated writer failure on attempt 1",
            non_retryable=False,
        )

    def _to_str(val, sep="\n") -> str:
        if isinstance(val, list):
            return sep.join(str(v) for v in val)
        return str(val) if val else ""

    prompt = _build_prompt(topic, research, competitor, feedback)

    # Retry the LLM call internally if the article comes back too short.
    # This is a fast in-activity retry (seconds), not a full Temporal retry (minutes).
    for write_attempt in range(1, MAX_WRITE_ATTEMPTS + 1):
        data = await call_llm_json(prompt=prompt, system=_SYSTEM)
        content = _to_str(data.get("content", ""))
        word_count = len(content.split())

        logger.info(f"Write attempt {write_attempt}: {word_count} words")

        if word_count >= MIN_WORD_COUNT:
            break

        if write_attempt < MAX_WRITE_ATTEMPTS:
            logger.warning(
                f"Article too short ({word_count} words, min {MIN_WORD_COUNT}) "
                f"— retrying LLM call ({write_attempt}/{MAX_WRITE_ATTEMPTS})"
            )
            # Strengthen the prompt for the next attempt
            prompt += f"\n\nPREVIOUS ATTEMPT WAS {word_count} WORDS — TOO SHORT. Write at least 800 words this time. Do not truncate."

    logger.info(f"Writer Agent completed. Title: {data.get('title', '')} | Words: {word_count}")

    return ArticleOutput(
        topic=topic,
        title=_to_str(data.get("title", topic)),
        meta_description=_to_str(data.get("meta_description", "")),
        content=content,
        word_count=word_count,
    )
