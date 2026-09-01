"""Web search source, constrained to a trusted domain allowlist (PRD 5.1).

Uses Claude's server-side web_search tool rather than a separate search API
-- results run through Anthropic's infrastructure and are filtered to
config.WEB_SEARCH_ALLOWED_DOMAINS before Claude ever sees them.
"""

import anthropic

from hr_rag.config import (
    ANTHROPIC_API_KEY,
    LIGHT_MODEL,
    WEB_SEARCH_ALLOWED_DOMAINS,
    WEB_SEARCH_MAX_USES,
)
from hr_rag.models import RetrievedChunk

_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


def search(query: str) -> list[RetrievedChunk]:
    response = _client.messages.create(
        model=LIGHT_MODEL,
        max_tokens=1024,
        tools=[
            {
                "type": "web_search_20260209",
                "name": "web_search",
                "allowed_domains": WEB_SEARCH_ALLOWED_DOMAINS,
                "max_uses": WEB_SEARCH_MAX_USES,
            }
        ],
        messages=[
            {
                "role": "user",
                "content": (
                    "Search for information relevant to this HR question and "
                    f"summarize what you find, citing the source URL: {query}"
                ),
            }
        ],
    )

    # Collect cited URLs from the search-result blocks for attribution...
    urls = []
    for block in response.content:
        if block.type == "web_search_tool_result" and isinstance(block.content, list):
            for result in block.content:
                urls.append(getattr(result, "url", None))

    # ...and use Claude's synthesized text (the model reads the search
    # results server-side) as the actual retrieved content.
    chunks = []
    for block in response.content:
        if block.type == "text" and block.text.strip():
            chunks.append(
                RetrievedChunk(
                    source="web_search",
                    text=block.text.strip(),
                    metadata={"urls": [u for u in urls if u]},
                )
            )

    return chunks
