import logging
from dataclasses import dataclass
from agents.llm_client import call_llm
from agents.research_agent import ResearchBrief
from agents.competitor_agent import CompetitorBrief
from temporalio import activity

logger = logging.getLogger(__name__)


@dataclass
class SEOBrief:
    primary_keyword: str
    secondary_keywords: list[str]
    search_intent: str
    suggested_headings: list[str]
    meta_description: str
    target_word_count: int

@activity.defn
async def run_seo_agent(
    topic: str,
    research: ResearchBrief,
    competitor: CompetitorBrief,
) -> SEOBrief:
    """
    Automatically generates SEO brief using
    research and competitor data.

    Step 1: Generate keywords from research
    Step 2: Generate headings from competitor gaps
    Step 3: Generate meta description
    Step 4: Return structured SEO brief
    """

    logger.info(f"SEO Agent starting for topic: {topic}")

    # Step 1 — Generate keywords
    keyword_prompt = f"""
    Topic: {topic}

    Based on this research:
    {research.key_facts[:500]}

    And these competitor gaps:
    {competitor.content_gaps[:300]}

    Generate SEO keywords in this exact format:
    PRIMARY: [one main keyword phrase]
    SECONDARY: [keyword1], [keyword2], [keyword3]
    INTENT: [informational OR commercial OR navigational]

    Return only the three lines above, nothing else.
    """

    keyword_response = await call_llm(
        prompt=keyword_prompt,
        system="You are an AI SEO expert. Return only the requested format."
    )

    # Parse keyword response
    primary_keyword = topic
    secondary_keywords = []
    search_intent = "informational"

    for line in keyword_response.strip().split("\n"):
        if line.startswith("PRIMARY:"):
            primary_keyword = line.replace("PRIMARY:", "").strip()
        elif line.startswith("SECONDARY:"):
            raw = line.replace("SECONDARY:", "").strip()
            secondary_keywords = [k.strip() for k in raw.split(",")]
        elif line.startswith("INTENT:"):
            search_intent = line.replace("INTENT:", "").strip()

    logger.info(f"Keywords generated: {primary_keyword}")

    # Step 2 — Generate headings
    headings_prompt = f"""
    Topic: {topic}
    Primary keyword: {primary_keyword}

    Competitor gaps to address:
    {competitor.opportunities[:400]}

    Generate exactly 5 article headings that:
    - Cover the topic comprehensively
    - Address the competitor gaps
    - Are clear and descriptive
    - Work well for AI search citation

    Return only 5 headings, one per line, no numbering.
    """

    headings_response = await call_llm(
        prompt=headings_prompt,
        system="You are an AI SEO expert. Return only the headings."
    )

    suggested_headings = [
        h.strip() for h in headings_response.strip().split("\n")
        if h.strip()
    ][:5]

    logger.info(f"Generated {len(suggested_headings)} headings")

    # Step 3 — Generate meta description
    meta_prompt = f"""
    Topic: {topic}
    Primary keyword: {primary_keyword}

    Write ONE meta description that:
    - Is under 155 characters
    - Includes the primary keyword
    - Describes what the article covers
    - Makes people want to click

    Return only the meta description, nothing else.
    """

    meta_description = await call_llm(
        prompt=meta_prompt,
        system="You are an AI SEO expert. Return only the meta description."
    )
    meta_description = meta_description.strip()[:155]

    logger.info("SEO Agent completed successfully")

    return SEOBrief(
        primary_keyword=primary_keyword,
        secondary_keywords=secondary_keywords,
        search_intent=search_intent,
        suggested_headings=suggested_headings,
        meta_description=meta_description,
        target_word_count=800,
    )