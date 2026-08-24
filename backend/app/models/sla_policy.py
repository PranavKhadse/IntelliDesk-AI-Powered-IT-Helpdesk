from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import TimestampMixin


class SLAPolicy(Base, TimestampMixin):
    __tablename__ = "sla_policies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(String(255), nullable=True)
    
    # Matching Criteria
    priority = Column(String(50), nullable=True, index=True)  # e.g., 'critical', 'high', 'medium', 'low'
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="CASCADE"), nullable=True, index=True)
    
    # Target Durations (in hours)
    first_response_hours = Column(Float, nullable=False, default=4.0)
    resolution_hours = Column(Float, nullable=False, default=24.0)
    
    # Thresholds (0.0 to 1.0 scale, e.g. 0.75 = 75%)
    warning_threshold_pct = Column(Float, nullable=False, default=0.75)
    escalation_threshold_pct = Column(Float, nullable=False, default=0.90)
    
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    category = relationship("Category")

    def __repr__(self) -> str:
        return f"<SLAPolicy {self.name} (Priority: {self.priority}, Category: {self.category_id})>"
