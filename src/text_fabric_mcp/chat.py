"""LLM chat backend — calls Anthropic API with TFEngine tools in an agentic loop."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

import anthropic

from text_fabric_mcp.tf_engine import TFEngine

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (Path(__file__).parent.parent.parent / "system_prompt.md").read_text()

# Tool definitions for the Anthropic API — mirror the MCP tools
TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "list_corpora",
        "description": "List available corpora.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "list_books",
        "description": "List books with chapter counts for a corpus.",
        "input_schema": {
            "type": "object",
            "properties": {
                "corpus": {"type": "string", "default": "hebrew"},
            },
            "required": [],
        },
    },
    {
        "name": "get_passage",
        "description": "Get biblical text for a verse range with full morphological annotations.",
        "input_schema": {
            "type": "object",
            "properties": {
                "book": {"type": "string"},
                "chapter": {"type": "integer"},
                "verse_start": {"type": "integer", "default": 1},
                "verse_end": {"type": "integer"},
                "corpus": {"type": "string", "default": "hebrew"},
            },
            "required": ["book", "chapter"],
        },
    },
    {
        "name": "get_schema",
        "description": "Return object types and their features for a corpus.",
        "input_schema": {
            "type": "object",
            "properties": {
                "corpus": {"type": "string", "default": "hebrew"},
            },
            "required": [],
        },
    },
    {
        "name": "search_words",
        "description": "Search for words matching morphological feature constraints.",
        "input_schema": {
            "type": "object",
            "properties": {
                "corpus": {"type": "string", "default": "hebrew"},
                "book": {"type": "string"},
                "chapter": {"type": "integer"},
                "features": {
                    "type": "object",
                    "additionalProperties": {"type": "string"},
                },
                "limit": {"type": "integer", "default": 100},
            },
            "required": [],
        },
    },
    {
        "name": "search_constructions",
        "description": "Search for structural/syntactic patterns using Text-Fabric search templates.",
        "input_schema": {
            "type": "object",
            "properties": {
                "template": {"type": "string"},
                "corpus": {"type": "string", "default": "hebrew"},
                "limit": {"type": "integer", "default": 50},
            },
            "required": ["template"],
        },
    },
    {
        "name": "get_lexeme_info",
        "description": "Look up a lexeme and return its gloss, part of speech, and occurrences.",
        "input_schema": {
            "type": "object",
            "properties": {
                "lexeme": {"type": "string"},
                "corpus": {"type": "string", "default": "hebrew"},
                "limit": {"type": "integer", "default": 50},
            },
            "required": ["lexeme"],
        },
    },
    {
        "name": "get_vocabulary",
        "description": "Get unique lexemes in a passage with frequency and gloss.",
        "input_schema": {
            "type": "object",
            "properties": {
                "book": {"type": "string"},
                "chapter": {"type": "integer"},
                "verse_start": {"type": "integer", "default": 1},
                "verse_end": {"type": "integer"},
                "corpus": {"type": "string", "default": "hebrew"},
            },
            "required": ["book", "chapter"],
        },
    },
    {
        "name": "get_word_context",
        "description": "Get the linguistic hierarchy (phrase, clause, sentence) for a specific word.",
        "input_schema": {
            "type": "object",
            "properties": {
                "book": {"type": "string"},
                "chapter": {"type": "integer"},
                "verse": {"type": "integer"},
                "word_index": {"type": "integer", "default": 0},
                "corpus": {"type": "string", "default": "hebrew"},
            },
            "required": ["book", "chapter", "verse"],
        },
    },
]


def _execute_tool(engine: TFEngine, name: str, args: dict[str, Any]) -> Any:
    """Execute a tool call against the TFEngine and return the result."""
    if name == "list_corpora":
        return engine.list_corpora()
    elif name == "list_books":
        books = engine.list_books(args.get("corpus", "hebrew"))
        return [b.model_dump() for b in books]
    elif name == "get_passage":
        result = engine.get_passage(
            book=args["book"],
            chapter=args["chapter"],
            verse_start=args.get("verse_start", 1),
            verse_end=args.get("verse_end"),
            corpus=args.get("corpus", "hebrew"),
        )
        return result.model_dump()
    elif name == "get_schema":
        result = engine.get_schema(args.get("corpus", "hebrew"))
        return result.model_dump()
    elif name == "search_words":
        return engine.search_words(
            corpus=args.get("corpus", "hebrew"),
            book=args.get("book"),
            chapter=args.get("chapter"),
            features=args.get("features"),
            limit=args.get("limit", 100),
        )
    elif name == "search_constructions":
        return engine.search_constructions(
            template=args["template"],
            corpus=args.get("corpus", "hebrew"),
            limit=args.get("limit", 50),
        )
    elif name == "get_lexeme_info":
        return engine.get_lexeme_info(
            lexeme=args["lexeme"],
            corpus=args.get("corpus", "hebrew"),
            limit=args.get("limit", 50),
        )
    elif name == "get_vocabulary":
        return engine.get_vocabulary(
            book=args["book"],
            chapter=args["chapter"],
            verse_start=args.get("verse_start", 1),
            verse_end=args.get("verse_end"),
            corpus=args.get("corpus", "hebrew"),
        )
    elif name == "get_word_context":
        return engine.get_context(
            book=args["book"],
            chapter=args["chapter"],
            verse=args["verse"],
            word_index=args.get("word_index", 0),
            corpus=args.get("corpus", "hebrew"),
        )
    else:
        return {"error": f"Unknown tool: {name}"}


def chat(
    engine: TFEngine,
    message: str,
    history: list[dict[str, Any]] | None = None,
    model: str = "claude-sonnet-4-20250514",
    max_turns: int = 10,
) -> dict[str, Any]:
    """Run a chat turn with tool use loop.

    Returns:
        {"reply": str, "tool_calls": [{"name": str, "input": dict, "result": Any}, ...]}
    """
    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env

    messages: list[dict[str, Any]] = []
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": message})

    tool_calls_log: list[dict[str, Any]] = []

    for _ in range(max_turns):
        response = client.messages.create(
            model=model,
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=TOOL_DEFINITIONS,
            messages=messages,
        )

        # If no tool use, we're done
        if response.stop_reason != "tool_use":
            # Extract text from response
            text_parts = [
                block.text for block in response.content if block.type == "text"
            ]
            return {
                "reply": "\n".join(text_parts),
                "tool_calls": tool_calls_log,
            }

        # Process tool calls
        assistant_content = response.content
        messages.append({"role": "assistant", "content": assistant_content})

        tool_results = []
        for block in assistant_content:
            if block.type != "tool_use":
                continue

            logger.info("Tool call: %s(%s)", block.name, json.dumps(block.input)[:200])
            try:
                result = _execute_tool(engine, block.name, block.input)
                result_str = json.dumps(result, ensure_ascii=False, default=str)
                # Truncate very large results to stay within context
                if len(result_str) > 20000:
                    result_str = result_str[:20000] + "... (truncated)"
            except Exception as e:
                logger.error("Tool error: %s", e)
                result_str = json.dumps({"error": str(e)})

            tool_calls_log.append(
                {
                    "name": block.name,
                    "input": block.input,
                    "result": json.loads(result_str)
                    if not result_str.endswith("(truncated)")
                    else result_str,
                }
            )

            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result_str,
                }
            )

        messages.append({"role": "user", "content": tool_results})

    # Exhausted max turns
    return {
        "reply": "I've reached the maximum number of tool calls. Please try a more specific question.",
        "tool_calls": tool_calls_log,
    }
