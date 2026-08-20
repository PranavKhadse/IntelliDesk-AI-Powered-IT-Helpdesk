from sqlalchemy import Column, String, Text, Boolean, Integer, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import TimestampMixin, generate_uuid


class KBArticle(Base, TimestampMixin):
    __tablename__ = "kb_articles"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    title = Column(String(255), nullable=False, index=True)
    slug = Column(String(255), unique=True, index=True, nullable=False)
    summary = Column(Text, nullable=True)
    content = Column(Text, nullable=False)
    
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    author_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    is_published = Column(Boolean, default=True, nullable=False, index=True)
    tags = Column(String(255), default="", nullable=False)  # Comma-separated tags
    view_count = Column(Integer, default=0, nullable=False)
    helpful_count = Column(Integer, default=0, nullable=False)

    # Relationships
    category = relationship("Category", back_populates="kb_articles")
    author = relationship("User", back_populates="kb_articles")

    def __repr__(self) -> str:
        return f"<KBArticle {self.slug}: {self.title}>"
