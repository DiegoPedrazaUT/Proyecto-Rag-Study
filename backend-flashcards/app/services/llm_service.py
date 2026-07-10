from langchain_google_genai import ChatGoogleGenerativeAI
from app.schemas.llm import LLMEditProposal, GeneratedDeck

from app.core.config import settings
from app.schemas.llm import LLMEditProposal

# Instrucciones fijas para el modelo (en español, como acordamos).
SYSTEM_PROMPT = """Eres un asistente educativo de la Universidad Tecnológica (UT)
especializado en crear y mejorar material de estudio.

Tu tarea es editar flashcards. Recibes una flashcard (un frente con la
pregunta o concepto, y un reverso con la respuesta) junto con una
instrucción del usuario sobre cómo modificarla.

Reglas:
- Responde SIEMPRE en español.
- Aplica la instrucción del usuario, pero conserva la exactitud del concepto.
- No inventes datos falsos ni cambies el tema de la flashcard.
- Mantén el frente como una pregunta o concepto, y el reverso como su respuesta.
- Si la instrucción no aplica bien, devuelve la versión más fiel posible.
"""


class LLMService:
    """Encapsula la comunicación con Gemini para editar flashcards."""

    def __init__(self) -> None:
        # El modelo se configura con la API key y el modelo del .env.
        self._model = ChatGoogleGenerativeAI(
            model=settings.GEMINI_MODEL,
            google_api_key=settings.GOOGLE_API_KEY,
            temperature=0.3,
        )
        # with_structured_output fuerza a que la respuesta tenga la forma
        # de LLMEditProposal (front_text y back_text), en vez de texto libre.
        self._structured = self._model.with_structured_output(LLMEditProposal)

    async def edit_flashcard(
        self, *, front_text: str, back_text: str, instruction: str
    ) -> LLMEditProposal:
        """Pide a Gemini una versión editada de la flashcard."""
        user_prompt = (
            f"Flashcard actual:\n"
            f"Frente: {front_text}\n"
            f"Reverso: {back_text}\n\n"
            f"Instrucción del usuario: {instruction}\n\n"
            f"Devuelve la flashcard editada."
        )
        messages = [
            ("system", SYSTEM_PROMPT),
            ("human", user_prompt),
        ]
        # ainvoke = versión async de invoke (para no bloquear el servidor).
        result = await self._structured.ainvoke(messages)
        return result
    
    async def generate_cards_from_text(
        self, *, text: str, num_cards: int
    ) -> GeneratedDeck:
        """Genera un conjunto de flashcards a partir del texto de un documento."""
        system = (
            "Eres un asistente educativo de la Universidad Tecnológica (UT) "
            "especializado en crear material de estudio.\n"
            "A partir del contenido de un documento, generas flashcards de estudio.\n\n"
            "Reglas:\n"
            "- Responde SIEMPRE en español.\n"
            "- Cada flashcard tiene un frente (pregunta o concepto) y un reverso "
            "(respuesta clara y concisa).\n"
            "- Basa las flashcards ÚNICAMENTE en el contenido proporcionado.\n"
            "- No inventes información que no esté en el documento.\n"
            "- Cubre los conceptos más importantes del contenido.\n"
        )
        user = (
            f"Genera exactamente {num_cards} flashcards del siguiente contenido:\n\n"
            f"{text}"
        )
        structured = self._model.with_structured_output(GeneratedDeck)
        result = await structured.ainvoke(
            [("system", system), ("human", user)]
        )
        return result