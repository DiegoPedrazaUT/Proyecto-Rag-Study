import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator


class QuizQuestionCreate(BaseModel):
    """Una pregunta a crear dentro de un quiz."""

    question: str = Field(..., min_length=1)
    options: list[str] = Field(..., min_length=2)
    correct_answer: str = Field(..., min_length=1)
    explanation: str | None = None

    @model_validator(mode="after")
    def validate_answer_and_options(self) -> "QuizQuestionCreate":
        cleaned = [o.strip() for o in self.options]
        if any(o == "" for o in cleaned):
            raise ValueError("Las opciones no pueden estar vacías.")
        if len(set(cleaned)) != len(cleaned):
            raise ValueError("Las opciones no pueden repetirse.")
        if self.correct_answer.strip() not in cleaned:
            raise ValueError(
                "correct_answer debe coincidir con una de las options."
            )
        return self


class QuizCreate(BaseModel):
    """Payload para crear un quiz completo (título + preguntas)."""

    title: str = Field(..., min_length=1, max_length=255)
    organization_id: uuid.UUID
    document_id: uuid.UUID | None = None
    questions: list[QuizQuestionCreate] = Field(..., min_length=1)


class QuizQuestionRead(BaseModel):
    """Pregunta tal como se devuelve al crear (incluye la respuesta)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    quiz_id: uuid.UUID
    question: str
    options: list[str]
    correct_answer: str
    explanation: str | None


class QuizQuestionPublic(BaseModel):
    """Pregunta SIN la respuesta correcta (para resolver el quiz)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    quiz_id: uuid.UUID
    question: str
    options: list[str]


class QuizWithAnswers(BaseModel):
    """Quiz con las respuestas correctas visibles (dueño o intento completado)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    document_id: uuid.UUID | None
    title: str
    created_at: datetime
    answers_revealed: bool
    questions: list[QuizQuestionRead]


class QuizWithoutAnswers(BaseModel):
    """Quiz sin respuestas (aún no se ha completado un intento)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    document_id: uuid.UUID | None
    title: str
    created_at: datetime
    answers_revealed: bool
    questions: list[QuizQuestionPublic]


class QuizRead(BaseModel):
    """Quiz con sus preguntas."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    document_id: uuid.UUID | None
    title: str
    created_at: datetime
    questions: list[QuizQuestionRead]


class QuizSummary(BaseModel):
    """Quiz sin preguntas, para listados (incluye conteo)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    creator_name: str
    document_id: uuid.UUID | None
    title: str
    created_at: datetime
    question_count: int

class AttemptRead(BaseModel):
    """Un intento de quiz."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    quiz_id: uuid.UUID
    user_id: uuid.UUID
    status: str
    score: float | None
    created_at: datetime

class AnswerSubmit(BaseModel):
    """Respuesta del usuario a una pregunta dentro de un intento."""

    question_id: uuid.UUID
    user_answer: str = Field(..., min_length=1)


class AnswerAck(BaseModel):
    """Confirmación de que la respuesta se guardó, SIN revelar si es correcta."""

    attempt_id: uuid.UUID
    question_id: uuid.UUID
    saved: bool


class AttemptResultItem(BaseModel):
    """Detalle del resultado de una pregunta, tras finalizar el intento."""

    question_id: uuid.UUID
    question: str
    options: list[str]
    correct_answer: str
    user_answer: str | None
    is_correct: bool
    explanation: str | None


class AttemptResult(BaseModel):
    """Resultado completo de un intento finalizado (revela respuestas)."""

    attempt_id: uuid.UUID
    quiz_id: uuid.UUID
    status: str
    score: float
    correct_count: int
    total_questions: int
    answered_count: int
    results: list[AttemptResultItem]

class QuizResultItem(BaseModel):
    """Resultado de un estudiante en un quiz (para el dueño)."""

    model_config = ConfigDict(from_attributes=True)

    user_id: uuid.UUID
    student_name: str
    score: float | None
    status: str
    attempted_at: datetime

