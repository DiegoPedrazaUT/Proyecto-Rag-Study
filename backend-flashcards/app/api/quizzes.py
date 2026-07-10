import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import CurrentUser, get_current_user
from app.db.session import get_db
from app.schemas.quiz import (
    AnswerAck,
    AnswerSubmit,
    AttemptRead,
    AttemptResult,
    QuizCreate,
    QuizRead,
    QuizSummary,
    QuizWithAnswers,
    QuizWithoutAnswers,
)
from app.services.attempt_service import AttemptService
from app.services.quiz_service import QuizService

router = APIRouter(prefix="/quizzes", tags=["quizzes"])


@router.post(
    "",
    response_model=QuizRead,
    status_code=status.HTTP_201_CREATED,
    summary="Crear un quiz manualmente",
    responses={
        201: {"description": "Quiz creado correctamente con sus preguntas."},
        401: {"description": "Token ausente, inválido o expirado."},
        422: {"description": "Datos inválidos (sin preguntas, opciones repetidas, o respuesta correcta fuera de las opciones)."},
        500: {"description": "Error interno del servidor."},
    },
)
async def create_quiz(
    payload: QuizCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> QuizRead:
    """Crea un quiz completo con su título y todas sus preguntas.

    Cada pregunta lleva sus opciones y la respuesta correcta (que debe
    coincidir con una de las opciones).
    """
    service = QuizService(db)
    quiz = await service.create_quiz(payload=payload, current_user=current_user)
    return QuizRead.model_validate(quiz)


@router.get(
    "/organization/{organization_id}",
    response_model=list[QuizSummary],
    summary="Listar todos los quizzes de un salón",
    responses={
        200: {"description": "Quizzes del salón (visible para cualquier miembro)."},
        401: {"description": "Token ausente, inválido o expirado."},
        403: {"description": "El usuario no pertenece al salón."},
        422: {"description": "El organization_id no es un UUID válido."},
        500: {"description": "Error interno del servidor."},
    },
)
async def list_organization_quizzes(
    organization_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[QuizSummary]:
    """Lista todos los quizzes creados en un salón, sin importar quién los creó.

    Accesible para cualquier miembro (accepted) del salón.
    """
    service = QuizService(db)
    return await service.list_organization_quizzes(
        organization_id=organization_id, current_user=current_user
    )

@router.get(
    "",
    response_model=list[QuizSummary],
    summary="Listar mis quizzes",
    responses={
        200: {"description": "Lista de quizzes del usuario (puede estar vacía)."},
        401: {"description": "Token ausente, inválido o expirado."},
        500: {"description": "Error interno del servidor."},
    },
)
async def list_quizzes(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[QuizSummary]:
    """Lista los quizzes creados por el usuario autenticado.

    Cada quiz incluye `question_count`, el número de preguntas que contiene.
    """
    service = QuizService(db)
    return await service.list_user_quizzes(current_user=current_user)


@router.get(
    "/{quiz_id}",
    response_model=QuizWithAnswers | QuizWithoutAnswers,
    summary="Obtener un quiz",
    responses={
        200: {"description": "Quiz con sus preguntas (con o sin respuestas, según corresponda)."},
        401: {"description": "Token ausente, inválido o expirado."},
        404: {"description": "El quiz no existe."},
        422: {"description": "El quiz_id de la URL no es un UUID válido."},
        500: {"description": "Error interno del servidor."},
    },
)
async def get_quiz(
    quiz_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> QuizWithAnswers | QuizWithoutAnswers:
    """Devuelve un quiz con sus preguntas.

    Las respuestas correctas se incluyen solo si el usuario es el dueño o
    si ya completó al menos un intento. En otro caso se ocultan.
    """
    service = QuizService(db)
    return await service.get_quiz(quiz_id=quiz_id, current_user=current_user)


@router.post(
    "/{quiz_id}/attempts",
    response_model=AttemptRead,
    status_code=status.HTTP_201_CREATED,
    summary="Iniciar un intento de quiz",
    responses={
        201: {"description": "Intento iniciado correctamente (estado en_progreso)."},
        401: {"description": "Token ausente, inválido o expirado."},
        404: {"description": "El quiz no existe."},
        409: {"description": "El usuario ya tiene un intento en progreso de este quiz."},
        422: {"description": "El quiz no tiene preguntas, o el quiz_id no es un UUID válido."},
        500: {"description": "Error interno del servidor."},
    },
)
async def start_attempt(
    quiz_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AttemptRead:
    """Inicia un nuevo intento para resolver el quiz.

    Falla si el quiz no tiene preguntas (422) o si el usuario ya tiene un
    intento en progreso de este quiz (409).
    """
    service = AttemptService(db)
    attempt = await service.start_attempt(
        quiz_id=quiz_id, current_user=current_user
    )
    return AttemptRead.model_validate(attempt)


@router.post(
    "/attempts/{attempt_id}/answers",
    response_model=AnswerAck,
    status_code=status.HTTP_201_CREATED,
    summary="Enviar respuesta a una pregunta del intento",
    responses={
        201: {"description": "Respuesta guardada (no se revela si es correcta)."},
        401: {"description": "Token ausente, inválido o expirado."},
        403: {"description": "El intento no pertenece al usuario."},
        404: {"description": "El intento no existe, o la pregunta no pertenece al quiz del intento."},
        409: {"description": "El intento ya fue finalizado; no admite más respuestas."},
        422: {"description": "La respuesta no coincide con ninguna de las opciones."},
    },
)
async def submit_answer(
    attempt_id: uuid.UUID,
    payload: AnswerSubmit,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AnswerAck:
    """Guarda la respuesta del usuario a una pregunta del intento.

    No revela si la respuesta es correcta (eso se ve al finalizar el intento).
    Si ya se había respondido esa pregunta, la sobrescribe.
    """
    service = AttemptService(db)
    answer = await service.submit_answer(
        attempt_id=attempt_id, payload=payload, current_user=current_user
    )
    return AnswerAck(
        attempt_id=attempt_id,
        question_id=answer.question_id,
        saved=True,
    )


@router.post(
    "/attempts/{attempt_id}/finish",
    response_model=AttemptResult,
    summary="Finalizar el intento y calcular el resultado",
    responses={
        200: {"description": "Intento finalizado; devuelve el score y el detalle por pregunta."},
        401: {"description": "Token ausente, inválido o expirado."},
        403: {"description": "El intento no pertenece al usuario."},
        404: {"description": "El intento no existe."},
        409: {"description": "El intento ya fue finalizado."},
        500: {"description": "Error interno del servidor."},
    },
)
async def finish_attempt(
    attempt_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AttemptResult:
    """Finaliza el intento, calcula el score y revela el resultado.

    Las preguntas sin responder cuentan como incorrectas. Devuelve el detalle
    por pregunta con la respuesta correcta y la del usuario.
    """
    service = AttemptService(db)
    return await service.finish_attempt(
        attempt_id=attempt_id, current_user=current_user
    )

