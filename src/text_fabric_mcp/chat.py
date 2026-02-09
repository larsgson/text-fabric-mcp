"""LLM chat backend — calls Google Gemini API with TFEngine tools in an agentic loop."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from google import genai
from google.genai import types

from text_fabric_mcp.tf_engine import TFEngine

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (Path(__file__).parent.parent.parent / "system_prompt.md").read_text()

# Tool declarations for the Gemini API — mirror the MCP tools
TOOL_DECLARATIONS = [
    {
        "name": "list_corpora",
        "description": "List available corpora.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "list_books",
        "description": "List books with chapter counts for a corpus.",
        "parameters": {
            "type": "object",
            "properties": {
                "corpus": {
                    "type": "string",
                    "description": "Corpus name (hebrew or greek)",
                },
            },
            "required": [],
        },
    },
    {
        "name": "get_passage",
        "description": "Get biblical text for a verse range with full morphological annotations.",
        "parameters": {
            "type": "object",
            "properties": {
                "book": {"type": "string", "description": "Book name"},
                "chapter": {"type": "integer", "description": "Chapter number"},
                "verse_start": {"type": "integer", "description": "Start verse"},
                "verse_end": {"type": "integer", "description": "End verse"},
                "corpus": {"type": "string", "description": "Corpus name"},
            },
            "required": ["book", "chapter"],
        },
    },
    {
        "name": "get_schema",
        "description": "Return object types and their features for a corpus.",
        "parameters": {
            "type": "object",
            "properties": {
                "corpus": {"type": "string", "description": "Corpus name"},
            },
            "required": [],
        },
    },
    {
        "name": "search_words",
        "description": "Search for words matching morphological feature constraints.",
        "parameters": {
            "type": "object",
            "properties": {
                "corpus": {"type": "string", "description": "Corpus name"},
                "book": {"type": "string", "description": "Book name"},
                "chapter": {"type": "integer", "description": "Chapter number"},
                "features": {
                    "type": "object",
                    "description": "Feature name/value pairs",
                    "properties": {},
                },
                "limit": {"type": "integer", "description": "Max results"},
            },
            "required": [],
        },
    },
    {
        "name": "search_constructions",
        "description": "Search for structural/syntactic patterns using Text-Fabric search templates.",
        "parameters": {
            "type": "object",
            "properties": {
                "template": {"type": "string", "description": "Search template"},
                "corpus": {"type": "string", "description": "Corpus name"},
                "limit": {"type": "integer", "description": "Max results"},
            },
            "required": ["template"],
        },
    },
    {
        "name": "get_lexeme_info",
        "description": "Look up a lexeme and return its gloss, part of speech, and occurrences.",
        "parameters": {
            "type": "object",
            "properties": {
                "lexeme": {"type": "string", "description": "Lexeme identifier"},
                "corpus": {"type": "string", "description": "Corpus name"},
                "limit": {"type": "integer", "description": "Max occurrences"},
            },
            "required": ["lexeme"],
        },
    },
    {
        "name": "get_vocabulary",
        "description": "Get unique lexemes in a passage with frequency and gloss.",
        "parameters": {
            "type": "object",
            "properties": {
                "book": {"type": "string", "description": "Book name"},
                "chapter": {"type": "integer", "description": "Chapter number"},
                "verse_start": {"type": "integer", "description": "Start verse"},
                "verse_end": {"type": "integer", "description": "End verse"},
                "corpus": {"type": "string", "description": "Corpus name"},
            },
            "required": ["book", "chapter"],
        },
    },
    {
        "name": "get_word_context",
        "description": "Get the linguistic hierarchy (phrase, clause, sentence) for a specific word.",
        "parameters": {
            "type": "object",
            "properties": {
                "book": {"type": "string", "description": "Book name"},
                "chapter": {"type": "integer", "description": "Chapter number"},
                "verse": {"type": "integer", "description": "Verse number"},
                "word_index": {"type": "integer", "description": "Word index in verse"},
                "corpus": {"type": "string", "description": "Corpus name"},
            },
            "required": ["book", "chapter", "verse"],
        },
    },
]

TOOLS = types.Tool(function_declarations=TOOL_DECLARATIONS)


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
    model: str = "gemini-2.5-flash-lite",
    max_turns: int = 10,
) -> dict[str, Any]:
    """Run a chat turn with tool use loop.

    Returns:
        {"reply": str, "tool_calls": [{"name": str, "input": dict, "result": Any}, ...]}
    """
    client = genai.Client()  # reads GEMINI_API_KEY or GOOGLE_API_KEY from env

    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        tools=[TOOLS],
    )

    # Build conversation contents
    contents: list[types.Content] = []
    if history:
        for msg in history:
            role = "model" if msg["role"] == "assistant" else "user"
            contents.append(
                types.Content(role=role, parts=[types.Part(text=msg["content"])])
            )
    contents.append(types.Content(role="user", parts=[types.Part(text=message)]))

    tool_calls_log: list[dict[str, Any]] = []

    for _ in range(max_turns):
        response = client.models.generate_content(
            model=model,
            contents=contents,
            config=config,
        )

        candidate = response.candidates[0]

        # Check for function calls in response parts
        function_calls = [
            part.function_call
            for part in candidate.content.parts
            if part.function_call is not None
        ]

        if not function_calls:
            # No tool use — extract text and return
            text_parts = [part.text for part in candidate.content.parts if part.text]
            return {
                "reply": "\n".join(text_parts),
                "tool_calls": tool_calls_log,
            }

        # Append assistant response to conversation
        contents.append(candidate.content)

        # Process each function call
        function_response_parts = []
        for fc in function_calls:
            args = dict(fc.args) if fc.args else {}
            logger.info("Tool call: %s(%s)", fc.name, json.dumps(args)[:200])

            try:
                result = _execute_tool(engine, fc.name, args)
                result_str = json.dumps(result, ensure_ascii=False, default=str)
                if len(result_str) > 20000:
                    result_str = result_str[:20000] + "... (truncated)"
                result_data = (
                    json.loads(result_str)
                    if not result_str.endswith("(truncated)")
                    else result_str
                )
            except Exception as e:
                logger.error("Tool error: %s", e)
                result_data = {"error": str(e)}

            tool_calls_log.append(
                {
                    "name": fc.name,
                    "input": args,
                    "result": result_data,
                }
            )

            function_response_parts.append(
                types.Part.from_function_response(
                    name=fc.name,
                    response={"result": result_data},
                )
            )

        contents.append(types.Content(role="user", parts=function_response_parts))

    return {
        "reply": "I've reached the maximum number of tool calls. Please try a more specific question.",
        "tool_calls": tool_calls_log,
    }
