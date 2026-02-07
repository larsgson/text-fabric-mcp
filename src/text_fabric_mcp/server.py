"""Text-Fabric MCP Server — exposes biblical text analysis via MCP tools."""

from __future__ import annotations

import logging

from mcp.server.fastmcp import FastMCP

from text_fabric_mcp.tf_engine import TFEngine
from text_fabric_mcp.tools import passage, schema, search, vocab

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

mcp = FastMCP(
    "Text-Fabric MCP",
    instructions=(
        "Biblical text analysis server powered by Text-Fabric. "
        "Provides access to the Hebrew Bible (BHSA/ETCBC4) and "
        "Greek New Testament (Nestle 1904) with full morphological annotations. "
        "Use list_corpora to see available corpora, list_books to see books, "
        "get_passage to retrieve annotated text, search_words to find words "
        "by morphological features, and get_word_context to see syntactic hierarchy."
    ),
)

engine = TFEngine()

# Register all tool modules
passage.register(mcp, engine)
schema.register(mcp, engine)
search.register(mcp, engine)
vocab.register(mcp, engine)


def main():
    logger.info("Starting Text-Fabric MCP server...")
    mcp.run()


if __name__ == "__main__":
    main()
