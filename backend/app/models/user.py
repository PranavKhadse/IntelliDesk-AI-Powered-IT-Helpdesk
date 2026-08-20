from sqlalchemy import Column, String, Boolean
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import TimestampMixin, generate_uuid


class UserRole:
    USER = "user"
    AGENT = "agent"
    ADMIN = "admin"
    ALL = [USER, AGENT, ADMIN]


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(String(50), default=UserRole.USER, nullable=False, index=True)
    department = Column(String(100), default="General", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    created_tickets = relationship("Ticket", back_populates="creator", foreign_keys="Ticket.creator_id", cascade="all, delete-orphan")
    assigned_tickets = relationship("Ticket", back_populates="assignee", foreign_keys="Ticket.assignee_id")
    comments = relationship("TicketComment", back_populates="author", cascade="all, delete-orphan")
    kb_articles = relationship("KBArticle", back_populates="author")

    def __repr__(self) -> str:
        return f"<User {self.email} ({self.role})>"
