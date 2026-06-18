import logging
from dataclasses import dataclass
from duckduckgo_search import DDGS
from agents.llm_client import call_llm_json
from temporalio import activity

logger = logging.getLogger(__name__)


@dataclass
class CompetitorBrief:
    topic: str
    content_gaps: str
    opportunities: str


# Stable system prompt — no dynamic data so provider-side prefix caching applies
# across all competitor agent calls regardless of topic.
_SYSTEM = (
    "You are a content strategist and competitor analyst. "
    "Analyze existing content to find gaps and opportunities for better articles. "
    "Always respond with valid JSON only."
)


@activity.defn
async def run_competitor_agent(topic: str) -> CompetitorBrief:
    """
    Searches for existing content on the topic, identifies gaps and opportunities.
    Single structured JSON call replaces the previous 2-call approach.
    """
    logger.info(f"Competitor Agent starting for topic: {topic}")

    competitor_results = []
    with DDGS() as ddgs:
        results = ddgs.text(f"{topic} complete guide article blog", max_results=5)
        for r in results:
            competitor_results.append({
                "title": r["title"],
                "snippet": r["body"],
            })

    logger.info(f"Found {len(competitor_results)} competitor articles")

    competitor_text = "\n\n".join([
        f"Article: {r['title']}\nContent: {r['snippet']}"
        for r in competitor_results
    ])

    # Single JSON call replaces the old analysis call + opportunities call
    prompt = f"""Topic: {topic}

Existing articles about this topic:
{competitor_text}

Return a JSON object with exactly these two keys:
{{
  "content_gaps": "A detailed paragraph describing what ALL these articles are missing — key points not covered, angles ignored, and reader questions left unanswered",
  "opportunities": "3 specific, concrete angles a new article should cover to be clearly better than everything that already exists. Be actionable."
}}"""

    data = await call_llm_json(prompt=prompt, system=_SYSTEM)

    logger.info("Competitor Agent completed (1 LLM call, was 2)")
    return CompetitorBrief(
        topic=topic,
        content_gaps=data.get("content_gaps", ""),
        opportunities=data.get("opportunities", ""),
    )
