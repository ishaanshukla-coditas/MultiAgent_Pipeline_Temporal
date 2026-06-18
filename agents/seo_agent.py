from dataclasses import dataclass

# SEO strategy is now generated inside run_writer_agent in a single combined
# LLM call. This dataclass is kept for import compatibility.


@dataclass
class SEOBrief:
    primary_keyword: str
    secondary_keywords: list[str]
    search_intent: str
    suggested_headings: list[str]
    meta_description: str
    target_word_count: int
