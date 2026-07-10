import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.external import User

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

    async def list_by_organization(
        self, organization_id: uuid.UUID
    ) -> list[dict]:
        """Quizzes de un salón, con conteo de preguntas y nombre del creador.

        JOIN con users para traer el nombre de quien creó cada quiz.
        Devuelve dicts listos para el schema.
        """
        stmt = (
            select(
                Quiz,
                func.count(QuizQuestion.id).label("question_count"),
                User.first_name,
                User.last_name,
            )
            .outerjoin(QuizQuestion, QuizQuestion.quiz_id == Quiz.id)
            .join(User, User.id == Quiz.user_id)
            .where(Quiz.organization_id == organization_id)
            .group_by(Quiz.id, User.first_name, User.last_name)
            .order_by(Quiz.created_at.desc())
        )
        result = await self.db.execute(stmt)
        rows = result.all()

        quizzes = []
        for row in rows:
            quiz = row[0]
            count = row[1]
            nombre = " ".join(
                parte for parte in [row.first_name, row.last_name] if parte
            ).strip()
            quizzes.append(
                {
                    "id": quiz.id,
                    "user_id": quiz.user_id,
                    "creator_name": nombre or "Usuario sin nombre",
                    "document_id": quiz.document_id,
                    "title": quiz.title,
                    "created_at": quiz.created_at,
                    "question_count": count,
                }
            )
        return quizzes

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

    async def list_completed_attempts_with_users(
        self, quiz_id: uuid.UUID
    ) -> list[dict]:
        """Intentos completados de un quiz, con el nombre del estudiante.

        JOIN con users para traer first_name y last_name. Ordenados del
        más reciente al más antiguo.
        """
        stmt = (
            select(
                QuizAttempt.user_id,
                QuizAttempt.score,
                QuizAttempt.status,
                QuizAttempt.created_at,
                User.first_name,
                User.last_name,
            )
            .join(User, User.id == QuizAttempt.user_id)
            .where(
                QuizAttempt.quiz_id == quiz_id,
                QuizAttempt.status == "completado",
            )
            .order_by(QuizAttempt.created_at.desc())
        )
        result = await self.db.execute(stmt)
        rows = result.all()

        resultados = []
        for row in rows:
            nombre = " ".join(
                parte for parte in [row.first_name, row.last_name] if parte
            ).strip()
            resultados.append(
                {
                    "user_id": row.user_id,
                    "student_name": nombre or "Usuario sin nombre",
                    "score": float(row.score) if row.score is not None else None,
                    "status": row.status,
                    "attempted_at": row.created_at,
                }
            )
        return resultados