import logging
from dataclasses import dataclass
from duckduckgo_search import DDGS
from agents.llm_client import call_llm
from temporalio import activity

logger = logging.getLogger(__name__)


@dataclass
class ResearchBrief:
    topic: str
    key_facts: str
    sources: list[str]

@activity.defn
async def run_research_agent(topic: str) -> ResearchBrief:
    """
    Searches the web for the topic and returns a research brief.

    Step 1: Search DuckDuckGo for real articles
    Step 2: Pass results to Gemma for summarization
    Step 3: Return structured research brief
    """

    logger.info(f"Research Agent starting for topic: {topic}")

    # Step 1 — Search the web
    logger.info("Searching DuckDuckGo...")
    search_results = []

    with DDGS() as ddgs:
        results = ddgs.text(
            f"{topic} latest trends facts 2026",
            max_results=5
        )
        for r in results:
            search_results.append({
                "title": r["title"],
                "snippet": r["body"],
                "url": r["href"]
            })

    logger.info(f"Found {len(search_results)} search results")

    # Step 2 — Ask Gemma to summarize
    search_text = "\n\n".join([
        f"Title: {r['title']}\nContent: {r['snippet']}"
        for r in search_results
    ])

    prompt = f"""
    Topic: {topic}

    Here are recent articles and information about this topic:
    {search_text}

    Please summarize the key facts, trends, and insights 
    about this topic in 3-5 paragraphs. 
    Focus on the most important and interesting points.
    Be factual and informative.
    """

    system = """You are a research analyst. 
    Your job is to summarize web search results 
    into clear, factual research briefs.
    Always be accurate and cite specific facts."""

    logger.info("Calling Gemma to summarize research...")
    summary = await call_llm(prompt=prompt, system=system)

    # Step 3 — Return structured brief
    sources = [r["url"] for r in search_results]

    brief = ResearchBrief(
        topic=topic,
        key_facts=summary,
        sources=sources
    )

    logger.info("Research Agent completed successfully")
    return brief