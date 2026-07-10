import uuid
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import CurrentUser
from app.core.text_utils import normalize_answer
from app.models.quizzes import QuizAnswer, QuizAttempt
from app.repositories.attempt_repository import AttemptRepository
from app.repositories.quiz_repository import QuizRepository
from app.schemas.quiz import (
    AnswerSubmit,
    AttemptResult,
    AttemptResultItem,
)


class AttemptService:
    """Lógica de negocio para intentos de quiz."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.attempts = AttemptRepository(db)
        self.quizzes = QuizRepository(db)

    async def start_attempt(
        self, *, quiz_id: uuid.UUID, current_user: CurrentUser
    ) -> QuizAttempt:
        """Inicia un nuevo intento de un quiz.

        - El quiz debe existir y tener al menos una pregunta.
        - El usuario no puede tener otro intento en progreso del mismo quiz.
        El intento se crea a nombre del usuario autenticado (sea o no dueño).
        """
        quiz = await self.quizzes.get_quiz_with_questions(quiz_id)
        if quiz is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="El quiz no existe.",
            )

        n_questions = await self.attempts.count_questions(quiz_id)
        if n_questions == 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="El quiz no tiene preguntas; no se puede intentar.",
            )

        existing = await self.attempts.get_in_progress(
            quiz_id=quiz_id, user_id=current_user.id
        )
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ya tienes un intento en progreso para este quiz.",
            )

        attempt = QuizAttempt(
            quiz_id=quiz_id,
            user_id=current_user.id,
            status="en_progreso",
        )
        await self.attempts.add(attempt)
        await self.db.commit()
        await self.db.refresh(attempt)
        return attempt

    async def submit_answer(
        self,
        *,
        attempt_id: uuid.UUID,
        payload: AnswerSubmit,
        current_user: CurrentUser,
    ) -> QuizAnswer:
        """Guarda (o sobrescribe) la respuesta del usuario a una pregunta.

        No revela si es correcta. Calcula is_correct internamente para no
        recalcular al finalizar. Normaliza la respuesta (mayúsculas/espacios,
        acentos significativos) y guarda la versión canónica de la opción.
        """
        attempt = await self.attempts.get_attempt(attempt_id)
        if attempt is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="El intento no existe.",
            )
        # El intento debe ser del usuario autenticado.
        if attempt.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Este intento no te pertenece.",
            )
        # No se aceptan respuestas en un intento ya finalizado.
        if attempt.status != "en_progreso":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El intento ya fue finalizado; no admite más respuestas.",
            )

        question = await self.attempts.get_question(payload.question_id)
        # La pregunta debe existir y pertenecer al quiz de este intento.
        if question is None or question.quiz_id != attempt.quiz_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="La pregunta no pertenece al quiz de este intento.",
            )

        # Validar que la respuesta sea una de las opciones (normalizada) y
        # obtener la versión canónica (el texto exacto de la opción).
        norm_user = normalize_answer(payload.user_answer)
        canonical = next(
            (opt for opt in question.options if normalize_answer(opt) == norm_user),
            None,
        )
        if canonical is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="La respuesta no coincide con ninguna de las opciones.",
            )

        is_correct = norm_user == normalize_answer(question.correct_answer)

        # Sobrescribir si ya existía respuesta para esta pregunta.
        existing = await self.attempts.get_answer(
            attempt_id=attempt_id, question_id=payload.question_id
        )
        if existing is not None:
            existing.user_answer = canonical
            existing.is_correct = is_correct
            answer = existing
        else:
            answer = QuizAnswer(
                attempt_id=attempt_id,
                question_id=payload.question_id,
                user_answer=canonical,
                is_correct=is_correct,
            )
            await self.attempts.add_answer(answer)

        await self.db.commit()
        return answer
    async def finish_attempt(
        self, *, attempt_id: uuid.UUID, current_user: CurrentUser
    ) -> AttemptResult:
        """Finaliza un intento: calcula el score, lo marca completado y revela.

        El score es (correctas / total de preguntas) * 100. Las preguntas sin
        responder cuentan como incorrectas. Solo el dueño del intento puede
        finalizarlo, y solo si está en progreso.
        """
        attempt = await self.attempts.get_attempt(attempt_id)
        if attempt is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="El intento no existe.",
            )
        if attempt.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Este intento no te pertenece.",
            )
        if attempt.status != "en_progreso":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El intento ya fue finalizado.",
            )

        questions = await self.attempts.list_questions(attempt.quiz_id)
        answers = await self.attempts.list_answers(attempt_id)
        answers_by_q = {a.question_id: a for a in answers}

        total = len(questions)
        correct_count = 0
        items: list[AttemptResultItem] = []
        for q in questions:
            ans = answers_by_q.get(q.id)
            is_correct = bool(ans.is_correct) if ans is not None else False
            if is_correct:
                correct_count += 1
            items.append(
                AttemptResultItem(
                    question_id=q.id,
                    question=q.question,
                    options=q.options,
                    correct_answer=q.correct_answer,
                    user_answer=ans.user_answer if ans is not None else None,
                    is_correct=is_correct,
                    explanation=q.explanation,
                )
            )

        # Score sobre el total de preguntas (las no respondidas cuentan mal).
        score_value = (correct_count / total * 100) if total > 0 else 0.0

        attempt.status = "completado"
        attempt.score = Decimal(f"{score_value:.2f}")
        await self.db.commit()

        return AttemptResult(
            attempt_id=attempt.id,
            quiz_id=attempt.quiz_id,
            status=attempt.status,
            score=float(attempt.score),
            correct_count=correct_count,
            total_questions=total,
            answered_count=len(answers),
            results=items,
        )