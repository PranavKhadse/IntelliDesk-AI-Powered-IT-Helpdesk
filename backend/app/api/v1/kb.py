import math
from typing import Optional, List
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User, UserRole
from app.models.ticket import Category
from app.schemas.ticket import CategoryResponse
from app.schemas.kb_article import (
    KBArticleCreate,
    KBArticleUpdate,
    KBArticleResponse,
    KBArticleListResponse,
    KBSearchResultItem,
    KBSearchResponse,
)
from app.services.kb_service import (
    create_kb_article,
    get_kb_article_by_id_or_slug,
    list_kb_articles,
    update_kb_article,
    delete_kb_article,
    vote_kb_helpful,
    search_relevant_articles,
)

router = APIRouter(prefix="/kb", tags=["Knowledge Base"])


@router.get("/categories", response_model=List[CategoryResponse])
def get_kb_categories(db: Session = Depends(get_db)):
    """List active categories for knowledge base browsing."""
    return db.query(Category).filter(Category.is_active == True).all()


@router.get("/search", response_model=KBSearchResponse)
def search_kb(
    q: str = Query(..., min_length=1, description="Search query keywords"),
    category_id: Optional[int] = None,
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Search published KB articles with relevance scoring."""
    matches = search_relevant_articles(
        db=db,
        query_text=q,
        category_id=category_id,
        limit=limit,
        min_score=0.15,
    )
    items = [
        KBSearchResultItem(
            id=article.id,
            title=article.title,
            slug=article.slug,
            summary=article.summary,
            category=article.category.name if article.category else None,
            tags=article.tags or "",
            relevance_score=score,
            snippet=snippet,
        )
        for article, score, snippet in matches
    ]
    return KBSearchResponse(query=q, items=items, total=len(items))


@router.get("/articles", response_model=KBArticleListResponse)
def get_articles(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    category_id: Optional[int] = None,
    tag: Optional[str] = None,
    search: Optional[str] = None,
    is_published: Optional[bool] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List KB articles. End-users see published articles only; staff can filter by draft state."""
    items, total = list_kb_articles(
        db=db,
        current_user=current_user,
        page=page,
        page_size=page_size,
        category_id=category_id,
        tag=tag,
        search=search,
        is_published=is_published,
    )
    total_pages = math.ceil(total / page_size) if total > 0 else 1
    return KBArticleListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.post("/articles", response_model=KBArticleResponse, status_code=status.HTTP_201_CREATED)
def create_article(
    req: KBArticleCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new knowledge base article (Agent / Admin only)."""
    return create_kb_article(db, req, current_user)


@router.get("/articles/{id_or_slug}", response_model=KBArticleResponse)
def get_article(
    id_or_slug: str,
    increment_view: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get KB article by ID or slug."""
    return get_kb_article_by_id_or_slug(
        db=db,
        id_or_slug=id_or_slug,
        current_user=current_user,
        increment_view=increment_view,
    )


@router.patch("/articles/{article_id}", response_model=KBArticleResponse)
def update_article(
    article_id: str,
    req: KBArticleUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a knowledge base article (Agent / Admin only)."""
    return update_kb_article(db, article_id, req, current_user)


@router.delete("/articles/{article_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_article(
    article_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a knowledge base article (Admin only)."""
    delete_kb_article(db, article_id, current_user)


@router.post("/articles/{article_id}/helpful")
def mark_article_helpful(
    article_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upvote the helpfulness counter of a KB article."""
    count = vote_kb_helpful(db, article_id)
    return {"helpful_count": count}
