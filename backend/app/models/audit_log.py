from sqlalchemy import Column, String, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import TimestampMixin, generate_uuid


class AuditAction:
    CREATED = "created"
    STATUS_CHANGED = "status_changed"
    PRIORITY_CHANGED = "priority_changed"
    ASSIGNED = "assigned"
    COMMENT_ADDED = "comment_added"
    AI_TRIAGED = "ai_triaged"
    AI_RECOMMENDATION_ACCEPTED = "ai_recommendation_accepted"
    AI_RECOMMENDATION_REJECTED = "ai_recommendation_rejected"
    AI_SLA_RISK_ASSESSED = "ai_sla_risk_assessed"
    AI_ESCALATION_ACCEPTED = "ai_escalation_accepted"
    AI_ESCALATION_REJECTED = "ai_escalation_rejected"


class AuditLog(Base, TimestampMixin):
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    ticket_id = Column(String(36), ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False, index=True)
    actor_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    action = Column(String(50), nullable=False)
    
    previous_state = Column(Text, nullable=True)  # JSON or text description
    new_state = Column(Text, nullable=True)       # JSON or text description

    # Relationships
    ticket = relationship("Ticket", back_populates="audit_logs")
    actor = relationship("User")

    def __repr__(self) -> str:
        return f"<AuditLog {self.action} on {self.ticket_id}>"
