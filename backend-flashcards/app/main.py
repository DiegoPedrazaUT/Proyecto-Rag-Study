from fastapi import FastAPI
from app.api import organizations

from app.api import decks, flashcards, quizzes, views

app = FastAPI(
    title="Rag-Study · Flashcards Service",
    version="0.1.0",
)


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(decks.router)
app.include_router(flashcards.router)
app.include_router(views.router)
app.include_router(quizzes.router)
app.include_router(organizations.router)