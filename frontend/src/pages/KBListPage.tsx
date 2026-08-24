import React, { useState, useEffect, useCallback } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { kbService } from '../services/kbService';
import { getApiErrorMessage } from '../services/api';
import type { KBArticle, Category } from '../types';
import {
  BookOpen,
  Search,
  PlusCircle,
  Eye,
  ThumbsUp,
  Clock,
  Layers,
  ChevronLeft,
  ChevronRight,
  Loader2,
  AlertCircle,
  FileText,
  X,
} from 'lucide-react';

export const KBListPage: React.FC = () => {
  const { user } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();

  const [articles, setArticles] = useState<KBArticle[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Filter and pagination states from query params
  const searchQuery = searchParams.get('q') || '';
  const selectedCategoryId = searchParams.get('category') ? Number(searchParams.get('category')) : undefined;
  const selectedTag = searchParams.get('tag') || '';
  const publicationFilter = searchParams.get('status') || 'all'; // 'all' | 'published' | 'draft'
  const currentPage = Number(searchParams.get('page') || '1');

  const [totalArticles, setTotalArticles] = useState<number>(0);
  const [totalPages, setTotalPages] = useState<number>(1);
  const [searchInput, setSearchInput] = useState<string>(searchQuery);

  const isStaff = user?.role === 'agent' || user?.role === 'admin';

  // Load categories
  useEffect(() => {
    const fetchCategories = async () => {
      try {
        const cats = await kbService.getCategories();
        setCategories(cats);
      } catch (err) {
        console.error('Failed to load categories:', err);
      }
    };
    fetchCategories();
  }, []);

  // Fetch articles
  const loadArticles = useCallback(async () => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      let isPublishedParam: boolean | undefined = undefined;
      if (isStaff) {
        if (publicationFilter === 'published') isPublishedParam = true;
        if (publicationFilter === 'draft') isPublishedParam = false;
      }

      const res = await kbService.getArticles({
        page: currentPage,
        page_size: 12,
        category_id: selectedCategoryId,
        tag: selectedTag || undefined,
        search: searchQuery || undefined,
        is_published: isPublishedParam,
      });

      setArticles(res.items);
      setTotalArticles(res.total);
      setTotalPages(res.total_pages);
    } catch (err: unknown) {
      console.error('Failed to load KB articles:', err);
      setErrorMessage(getApiErrorMessage(err, 'Failed to retrieve knowledge base articles.'));
    } finally {
      setIsLoading(false);
    }
  }, [currentPage, selectedCategoryId, selectedTag, searchQuery, publicationFilter, isStaff]);

  useEffect(() => {
    loadArticles();
  }, [loadArticles]);

  // Update query params helper
  const updateParams = (updates: Record<string, string | null>) => {
    const newParams = new URLSearchParams(searchParams);
    Object.entries(updates).forEach(([key, value]) => {
      if (value === null || value === '') {
        newParams.delete(key);
      } else {
        newParams.set(key, value);
      }
    });
    // Reset page to 1 whenever filters change, unless page itself is updated
    if (!('page' in updates)) {
      newParams.set('page', '1');
    }
    setSearchParams(newParams);
  };

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    updateParams({ q: searchInput.trim() || null });
  };

  const handleClearSearch = () => {
    setSearchInput('');
    updateParams({ q: null });
  };

  const formatDate = (isoString?: string) => {
    if (!isoString) return '—';
    try {
      return new Date(isoString).toLocaleDateString(undefined, {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
      });
    } catch {
      return isoString;
    }
  };

  return (
    <div className="kb-page-container">
      {/* Knowledge Base Hero Header */}
      <div className="kb-hero-banner glass-card">
        <div className="kb-hero-content">
          <div className="kb-badge-row">
            <span className="kb-hero-badge">
              <BookOpen size={14} />
              <span>Verified Knowledge Base</span>
            </span>
            <span className="kb-hero-count">{totalArticles} Articles Available</span>
          </div>

          <h1 className="kb-hero-title">How can we help you today?</h1>
          <p className="kb-hero-subtitle">
            Search curated troubleshooting guides, company IT setups, and verified answers grounded in official documentation.
          </p>

          {/* Search Form */}
          <form onSubmit={handleSearchSubmit} className="kb-hero-search-form">
            <div className="kb-search-input-wrapper">
              <Search size={20} className="kb-search-icon" />
              <input
                type="text"
                className="kb-search-input"
                placeholder="Search by keywords, error codes, topics, or system names..."
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
              />
              {searchInput && (
                <button
                  type="button"
                  className="kb-search-clear-btn"
                  onClick={handleClearSearch}
                  title="Clear search"
                >
                  <X size={16} />
                </button>
              )}
            </div>
            <button type="submit" className="btn btn-primary kb-search-submit-btn">
              <span>Search Knowledge</span>
            </button>
          </form>
        </div>
      </div>

      {/* Filter and Control Bar */}
      <div className="kb-controls-bar glass-card">
        {/* Category Pills */}
        <div className="kb-category-pills-row">
          <button
            type="button"
            className={`category-pill-btn ${selectedCategoryId === undefined ? 'active' : ''}`}
            onClick={() => updateParams({ category: null })}
          >
            All Categories
          </button>
          {categories.map((cat) => (
            <button
              key={cat.id}
              type="button"
              className={`category-pill-btn ${selectedCategoryId === cat.id ? 'active' : ''}`}
              onClick={() => updateParams({ category: String(cat.id) })}
            >
              {cat.name}
            </button>
          ))}
        </div>

        {/* Staff controls & Tag badges */}
        <div className="kb-actions-subrow">
          <div className="kb-filter-tags-group">
            {selectedTag && (
              <span className="active-tag-chip">
                <span>Tag: {selectedTag}</span>
                <button
                  type="button"
                  onClick={() => updateParams({ tag: null })}
                  aria-label="Remove tag filter"
                >
                  <X size={13} />
                </button>
              </span>
            )}

            {searchQuery && (
              <span className="active-tag-chip">
                <span>Query: "{searchQuery}"</span>
                <button
                  type="button"
                  onClick={() => updateParams({ q: null })}
                  aria-label="Remove query filter"
                >
                  <X size={13} />
                </button>
              </span>
            )}

            {isStaff && (
              <div className="kb-status-selector">
                <button
                  type="button"
                  className={`status-filter-btn ${publicationFilter === 'all' ? 'active' : ''}`}
                  onClick={() => updateParams({ status: 'all' })}
                >
                  All Status
                </button>
                <button
                  type="button"
                  className={`status-filter-btn ${publicationFilter === 'published' ? 'active' : ''}`}
                  onClick={() => updateParams({ status: 'published' })}
                >
                  Published
                </button>
                <button
                  type="button"
                  className={`status-filter-btn ${publicationFilter === 'draft' ? 'active' : ''}`}
                  onClick={() => updateParams({ status: 'draft' })}
                >
                  Drafts
                </button>
              </div>
            )}
          </div>

          {/* Create Article Button for Staff */}
          {isStaff && (
            <Link to="/kb/new" className="btn btn-primary btn-sm kb-create-btn">
              <PlusCircle size={16} />
              <span>Create Article</span>
            </Link>
          )}
        </div>
      </div>

      {/* Error Alert */}
      {errorMessage && (
        <div className="alert alert-error" style={{ marginBottom: '1.5rem' }}>
          <AlertCircle size={18} />
          <span>{errorMessage}</span>
        </div>
      )}

      {/* Loading State */}
      {isLoading ? (
        <div className="kb-loading-box">
          <Loader2 size={36} className="spinner" color="#38bdf8" />
          <p>Retrieving knowledge base articles...</p>
        </div>
      ) : articles.length === 0 ? (
        /* Empty State */
        <div className="kb-empty-box glass-card">
          <FileText size={48} color="#64748b" />
          <h3>No Knowledge Base Articles Found</h3>
          <p>
            {searchQuery || selectedCategoryId || selectedTag || publicationFilter !== 'all'
              ? 'No articles match your current search and filter criteria. Try resetting filters.'
              : 'There are currently no knowledge base articles published.'}
          </p>
          <div className="kb-empty-actions">
            {(searchQuery || selectedCategoryId || selectedTag || publicationFilter !== 'all') && (
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={() => setSearchParams(new URLSearchParams())}
              >
                Reset All Filters
              </button>
            )}
            {isStaff && (
              <Link to="/kb/new" className="btn btn-primary btn-sm">
                <PlusCircle size={15} />
                <span>Create New Article</span>
              </Link>
            )}
          </div>
        </div>
      ) : (
        /* Articles Grid */
        <div className="kb-articles-grid">
          {articles.map((article) => {
            const tagList = article.tags
              ? article.tags.split(',').map((t) => t.trim()).filter(Boolean)
              : [];

            return (
              <Link
                key={article.id}
                to={`/kb/${article.slug || article.id}`}
                className="kb-article-card glass-card"
              >
                <div className="kb-card-header">
                  <div className="kb-card-category-row">
                    {article.category ? (
                      <span className="kb-card-category-pill">
                        <Layers size={12} />
                        <span>{article.category.name}</span>
                      </span>
                    ) : (
                      <span className="kb-card-category-pill">General</span>
                    )}

                    {isStaff && (
                      <span
                        className={`kb-publish-badge ${article.is_published ? 'published' : 'draft'}`}
                      >
                        {article.is_published ? 'Published' : 'Draft'}
                      </span>
                    )}
                  </div>
                </div>

                <h3 className="kb-card-title">{article.title}</h3>

                <p className="kb-card-snippet">
                  {article.summary || article.content.slice(0, 140) + '...'}
                </p>

                {tagList.length > 0 && (
                  <div className="kb-card-tags-row">
                    {tagList.slice(0, 3).map((tag, idx) => (
                      <span key={idx} className="kb-tag-mini-pill">
                        #{tag}
                      </span>
                    ))}
                    {tagList.length > 3 && (
                      <span className="kb-tag-more-pill">+{tagList.length - 3}</span>
                    )}
                  </div>
                )}

                <div className="kb-card-footer">
                  <div className="kb-card-author-meta">
                    <span className="kb-card-author-name">
                      {article.author?.full_name || 'Staff'}
                    </span>
                    <span className="kb-card-date">
                      <Clock size={11} />
                      <span>{formatDate(article.created_at)}</span>
                    </span>
                  </div>

                  <div className="kb-card-stats-row">
                    <span className="kb-stat-pill" title="Views">
                      <Eye size={12} />
                      <span>{article.view_count}</span>
                    </span>
                    <span className="kb-stat-pill" title="Helpful votes">
                      <ThumbsUp size={12} />
                      <span>{article.helpful_count}</span>
                    </span>
                  </div>
                </div>
              </Link>
            );
          })}
        </div>
      )}

      {/* Pagination */}
      {!isLoading && totalPages > 1 && (
        <div className="kb-pagination-bar">
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            disabled={currentPage <= 1}
            onClick={() => updateParams({ page: String(currentPage - 1) })}
          >
            <ChevronLeft size={16} />
            <span>Previous</span>
          </button>
          <span className="pagination-info">
            Page {currentPage} of {totalPages}
          </span>
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            disabled={currentPage >= totalPages}
            onClick={() => updateParams({ page: String(currentPage + 1) })}
          >
            <span>Next</span>
            <ChevronRight size={16} />
          </button>
        </div>
      )}
    </div>
  );
};
