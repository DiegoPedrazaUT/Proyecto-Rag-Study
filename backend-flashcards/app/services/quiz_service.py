import uuid

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.organization_repository import OrganizationRepository
from app.core.security import CurrentUser
from app.models.quizzes import Quiz, QuizQuestion
from app.repositories.quiz_repository import QuizRepository
from app.schemas.quiz import (
    QuizCreate,
    QuizSummary,
    QuizWithAnswers,
    QuizWithoutAnswers,
)


class QuizService:
    """Lógica de negocio para quizzes."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = QuizRepository(db)
        self.orgs = OrganizationRepository(db)

    async def create_quiz(
        self, *, payload: QuizCreate, current_user: CurrentUser
    ) -> Quiz:
        """Crea un quiz completo con todas sus preguntas en una operación.

        El usuario debe pertenecer (accepted) al salón indicado.
        """
        is_member = await self.orgs.is_member(
            user_id=current_user.id,
            organization_id=payload.organization_id,
        )
        if not is_member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No perteneces a este salón.",
            )

        quiz = Quiz(
            user_id=current_user.id,
            organization_id=payload.organization_id,
            document_id=payload.document_id,
            title=payload.title,
            questions=[
                QuizQuestion(
                    question=q.question,
                    options=[o.strip() for o in q.options],
                    correct_answer=q.correct_answer.strip(),
                    explanation=q.explanation,
                )
                for q in payload.questions
            ],
        )
        await self.repo.add_quiz(quiz)
        await self.db.commit()

        return await self.repo.get_quiz_with_questions(quiz.id)

    async def list_user_quizzes(
        self, *, current_user: CurrentUser
    ) -> list[QuizSummary]:
        """Lista los quizzes del usuario, con conteo de preguntas."""
        rows = await self.repo.list_by_user(current_user.id)
        return [
            QuizSummary(
                id=quiz.id,
                user_id=quiz.user_id,
                document_id=quiz.document_id,
                title=quiz.title,
                created_at=quiz.created_at,
                question_count=count,
            )
            for quiz, count in rows
        ]
    
    async def list_organization_quizzes(
        self, *, organization_id: uuid.UUID, current_user: CurrentUser
    ) -> list[QuizSummary]:
        """Lista todos los quizzes de un salón, visible para cualquier miembro.

        El usuario debe pertenecer (accepted) al salón.
        """
        is_member = await self.orgs.is_member(
            user_id=current_user.id,
            organization_id=organization_id,
        )
        if not is_member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No perteneces a este salón.",
            )

        rows = await self.repo.list_by_organization(organization_id)
        return [
            QuizSummary(
                id=quiz.id,
                user_id=quiz.user_id,
                document_id=quiz.document_id,
                title=quiz.title,
                created_at=quiz.created_at,
                question_count=count,
            )
            for quiz, count in rows
        ]


    async def get_quiz(
        self, *, quiz_id: uuid.UUID, current_user: CurrentUser
    ) -> QuizWithAnswers | QuizWithoutAnswers:
        """Devuelve un quiz, revelando respuestas solo si corresponde.

        Cualquier miembro (accepted) del salón del quiz puede verlo.
        Las respuestas se revelan si el usuario es el dueño, o si tiene al
        menos un intento completado. En otro caso, se ocultan (anti-trampa).
        """
        quiz = await self.repo.get_quiz_with_questions(quiz_id)
        if quiz is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="El quiz no existe.",
            )

        # Permiso de acceso: debe ser miembro del salón del quiz.
        # (Los quizzes viejos sin organization_id solo los ve su dueño.)
        is_owner = quiz.user_id == current_user.id
        if quiz.organization_id is not None:
            is_member = await self.orgs.is_member(
                user_id=current_user.id,
                organization_id=quiz.organization_id,
            )
            if not is_member:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="No perteneces al salón de este quiz.",
                )
        elif not is_owner:
            # Quiz viejo sin salón: solo el dueño puede verlo.
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes acceso a este quiz.",
            )

        # Revelar respuestas: dueño o quien ya completó un intento (anti-trampa).
        reveal = is_owner or await self.repo.has_completed_attempt(
            quiz_id=quiz_id, user_id=current_user.id
        )

        questions = sorted(quiz.questions, key=lambda q: str(q.id))

        if reveal:
            return QuizWithAnswers(
                id=quiz.id,
                user_id=quiz.user_id,
                document_id=quiz.document_id,
                title=quiz.title,
                created_at=quiz.created_at,
                answers_revealed=True,
                questions=questions,
            )
        return QuizWithoutAnswers(
            id=quiz.id,
            user_id=quiz.user_id,
            document_id=quiz.document_id,
            title=quiz.title,
            created_at=quiz.created_at,
            answers_revealed=False,
            questions=questions,
        )