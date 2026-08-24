from datetime import datetime
from typing import Optional, List, Union
from pydantic import BaseModel, Field, ConfigDict, field_validator


class KBArticleAuthorSummary(BaseModel):
    id: str
    full_name: str
    email: str
    role: str

    model_config = ConfigDict(from_attributes=True)


class KBArticleCategorySummary(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)


class KBArticleBase(BaseModel):
    title: str = Field(..., min_length=3, max_length=255)
    summary: Optional[str] = None
    content: str = Field(..., min_length=10)
    category_id: Optional[int] = None
    is_published: bool = True
    tags: Optional[Union[str, List[str]]] = ""
    slug: Optional[str] = Field(default=None, max_length=255)

    @field_validator("tags", mode="before")
    @classmethod
    def normalize_tags(cls, v):
        if isinstance(v, list):
            return ",".join([str(item).strip() for item in v if str(item).strip()])
        if isinstance(v, str):
            return v.strip()
        return ""


class KBArticleCreate(KBArticleBase):
    pass


class KBArticleUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=3, max_length=255)
    summary: Optional[str] = None
    content: Optional[str] = Field(default=None, min_length=10)
    category_id: Optional[int] = None
    is_published: Optional[bool] = None
    tags: Optional[Union[str, List[str]]] = None
    slug: Optional[str] = Field(default=None, max_length=255)

    @field_validator("tags", mode="before")
    @classmethod
    def normalize_tags(cls, v):
        if v is None:
            return None
        if isinstance(v, list):
            return ",".join([str(item).strip() for item in v if str(item).strip()])
        if isinstance(v, str):
            return v.strip()
        return ""


class KBArticleResponse(BaseModel):
    id: str
    title: str
    slug: str
    summary: Optional[str] = None
    content: str
    category_id: Optional[int] = None
    category: Optional[KBArticleCategorySummary] = None
    author_id: Optional[str] = None
    author: Optional[KBArticleAuthorSummary] = None
    is_published: bool
    tags: str
    view_count: int
    helpful_count: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class KBArticleListResponse(BaseModel):
    items: List[KBArticleResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class KBSearchResultItem(BaseModel):
    id: str
    title: str
    slug: str
    summary: Optional[str] = None
    category: Optional[str] = None
    tags: str = ""
    relevance_score: float = Field(ge=0.0, le=1.0)
    snippet: str


class KBSearchResponse(BaseModel):
    query: str
    items: List[KBSearchResultItem]
    total: int
