import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.quizzes import QuizAnswer, QuizAttempt, QuizQuestion


class AttemptRepository:
    """Acceso a datos para intentos de quiz."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_in_progress(
        self, *, quiz_id: uuid.UUID, user_id: uuid.UUID
    ) -> QuizAttempt | None:
        """Devuelve el intento en progreso del usuario para ese quiz, si existe."""
        stmt = select(QuizAttempt).where(
            QuizAttempt.quiz_id == quiz_id,
            QuizAttempt.user_id == user_id,
            QuizAttempt.status == "en_progreso",
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_attempt(self, attempt_id: uuid.UUID) -> QuizAttempt | None:
        result = await self.db.execute(
            select(QuizAttempt).where(QuizAttempt.id == attempt_id)
        )
        return result.scalar_one_or_none()

    async def get_question(
        self, question_id: uuid.UUID
    ) -> QuizQuestion | None:
        result = await self.db.execute(
            select(QuizQuestion).where(QuizQuestion.id == question_id)
        )
        return result.scalar_one_or_none()

    async def get_answer(
        self, *, attempt_id: uuid.UUID, question_id: uuid.UUID
    ) -> QuizAnswer | None:
        """Respuesta existente del usuario a una pregunta en este intento."""
        stmt = select(QuizAnswer).where(
            QuizAnswer.attempt_id == attempt_id,
            QuizAnswer.question_id == question_id,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def count_questions(self, quiz_id: uuid.UUID) -> int:
        """Número de preguntas de un quiz."""
        stmt = select(func.count(QuizQuestion.id)).where(
            QuizQuestion.quiz_id == quiz_id
        )
        result = await self.db.execute(stmt)
        return result.scalar_one()

    async def add(self, attempt: QuizAttempt) -> QuizAttempt:
        self.db.add(attempt)
        await self.db.flush()
        return attempt

    async def add_answer(self, answer: QuizAnswer) -> QuizAnswer:
        self.db.add(answer)
        await self.db.flush()
        return answer
    
    async def list_answers(
        self, attempt_id: uuid.UUID
    ) -> list[QuizAnswer]:
        """Todas las respuestas guardadas en un intento."""
        stmt = select(QuizAnswer).where(QuizAnswer.attempt_id == attempt_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def list_questions(
        self, quiz_id: uuid.UUID
    ) -> list[QuizQuestion]:
        """Todas las preguntas de un quiz, ordenadas por id (orden estable)."""
        stmt = (
            select(QuizQuestion)
            .where(QuizQuestion.quiz_id == quiz_id)
            .order_by(QuizQuestion.id)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())