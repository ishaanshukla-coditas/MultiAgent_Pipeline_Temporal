import logging
from dataclasses import dataclass
from agents.tavily_client import search as tavily_search
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

    snippets, _ = tavily_search(f"{topic} complete guide article blog")
    competitor_results = []
    for block in snippets.split("\n\n"):
        lines = block.strip().splitlines()
        title = lines[0].replace("Title: ", "") if lines else ""
        content = lines[1].replace("Content: ", "") if len(lines) > 1 else ""
        if title:
            competitor_results.append({"title": title, "snippet": content})

    logger.info(f"Found {len(competitor_results)} competitor articles")

    competitor_text = "\n\n".join(
        f"Article: {r['title']}\nContent: {r['snippet']}"
        for r in competitor_results
    )

    prompt = f"""Topic: {topic}

Existing articles about this topic:
{competitor_text}

Return a JSON object with exactly these two keys:
{{
  "content_gaps": "A detailed paragraph describing what ALL these articles are missing — key points not covered, angles ignored, and reader questions left unanswered",
  "opportunities": "3 specific, concrete angles a new article should cover to be clearly better than everything that already exists. Be actionable."
}}"""

    data = await call_llm_json(prompt=prompt, system=_SYSTEM)

    # LLM sometimes returns a list for these fields despite the prompt asking for strings.
    content_gaps = data.get("content_gaps", "")
    opportunities = data.get("opportunities", "")
    if isinstance(content_gaps, list):
        content_gaps = "\n".join(f"- {item}" for item in content_gaps)
    if isinstance(opportunities, list):
        opportunities = "\n".join(f"- {item}" for item in opportunities)

    logger.info("Competitor Agent completed")
    return CompetitorBrief(
        topic=topic,
        content_gaps=content_gaps,
        opportunities=opportunities,
    )
