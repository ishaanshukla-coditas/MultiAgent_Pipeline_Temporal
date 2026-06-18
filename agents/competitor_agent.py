import logging
from dataclasses import dataclass
from duckduckgo_search import DDGS
from agents.llm_client import call_llm
from temporalio import activity

logger = logging.getLogger(__name__)

@dataclass
class CompetitorBrief:
    topic: str
    content_gaps: str
    opportunities: str

@activity.defn
async def run_competitor_agent(topic: str) -> CompetitorBrief:
    """
    Searches for existing content on the topic,
    identifies what competitors are missing,
    and returns opportunities to write better content.

    Step 1: Search for existing articles on topic
    Step 2: Ask Gemma what gaps exist
    Step 3: Return structured competitor brief
    """

    logger.info(f"Competitor Agent starting for topic: {topic}")

    # Step 1 — Search for existing content
    logger.info("Searching for existing competitor content...")
    competitor_results = []

    with DDGS() as ddgs:
        results = ddgs.text(
            f"{topic} complete guide article blog",
            max_results=5
        )
        for r in results:
            competitor_results.append({
                "title": r["title"],
                "snippet": r["body"],
                "url": r["href"]
            })

    logger.info(f"Found {len(competitor_results)} competitor articles")

    # Step 2 — Ask Gemma to identify gaps
    competitor_text = "\n\n".join([
        f"Article: {r['title']}\nContent: {r['snippet']}"
        for r in competitor_results
    ])

    prompt = f"""
    Topic: {topic}

    Here are existing articles already written about this topic:
    {competitor_text}

    Analyze these articles and answer:
    1. What key points are ALL these articles missing?
    2. What angles are not being covered?
    3. What questions do readers likely have that are not answered?
    4. What would make a NEW article on this topic stand out?

    Be specific and actionable.
    """

    system = """You are a content strategist and competitor analyst.
    Your job is to find gaps in existing content
    and identify opportunities to write better articles
    that outperform what already exists."""

    logger.info("Calling Gemma to identify content gaps...")
    analysis = await call_llm(prompt=prompt, system=system)

    # Step 3 — Ask Gemma for specific opportunities
    opportunity_prompt = f"""
    Based on this competitor analysis for the topic "{topic}":
    {analysis}

    List 3 specific angles or unique perspectives 
    that a new article should cover to be better 
    than everything that already exists.
    Be concrete and specific.
    """

    opportunities = await call_llm(
        prompt=opportunity_prompt,
        system=system
    )

    brief = CompetitorBrief(
        topic=topic,
        content_gaps=analysis,
        opportunities=opportunities
    )

    logger.info("Competitor Agent completed successfully")
    return brief