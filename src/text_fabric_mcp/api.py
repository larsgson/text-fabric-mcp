"""FastAPI HTTP layer wrapping TFEngine."""

from __future__ import annotations

import hmac
import logging
import os

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from text_fabric_mcp.quiz_engine import QuizStore, generate_session
from text_fabric_mcp.quiz_models import QuizDefinition
from text_fabric_mcp.tf_engine import TFEngine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Text-Fabric MCP API",
    description="Biblical text analysis API powered by Text-Fabric",
    version="0.1.0",
)

API_KEY = os.getenv("API_KEY")
if not API_KEY:
    logger.warning("API_KEY not set. All requests will be allowed.")


@app.middleware("http")
async def verify_api_key(request: Request, call_next):
    if API_KEY and request.url.path != "/health":
        key = request.headers.get("x-api-key", "")
        if not hmac.compare_digest(key, API_KEY):
            return JSONResponse(status_code=401, content={"detail": "Invalid API key"})
    return await call_next(request)


@app.get("/health")
def health():
    """Unauthenticated health check for Railway/Fly.io."""
    return {"status": "ok"}


engine = TFEngine()
quiz_store = QuizStore()


# --- Request models ---


class WordSearchRequest(BaseModel):
    corpus: str = "hebrew"
    book: str | None = None
    chapter: int | None = None
    features: dict[str, str] | None = None
    limit: int = 100


class ConstructionSearchRequest(BaseModel):
    template: str
    corpus: str = "hebrew"
    limit: int = 50


class ChatRequest(BaseModel):
    message: str
    history: list[dict] | None = None


# --- Endpoints ---


@app.get("/api/corpora")
def list_corpora():
    """List available corpora."""
    return engine.list_corpora()


@app.get("/api/books")
def list_books(corpus: str = "hebrew"):
    """List books with chapter counts for a corpus."""
    books = engine.list_books(corpus)
    return [b.model_dump() for b in books]


@app.get("/api/passage")
def get_passage(
    book: str,
    chapter: int,
    verse_start: int = 1,
    verse_end: int | None = None,
    corpus: str = "hebrew",
):
    """Get biblical text for a verse range with morphological annotations."""
    result = engine.get_passage(book, chapter, verse_start, verse_end, corpus)
    return result.model_dump()


@app.get("/api/schema")
def get_schema(corpus: str = "hebrew"):
    """Return object types and their features for a corpus."""
    result = engine.get_schema(corpus)
    return result.model_dump()


@app.post("/api/search/words")
def search_words(req: WordSearchRequest):
    """Search for words matching morphological feature constraints."""
    return engine.search_words(
        corpus=req.corpus,
        book=req.book,
        chapter=req.chapter,
        features=req.features,
        limit=req.limit,
    )


@app.post("/api/search/constructions")
def search_constructions(req: ConstructionSearchRequest):
    """Search for structural patterns using Text-Fabric search templates."""
    return engine.search_constructions(
        template=req.template,
        corpus=req.corpus,
        limit=req.limit,
    )


@app.get("/api/lexeme/{lexeme}")
def get_lexeme_info(
    lexeme: str,
    corpus: str = "hebrew",
    limit: int = 50,
):
    """Look up a lexeme and return its gloss, part of speech, and occurrences."""
    return engine.get_lexeme_info(lexeme, corpus, limit)


@app.get("/api/vocabulary")
def get_vocabulary(
    book: str,
    chapter: int,
    verse_start: int = 1,
    verse_end: int | None = None,
    corpus: str = "hebrew",
):
    """Get unique lexemes in a passage with frequency and gloss."""
    return engine.get_vocabulary(book, chapter, verse_start, verse_end, corpus)


@app.post("/api/chat")
def chat_endpoint(req: ChatRequest):
    """Send a message to the LLM with biblical text tools available."""
    if not (os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")):
        raise HTTPException(
            status_code=503,
            detail="Chat unavailable: GOOGLE_API_KEY not configured",
        )
    try:
        from text_fabric_mcp.chat import chat

        return chat(engine, req.message, req.history)
    except Exception as e:
        logger.error("Chat error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chat-quiz")
def chat_quiz_endpoint(req: ChatRequest):
    """AI-assisted quiz builder. Describe the quiz you want in natural language."""
    if not (os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")):
        raise HTTPException(
            status_code=503,
            detail="Chat unavailable: GOOGLE_API_KEY not configured",
        )
    try:
        from text_fabric_mcp.chat import chat_quiz

        return chat_quiz(engine, req.message, req.history)
    except Exception as e:
        logger.error("Chat-quiz error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/context")
def get_context(
    book: str,
    chapter: int,
    verse: int,
    word_index: int = 0,
    corpus: str = "hebrew",
):
    """Get the linguistic hierarchy for a specific word."""
    return engine.get_context(book, chapter, verse, word_index, corpus)


# --- Quiz endpoints ---


@app.get("/api/quizzes")
def list_quizzes():
    """List all saved quizzes."""
    return quiz_store.list_all()


@app.post("/api/quizzes")
def create_quiz(quiz: QuizDefinition):
    """Create a new quiz."""
    return quiz_store.save(quiz).model_dump()


@app.get("/api/quizzes/{quiz_id}")
def get_quiz(quiz_id: str):
    """Load a quiz by ID."""
    try:
        return quiz_store.load(quiz_id).model_dump()
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Quiz not found: {quiz_id}")


@app.put("/api/quizzes/{quiz_id}")
def update_quiz(quiz_id: str, quiz: QuizDefinition):
    """Update an existing quiz."""
    quiz.id = quiz_id
    return quiz_store.save(quiz).model_dump()


@app.delete("/api/quizzes/{quiz_id}")
def delete_quiz(quiz_id: str):
    """Delete a quiz."""
    quiz_store.delete(quiz_id)
    return {"status": "deleted"}


@app.post("/api/quizzes/{quiz_id}/generate")
def generate_quiz_session(quiz_id: str):
    """Generate a quiz session with questions from the quiz definition."""
    try:
        quiz = quiz_store.load(quiz_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Quiz not found: {quiz_id}")
    session = generate_session(quiz, engine)
    return session.model_dump()


if not (os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")):
    logger.warning("GOOGLE_API_KEY not set. Chat endpoint will be unavailable.")


def main():
    """Run the API server."""
    import uvicorn

    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
