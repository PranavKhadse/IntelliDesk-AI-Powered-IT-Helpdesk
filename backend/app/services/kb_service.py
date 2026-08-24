"""Knowledge Base article management, retrieval, and search service."""

import math
import re
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, desc

from app.models.kb_article import KBArticle
from app.models.ticket import Category, Ticket
from app.models.user import User, UserRole
from app.schemas.kb_article import KBArticleCreate, KBArticleUpdate
from app.schemas.ai_grounding import GroundedArticleReference
from app.core.exceptions import NotFoundError, ForbiddenError, ValidationError


def slugify(text: str) -> str:
    """Generate a clean URL-friendly slug from title."""
    slug = re.sub(r'[^a-zA-Z0-9\s-]', '', text).strip().lower()
    slug = re.sub(r'[\s_-]+', '-', slug)
    return slug or "kb-article"


def generate_unique_slug(db: Session, title: str, custom_slug: Optional[str] = None, exclude_id: Optional[str] = None) -> str:
    """Generate a guaranteed-unique slug for a KB article."""
    base_slug = slugify(custom_slug) if custom_slug else slugify(title)
    slug = base_slug
    counter = 1

    while True:
        query = db.query(KBArticle).filter(KBArticle.slug == slug)
        if exclude_id:
            query = query.filter(KBArticle.id != exclude_id)
        if not query.first():
            return slug
        counter += 1
        slug = f"{base_slug}-{counter}"


def create_kb_article(db: Session, req: KBArticleCreate, author: User) -> KBArticle:
    """Create a new KB article. Only Agents and Admins can create articles."""
    if author.role not in [UserRole.AGENT, UserRole.ADMIN]:
        raise ForbiddenError("Only support agents and administrators can create knowledge base articles.")

    if req.category_id:
        category = db.query(Category).filter(Category.id == req.category_id).first()
        if not category:
            raise NotFoundError("Category", req.category_id)

    slug = generate_unique_slug(db, title=req.title, custom_slug=req.slug)
    tags_str = req.tags if isinstance(req.tags, str) else (",".join(req.tags) if req.tags else "")

    article = KBArticle(
        title=req.title,
        slug=slug,
        summary=req.summary,
        content=req.content,
        category_id=req.category_id,
        author_id=author.id,
        is_published=req.is_published,
        tags=tags_str,
        view_count=0,
        helpful_count=0,
    )
    db.add(article)
    db.commit()
    db.refresh(article)
    return get_kb_article_by_id_or_slug(db, article.id, current_user=author)


def get_kb_article_by_id_or_slug(
    db: Session,
    id_or_slug: str,
    current_user: Optional[User] = None,
    increment_view: bool = False,
) -> KBArticle:
    """Fetch article with category and author relationships, enforcing publication visibility."""
    article = db.query(KBArticle).options(
        joinedload(KBArticle.category),
        joinedload(KBArticle.author),
    ).filter(
        or_(KBArticle.id == id_or_slug, KBArticle.slug == id_or_slug)
    ).first()

    if not article:
        raise NotFoundError("KBArticle", id_or_slug)

    # End-users can only view published articles
    is_staff = current_user and current_user.role in [UserRole.AGENT, UserRole.ADMIN]
    if not is_staff and not article.is_published:
        raise NotFoundError("KBArticle", id_or_slug)

    if increment_view:
        article.view_count += 1
        db.commit()
        db.refresh(article)

    return article


def list_kb_articles(
    db: Session,
    current_user: Optional[User] = None,
    page: int = 1,
    page_size: int = 20,
    category_id: Optional[int] = None,
    tag: Optional[str] = None,
    search: Optional[str] = None,
    is_published: Optional[bool] = None,
) -> Tuple[List[KBArticle], int]:
    """List KB articles with filtering, pagination, and role-based visibility."""
    query = db.query(KBArticle).options(
        joinedload(KBArticle.category),
        joinedload(KBArticle.author),
    )

    is_staff = current_user and current_user.role in [UserRole.AGENT, UserRole.ADMIN]
    if not is_staff:
        # Non-staff can only see published articles
        query = query.filter(KBArticle.is_published == True)
    elif is_published is not None:
        query = query.filter(KBArticle.is_published == is_published)

    if category_id is not None:
        query = query.filter(KBArticle.category_id == category_id)

    if tag:
        tag_clean = tag.strip().lower()
        query = query.filter(KBArticle.tags.ilike(f"%{tag_clean}%"))

    if search:
        search_filter = f"%{search.strip()}%"
        query = query.filter(
            or_(
                KBArticle.title.ilike(search_filter),
                KBArticle.summary.ilike(search_filter),
                KBArticle.content.ilike(search_filter),
                KBArticle.tags.ilike(search_filter),
            )
        )

    total = query.count()
    items = query.order_by(desc(KBArticle.created_at)).offset((page - 1) * page_size).limit(page_size).all()
    return items, total


def update_kb_article(db: Session, article_id: str, req: KBArticleUpdate, actor: User) -> KBArticle:
    """Update article properties. Only Agents and Admins can update articles."""
    if actor.role not in [UserRole.AGENT, UserRole.ADMIN]:
        raise ForbiddenError("Only support agents and administrators can update knowledge base articles.")

    article = db.query(KBArticle).filter(KBArticle.id == article_id).first()
    if not article:
        raise NotFoundError("KBArticle", article_id)

    if req.category_id is not None:
        if req.category_id != 0:
            category = db.query(Category).filter(Category.id == req.category_id).first()
            if not category:
                raise NotFoundError("Category", req.category_id)
            article.category_id = category.id
        else:
            article.category_id = None

    if req.title is not None and req.title != article.title:
        article.title = req.title
        # If slug not explicitly given, regenerate slug from new title
        if req.slug is None:
            article.slug = generate_unique_slug(db, title=req.title, exclude_id=article.id)

    if req.slug is not None and req.slug != article.slug:
        article.slug = generate_unique_slug(db, title=article.title, custom_slug=req.slug, exclude_id=article.id)

    if req.summary is not None:
        article.summary = req.summary

    if req.content is not None:
        article.content = req.content

    if req.is_published is not None:
        article.is_published = req.is_published

    if req.tags is not None:
        article.tags = req.tags if isinstance(req.tags, str) else ",".join(req.tags)

    db.commit()
    db.refresh(article)
    return get_kb_article_by_id_or_slug(db, article.id, current_user=actor)


def delete_kb_article(db: Session, article_id: str, actor: User) -> None:
    """Delete a KB article. Only Admins can delete articles."""
    if actor.role != UserRole.ADMIN:
        raise ForbiddenError("Only administrators can delete knowledge base articles.")

    article = db.query(KBArticle).filter(KBArticle.id == article_id).first()
    if not article:
        raise NotFoundError("KBArticle", article_id)

    db.delete(article)
    db.commit()


def vote_kb_helpful(db: Session, article_id: str) -> int:
    """Increment helpful counter for an article."""
    article = db.query(KBArticle).filter(
        or_(KBArticle.id == article_id, KBArticle.slug == article_id)
    ).first()
    if not article:
        raise NotFoundError("KBArticle", article_id)

    article.helpful_count += 1
    db.commit()
    db.refresh(article)
    return article.helpful_count


def _extract_keywords(text: str) -> List[str]:
    """Tokenize and filter keywords for retrieval matching."""
    stop_words = {
        "a", "an", "and", "are", "as", "at", "be", "by", "for", "from",
        "has", "he", "in", "is", "it", "its", "of", "on", "that", "the",
        "to", "was", "were", "will", "with", "i", "my", "me", "we", "our",
        "you", "your", "can", "cannot", "cant", "help", "need", "issue",
        "please", "problem", "ticket", "having", "how", "what", "when", "where",
    }
    words = re.findall(r'[a-zA-Z0-9_-]{2,}', text.lower())
    return [w for w in words if w not in stop_words]


def _build_snippet(content: str, query_keywords: List[str], max_length: int = 240) -> str:
    """Extract a concise representative snippet around matched keywords."""
    if not content:
        return ""

    content_clean = " ".join(content.split())
    content_lower = content_clean.lower()

    # Find earliest matching keyword index
    best_pos = -1
    for kw in query_keywords:
        pos = content_lower.find(kw)
        if pos != -1 and (best_pos == -1 or pos < best_pos):
            best_pos = pos

    if best_pos == -1 or len(content_clean) <= max_length:
        return content_clean[:max_length] + ("..." if len(content_clean) > max_length else "")

    start = max(0, best_pos - 40)
    end = min(len(content_clean), start + max_length)
    snippet = content_clean[start:end].strip()

    if start > 0:
        snippet = "..." + snippet
    if end < len(content_clean):
        snippet = snippet + "..."

    return snippet


def search_relevant_articles(
    db: Session,
    query_text: str,
    category_id: Optional[int] = None,
    limit: int = 5,
    min_score: float = 0.20,
) -> List[Tuple[KBArticle, float, str]]:
    """
    Search and score relevant published KB articles using keyword frequency,
    title/tag weighting, and category affinity.
    """
    if not query_text or not query_text.strip():
        return []

    keywords = _extract_keywords(query_text)
    if not keywords:
        return []

    # Only published articles are retrieved for search and grounding
    candidates = db.query(KBArticle).options(
        joinedload(KBArticle.category)
    ).filter(
        KBArticle.is_published == True
    ).all()

    if not candidates:
        return []

    scored_results: List[Tuple[KBArticle, float, str]] = []

    for article in candidates:
        title_lower = article.title.lower()
        summary_lower = (article.summary or "").lower()
        content_lower = article.content.lower()
        tags_lower = (article.tags or "").lower()
        tag_list = [t.strip().lower() for t in tags_lower.split(",") if t.strip()]

        raw_score = 0.0
        matched_kw_count = 0

        # Exact query phrase match bonus
        clean_query = query_text.strip().lower()
        if len(clean_query) > 3:
            if clean_query in title_lower:
                raw_score += 15.0
            if clean_query in tags_lower:
                raw_score += 10.0
            if clean_query in summary_lower:
                raw_score += 8.0
            if clean_query in content_lower:
                raw_score += 5.0

        for kw in keywords:
            kw_matched = False
            # Title match (high weight)
            if kw in title_lower:
                raw_score += 5.0
                kw_matched = True
            # Tags match (high weight)
            if any(kw in t for t in tag_list):
                raw_score += 4.0
                kw_matched = True
            # Summary match
            if kw in summary_lower:
                raw_score += 2.5
                kw_matched = True
            # Content match
            if kw in content_lower:
                # Count frequency in content up to 3 occurrences
                freq = min(3, content_lower.count(kw))
                raw_score += 1.0 * freq
                kw_matched = True

            if kw_matched:
                matched_kw_count += 1

        if matched_kw_count == 0 and raw_score == 0.0:
            continue

        # Coverage factor (percentage of query keywords matched)
        coverage_ratio = matched_kw_count / max(1, len(keywords))
        raw_score *= (0.5 + 0.5 * coverage_ratio)

        # Category match boost
        if category_id and article.category_id == category_id:
            raw_score *= 1.25

        # Normalize score into [0.0, 1.0] scale using sigmoid-like curve
        # Typical raw_score ranges from 1.0 to ~30.0+
        normalized_score = round(1.0 - (1.0 / (1.0 + (raw_score / 6.0))), 3)

        if normalized_score >= min_score:
            snippet = _build_snippet(article.content or article.summary or article.title, keywords)
            scored_results.append((article, normalized_score, snippet))

    # Sort descending by score
    scored_results.sort(key=lambda x: x[1], reverse=True)
    return scored_results[:limit]


def get_relevant_articles_for_ticket(
    db: Session,
    ticket: Ticket,
    limit: int = 3,
    min_score: float = 0.25,
) -> List[GroundedArticleReference]:
    """Retrieve top published KB articles relevant to a ticket's title and description."""
    # Strict public ticket text only - excludes internal notes
    query_text = f"{ticket.title} {ticket.description}"
    search_matches = search_relevant_articles(
        db=db,
        query_text=query_text,
        category_id=ticket.category_id,
        limit=limit,
        min_score=min_score,
    )

    references: List[GroundedArticleReference] = []
    for article, score, snippet in search_matches:
        references.append(
            GroundedArticleReference(
                article_id=article.id,
                slug=article.slug,
                title=article.title,
                category=article.category.name if article.category else None,
                relevance_score=score,
                snippet=snippet,
            )
        )

    return references
