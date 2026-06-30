import logging
from dataclasses import dataclass
from agents.tavily_client import search as tavily_search
from agents.llm_client import call_llm
from temporalio import activity

logger = logging.getLogger(__name__)


@dataclass
class ResearchBrief:
    topic: str
    key_facts: str
    sources: str  # comma-joined URLs — avoids generic list[str] decode issues in Python 3.14


# ── Sub-activities (run in parallel) ──────────────────────────────────────────

@activity.defn
async def fetch_industry_trends(topic: str) -> str:
    """Tavily search focused on market trends and industry direction."""
    logger.info(f"[research] fetch_industry_trends: {topic}")
    snippets, _ = tavily_search(f"{topic} industry trends market size 2026")
    return snippets


@activity.defn
async def fetch_key_facts(topic: str) -> str:
    """Tavily search focused on statistics, data, and hard facts."""
    logger.info(f"[research] fetch_key_facts: {topic}")
    snippets, _ = tavily_search(f"{topic} statistics data facts research")
    return snippets


@activity.defn
async def fetch_recent_news(topic: str) -> str:
    """Tavily search focused on latest news and developments."""
    logger.info(f"[research] fetch_recent_news: {topic}")
    snippets, sources = tavily_search(f"{topic} latest news developments 2026")
    # sources tagged here because aggregate_research uses this activity's URLs
    return f"__SOURCES__{sources}__END_SOURCES__\n{snippets}"


@activity.defn
async def aggregate_research(
    topic: str,
    trends_text: str,
    facts_text: str,
    news_raw: str,
) -> ResearchBrief:
    """Merge the three search result sets into a single ResearchBrief via one LLM call."""
    logger.info(f"[research] aggregate_research: {topic}")

    # Extract sources embedded by fetch_recent_news
    sources = ""
    news_text = news_raw
    if news_raw.startswith("__SOURCES__"):
        end = news_raw.index("__END_SOURCES__")
        sources = news_raw[len("__SOURCES__"):end]
        news_text = news_raw[end + len("__END_SOURCES__\n"):]

    prompt = f"""
Topic: {topic}

You have three sets of research gathered in parallel. Synthesize them into a
cohesive 3-5 paragraph research brief covering the most important facts,
trends, and recent developments. Be factual and specific.

## Industry Trends
{trends_text}

## Key Facts & Statistics
{facts_text}

## Recent News
{news_text}
"""

    system = """You are a research analyst. Synthesize multiple web search result
sets into a clear, factual research brief. Highlight the most important
insights, avoid repetition, and cite specific data points where possible."""

    summary = await call_llm(prompt=prompt, system=system)
    logger.info("[research] aggregate_research completed")

    return ResearchBrief(topic=topic, key_facts=summary, sources=sources)
