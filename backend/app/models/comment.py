from sqlalchemy import Column, String, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import TimestampMixin, generate_uuid


class CommentType:
    PUBLIC = "public"
    INTERNAL_NOTE = "internal_note"
    SYSTEM_EVENT = "system_event"
    AI_DRAFT = "ai_resolution_draft"
    ALL = [PUBLIC, INTERNAL_NOTE, SYSTEM_EVENT, AI_DRAFT]


class TicketComment(Base, TimestampMixin):
    __tablename__ = "ticket_comments"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    ticket_id = Column(String(36), ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False, index=True)
    author_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    comment_type = Column(String(50), default=CommentType.PUBLIC, nullable=False)
    content = Column(Text, nullable=False)

    # Relationships
    ticket = relationship("Ticket", back_populates="comments")
    author = relationship("User", back_populates="comments")

    def __repr__(self) -> str:
        return f"<Comment {self.id} on {self.ticket_id} ({self.comment_type})>"
