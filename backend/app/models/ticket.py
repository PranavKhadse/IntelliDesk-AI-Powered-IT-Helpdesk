from datetime import datetime
from sqlalchemy import Column, String, Integer, Text, Boolean, DateTime, Float, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import TimestampMixin, generate_uuid


class TicketStatus:
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    PENDING_CUSTOMER = "pending_customer"
    RESOLVED = "resolved"
    CLOSED = "closed"
    ALL = [OPEN, IN_PROGRESS, PENDING_CUSTOMER, RESOLVED, CLOSED]


class TicketPriority:
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    ALL = [LOW, MEDIUM, HIGH, CRITICAL]


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(String(255), nullable=True)
    default_sla_hours = Column(Integer, default=24, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    tickets = relationship("Ticket", back_populates="category")
    kb_articles = relationship("KBArticle", back_populates="category")

    def __repr__(self) -> str:
        return f"<Category {self.name}>"


class Ticket(Base, TimestampMixin):
    __tablename__ = "tickets"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    ticket_number = Column(String(20), unique=True, index=True, nullable=False)
    title = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=False)
    
    status = Column(String(50), default=TicketStatus.OPEN, nullable=False, index=True)
    priority = Column(String(50), default=TicketPriority.MEDIUM, nullable=False, index=True)
    
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    creator_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    assignee_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # ML / AI Enrichment Fields (Optional - Core functions without them)
    ai_suggested_category = Column(String(100), nullable=True)
    ai_suggested_priority = Column(String(50), nullable=True)
    ai_confidence_score = Column(Float, nullable=True)
    
    # SLA & Resolution Timestamps
    sla_due_at = Column(DateTime, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    closed_at = Column(DateTime, nullable=True)

    # Relationships
    category = relationship("Category", back_populates="tickets")
    creator = relationship("User", back_populates="created_tickets", foreign_keys=[creator_id])
    assignee = relationship("User", back_populates="assigned_tickets", foreign_keys=[assignee_id])
    comments = relationship("TicketComment", back_populates="ticket", cascade="all, delete-orphan", order_by="TicketComment.created_at")
    audit_logs = relationship("AuditLog", back_populates="ticket", cascade="all, delete-orphan", order_by="AuditLog.created_at.desc()")

    def __repr__(self) -> str:
        return f"<Ticket {self.ticket_number}: {self.title} ({self.status})>"
