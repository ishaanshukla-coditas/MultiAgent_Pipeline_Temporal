import httpx
import os
import logging

logger = logging.getLogger(__name__)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"


async def call_llm(prompt: str, system: str = None) -> str:
    """
    Calls Groq API and returns the response text.

    Args:
        prompt: the user message to send
        system: optional system prompt to set agent personality

    Returns:
        The LLM response as a plain string
    """

    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY is not set in environment variables")

    messages = []

    if system:
        messages.append({"role": "system", "content": system})

    messages.append({"role": "user", "content": prompt})

    logger.info(f"Calling Groq model={GROQ_MODEL}")
    logger.info(f"Prompt preview: {prompt[:100]}...")

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            GROQ_API_URL,
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": GROQ_MODEL,
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 2048,
            },
        )

        response.raise_for_status()
        data = response.json()

        result = data["choices"][0]["message"]["content"]
        logger.info(f"Groq responded: {result[:100]}...")
        return result
