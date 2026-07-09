import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.quizzes import Quiz, QuizQuestion, QuizAttempt


class QuizRepository:
    """Acceso a datos para quizzes. Sin lógica de negocio ni commits."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def add_quiz(self, quiz: Quiz) -> Quiz:
        self.db.add(quiz)
        await self.db.flush()
        return quiz

    async def get_quiz_with_questions(
        self, quiz_id: uuid.UUID
    ) -> Quiz | None:
        stmt = (
            select(Quiz)
            .where(Quiz.id == quiz_id)
            .options(selectinload(Quiz.questions))
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_user(
        self, user_id: uuid.UUID
    ) -> list[tuple[Quiz, int]]:
        """Quizzes del usuario, cada uno con su conteo de preguntas.

        Un solo query con LEFT JOIN + GROUP BY (evita el problema N+1).
        Devuelve tuplas (quiz, question_count), del más reciente al más antiguo.
        """
        stmt = (
            select(Quiz, func.count(QuizQuestion.id))
            .outerjoin(QuizQuestion, QuizQuestion.quiz_id == Quiz.id)
            .where(Quiz.user_id == user_id)
            .group_by(Quiz.id)
            .order_by(Quiz.created_at.desc())
        )
        result = await self.db.execute(stmt)
        return [(row[0], row[1]) for row in result.all()]
    

async def has_completed_attempt(
        self, *, quiz_id: uuid.UUID, user_id: uuid.UUID
    ) -> bool:
        """True si el usuario tiene al menos un intento completado del quiz."""
        stmt = select(QuizAttempt.id).where(
            QuizAttempt.quiz_id == quiz_id,
            QuizAttempt.user_id == user_id,
            QuizAttempt.status == "completado",
        )
        result = await self.db.execute(stmt)
        return result.first() is not None