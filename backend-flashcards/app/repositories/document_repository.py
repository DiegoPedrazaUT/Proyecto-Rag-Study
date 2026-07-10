import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.external import Document
from app.models.document_chunk import DocumentChunk


class DocumentRepository:
    """Acceso de solo lectura a documentos y sus chunks (los gestiona el RAG)."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_document(self, document_id: uuid.UUID) -> Document | None:
        result = await self.db.execute(
            select(Document).where(Document.id == document_id)
        )
        return result.scalar_one_or_none()

    async def get_chunks_text(
        self, document_id: uuid.UUID, *, char_limit: int = 15000
    ) -> str:
        """Concatena el texto de los chunks de un documento, en orden de página.

        Se detiene al alcanzar el límite de caracteres para no exceder el
        contexto del modelo.
        """
        stmt = (
            select(DocumentChunk.content)
            .where(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.page_number)
        )
        result = await self.db.execute(stmt)
        chunks = result.scalars().all()

        texto = ""
        for chunk in chunks:
            if len(texto) + len(chunk) > char_limit:
                # Agrega lo que quepa y corta.
                texto += chunk[: char_limit - len(texto)]
                break
            texto += chunk + "\n"
        return texto