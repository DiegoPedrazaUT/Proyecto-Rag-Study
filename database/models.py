import uuid
from sqlalchemy import Boolean, Column, Integer, String, Text, SmallInteger, DateTime, ForeignKey, Numeric, Table
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector 
from database.database import Base

# ==========================================
# 1. CATÁLOGOS
# ==========================================
class Role(Base):
    __tablename__ = "roles"
    role_id = Column(Integer, primary_key=True, index=True)
    role_name = Column(String(50), unique=True, nullable=False)

class Career(Base):
    __tablename__ = "careers"
    career_id = Column(Integer, primary_key=True, index=True)
    career_name = Column(String(255), unique=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# ==========================================
# 2. SEGURIDAD BASE (Tu módulo)
# ==========================================
class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    role_id = Column(Integer, ForeignKey("roles.role_id", ondelete="RESTRICT"), nullable=False)
    
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=True) 
    google_id = Column(String(255), unique=True, nullable=True)
    
    is_verified = Column(Boolean, default=False)
    verification_token = Column(String(255), unique=True, nullable=True)
    verification_token_expires = Column(DateTime(timezone=True), nullable=True)
    
    reset_token = Column(String(255), unique=True, nullable=True)
    reset_token_expires = Column(DateTime(timezone=True), nullable=True)
    
    is_mfa_enabled = Column(Boolean, default=False)
    mfa_secret = Column(String(32), nullable=True)
    
    failed_attempts = Column(SmallInteger, default=0)
    lockout_until = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    role = relationship("Role")

class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    token = Column(Text, unique=True, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# ==========================================
# 3. PERFILES DE USUARIO
# ==========================================
class StudentProfile(Base):
    __tablename__ = "student_profiles"
    profile_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    matricula = Column(String(50), unique=True, nullable=False)
    career_id = Column(Integer, ForeignKey("careers.career_id", ondelete="RESTRICT"))

class TeacherProfile(Base):
    __tablename__ = "teacher_profiles"
    profile_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    career_id = Column(Integer, ForeignKey("careers.career_id", ondelete="RESTRICT"))

# ==========================================
# 4. ORGANIZACIONES E INVITACIONES
# ==========================================
class Organization(Base):
    __tablename__ = "organizations"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    career_id = Column(Integer, ForeignKey("careers.career_id", ondelete="CASCADE"))
    join_code = Column(String(20), unique=True, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class OrganizationMember(Base):
    __tablename__ = "organization_members"
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    role = Column(String(50), default="Miembro")
    status = Column(String(50), default="pending")
    joined_at = Column(DateTime(timezone=True), server_default=func.now())

class OrganizationInvite(Base):
    __tablename__ = "organization_invites"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"))
    email = Column(String(255), nullable=False)
    invited_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    status = Column(String(50), default="pending")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# ==========================================
# 5. DOCUMENTOS Y MOTOR RAG
# ==========================================
class Document(Base):
    __tablename__ = "documents"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True)
    title = Column(String(255), nullable=False)
    file_url = Column(Text)
    status = Column(String(50), default="procesando")
    last_read_page = Column(Integer, default=1)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"))
    page_number = Column(Integer)
    content = Column(Text, nullable=False)
    embedding = Column(Vector(768)) # Requiere pgvector
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class RagSession(Base):
    __tablename__ = "rag_sessions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    title = Column(String(255), default="Nuevo Chat")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# Tabla puente para RAG Sessions y Documents
rag_session_documents = Table(
    "rag_session_documents",
    Base.metadata,
    Column("session_id", UUID(as_uuid=True), ForeignKey("rag_sessions.id", ondelete="CASCADE"), primary_key=True),
    Column("document_id", UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), primary_key=True)
)

class RagMessage(Base):
    __tablename__ = "rag_messages"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("rag_sessions.id", ondelete="CASCADE"))
    role = Column(String(50), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# ==========================================
# 6. FLASHCARDS Y VISTAS
# ==========================================
class FlashcardDeck(Base):
    __tablename__ = "flashcard_decks"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)
    title = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Flashcard(Base):
    __tablename__ = "flashcards"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    deck_id = Column(UUID(as_uuid=True), ForeignKey("flashcard_decks.id", ondelete="CASCADE"))
    front_text = Column(Text, nullable=False)
    back_text = Column(Text, nullable=False)
    is_seen = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class FlashcardView(Base):
    __tablename__ = "flashcard_views"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    deck_id = Column(UUID(as_uuid=True), ForeignKey("flashcard_decks.id", ondelete="CASCADE"))
    viewer_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    viewer_name = Column(String(255), nullable=False)
    viewed_at = Column(DateTime(timezone=True), server_default=func.now())

# ==========================================
# 7. EXÁMENES (QUIZZES)
# ==========================================
class Quiz(Base):
    __tablename__ = "quizzes"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"))
    title = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class QuizQuestion(Base):
    __tablename__ = "quiz_questions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    quiz_id = Column(UUID(as_uuid=True), ForeignKey("quizzes.id", ondelete="CASCADE"))
    question = Column(Text, nullable=False)
    options = Column(JSONB, nullable=False)
    correct_answer = Column(String(255), nullable=False)
    explanation = Column(Text)

class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    quiz_id = Column(UUID(as_uuid=True), ForeignKey("quizzes.id", ondelete="CASCADE"))
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    score = Column(Numeric(5,2))
    status = Column(String(50), default="en_progreso")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class QuizAnswer(Base):
    __tablename__ = "quiz_answers"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    attempt_id = Column(UUID(as_uuid=True), ForeignKey("quiz_attempts.id", ondelete="CASCADE"))
    question_id = Column(UUID(as_uuid=True), ForeignKey("quiz_questions.id", ondelete="CASCADE"))
    user_answer = Column(String(255))
    is_correct = Column(Boolean)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# ==========================================
# 8. PROGRESO EXTERNO
# ==========================================
class UserActivityLog(Base):
    __tablename__ = "user_activity_logs"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    action_type = Column(String(100), nullable=False)
    duration_minutes = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class ApiKey(Base):
    __tablename__ = "api_keys"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    name = Column(String(100))
    hashed_key = Column(Text, nullable=False)
    prefix = Column(String(10))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Subscription(Base):
    __tablename__ = "subscriptions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    plan_name = Column(String(100), nullable=False)
    status = Column(String(50), nullable=False)
    current_period_end = Column(DateTime(timezone=True))