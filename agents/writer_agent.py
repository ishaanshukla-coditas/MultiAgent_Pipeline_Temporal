import logging
from dataclasses import dataclass
from agents.llm_client import call_llm
from agents.research_agent import ResearchBrief
from agents.competitor_agent import CompetitorBrief
from agents.seo_agent import SEOBrief
from temporalio import activity

logger = logging.getLogger(__name__)


@dataclass
class ArticleOutput:
    topic: str
    title: str
    meta_description: str
    content: str
    word_count: int

@activity.defn
async def run_writer_agent(
    topic: str,
    research: ResearchBrief,
    competitor: CompetitorBrief,
    seo: SEOBrief,
) -> ArticleOutput:
    """
    Takes all 3 briefs and writes a complete article.

    Step 1: Generate the best title
    Step 2: Write the full article using all briefs
    Step 3: Return structured article output
    """

    logger.info(f"Writer Agent starting for topic: {topic}")

    # Step 1 — Generate title
    title_prompt = f"""
    Topic: {topic}
    Primary keyword: {seo.primary_keyword}
    Search intent: {seo.search_intent}

    Write ONE compelling article title that:
    - Includes the primary keyword naturally
    - Is under 60 characters
    - Matches the search intent
    - Makes people want to click

    Return only the title, nothing else.
    """

    title = await call_llm(
        prompt=title_prompt,
        system="You are an expert headline writer for SEO content."
    )
    title = title.strip().strip('"')
    logger.info(f"Generated title: {title}")

    # Step 2 — Write the full article
    headings = "\n".join([f"- {h}" for h in seo.suggested_headings])
    secondary_kw = ", ".join(seo.secondary_keywords)

    article_prompt = f"""
    Write a complete, high-quality article with these specifications:

    TOPIC: {topic}
    TITLE: {title}
    TARGET WORD COUNT: {seo.target_word_count} words

    SEO REQUIREMENTS:
    - Primary keyword: {seo.primary_keyword}
    - Secondary keywords to use naturally: {secondary_kw}
    - Search intent: {seo.search_intent}

    USE THESE HEADINGS:
    {headings}

    RESEARCH TO INCLUDE:
    {research.key_facts}

    CONTENT GAPS TO ADDRESS:
    {competitor.content_gaps}

    UNIQUE ANGLES TO COVER:
    {competitor.opportunities}

    WRITING REQUIREMENTS:
    - Clear, engaging, informative style
    - Short paragraphs (2-3 sentences max)
    - Include specific facts from research
    - Each heading section is self-contained
    - Strong introduction and conclusion
    - Format in Markdown

    AI SEO REQUIREMENTS:
    - Each section directly answers a specific question
    - Clear definitions for key terms
    - At least 3 specific statistics or facts
    - Content that AI systems can easily extract and cite
    """

    system = """You are an expert content writer specializing in
    AI-optimized SEO content. You write articles that rank well
    in both traditional search and AI-generated answers.
    Always use clear extractable content blocks and direct answers."""

    logger.info("Calling Gemma to write full article...")
    content = await call_llm(prompt=article_prompt, system=system)

    word_count = len(content.split())
    logger.info(f"Article written. Word count: {word_count}")

    return ArticleOutput(
        topic=topic,
        title=title,
        meta_description=seo.meta_description,
        content=content,
        word_count=word_count,
    )