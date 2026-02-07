# Text-Fabric MCP

Biblical text analysis server powered by [Text-Fabric](https://annotation.github.io/text-fabric/), providing morphologically annotated Hebrew Bible (BHSA) and Greek New Testament (Nestle 1904) data via both an MCP (Model Context Protocol) interface and a REST API.

## Features

- **Hebrew Bible** -- 39 books (Genesis--2 Chronicles) with full morphological annotation from [ETCBC/bhsa](https://github.com/ETCBC/bhsa)
- **Greek New Testament** -- 27 books (Matthew--Revelation) from [ETCBC/nestle1904](https://github.com/ETCBC/nestle1904)
- **Passage retrieval** -- verse-level text with per-word lexeme, gloss, part of speech, and morphological features
- **Morphological search** -- find words by part of speech, verbal stem, tense, gender, number, person, state, and more
- **Structural search** -- find syntactic patterns (clauses, phrases) using Text-Fabric search templates
- **Vocabulary extraction** -- unique lexemes in a passage sorted by corpus frequency
- **LLM chat** -- agentic conversation with Claude that can call all the above tools (requires Anthropic API key)
- **Quiz generation** -- configurable quiz engine for Hebrew morphology drills
- **Dual interface** -- same engine exposed as MCP tools (for AI assistants) and as a FastAPI HTTP API (for web frontends)

## Quick Start

```bash
# Clone and set up
git clone https://github.com/<your-org>/text-fabric-mcp.git
cd text-fabric-mcp
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Start the REST API server
tf-api
```

The API runs at `http://localhost:8000`. The first request loads corpus data into memory (~10 seconds on first download).

### Run as MCP server

```bash
tf-mcp
```

This starts the MCP (Model Context Protocol) server for use with Claude Desktop or other MCP-compatible clients.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/corpora` | List available corpora |
| GET | `/api/books?corpus=hebrew` | List books with chapter counts |
| GET | `/api/passage?book=Genesis&chapter=1&verse_start=1` | Get annotated text |
| GET | `/api/schema?corpus=hebrew` | Corpus object types and features |
| POST | `/api/search/words` | Search by morphological features |
| POST | `/api/search/constructions` | Structural pattern matching |
| GET | `/api/lexeme/{lexeme}` | Lexeme lookup with occurrences |
| GET | `/api/vocabulary?book=Genesis&chapter=1` | Unique lexemes in a passage |
| GET | `/api/context?book=Genesis&chapter=1&verse=1` | Syntactic hierarchy for a word |
| POST | `/api/chat` | LLM-powered biblical analysis |
| GET/POST | `/api/quizzes` | Quiz CRUD |
| POST | `/api/quizzes/{id}/generate` | Generate a quiz session |

## MCP Tools

When running as an MCP server, the following tools are available to AI assistants:

- `list_corpora`, `list_books`, `get_schema` -- corpus introspection
- `get_passage`, `get_word_context` -- text retrieval
- `search_words`, `search_constructions` -- linguistic search
- `get_lexeme_info`, `get_vocabulary` -- vocabulary queries

## Project Structure

```
src/text_fabric_mcp/
├── server.py          # MCP server entry point
├── api.py             # FastAPI HTTP layer
├── tf_engine.py       # Text-Fabric data access
├── chat.py            # Anthropic LLM integration
├── models.py          # Pydantic data models
├── quiz_engine.py     # Quiz generation engine
├── quiz_models.py     # Quiz data models
└── tools/             # MCP tool definitions
    ├── passage.py
    ├── schema.py
    ├── search.py
    └── vocab.py
tests/
├── test_api.py
├── test_tf_engine.py
└── test_quiz.py
```

## Testing

```bash
pytest
```

Tests download Text-Fabric data on first run (cached in `~/text-fabric-data/`).

## Configuration

| Variable | Required | Description |
|----------|----------|-------------|
| `PORT` | No | API server port (default: 8000) |
| `ANTHROPIC_API_KEY` | No | Enables the `/api/chat` endpoint |

## Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for full instructions on deploying to Fly.io, Railway, or Docker.

```bash
# Docker
docker build -t text-fabric-mcp .
docker run -p 8000:8000 text-fabric-mcp
```

## License

[MIT](LICENSE)
