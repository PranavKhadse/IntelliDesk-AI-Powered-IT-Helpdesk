import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { kbService } from '../services/kbService';
import { getApiErrorMessage } from '../services/api';
import type { Category } from '../types';
import {
  ArrowLeft,
  Save,
  BookOpen,
  Layers,
  Tag,
  FileText,
  AlertCircle,
  Loader2,
  CheckCircle,
  Globe,
  Lock,
} from 'lucide-react';

export const KBCreateEditPage: React.FC = () => {
  const { articleIdOrSlug } = useParams<{ articleIdOrSlug: string }>();
  const isEditing = Boolean(articleIdOrSlug);
  const { user } = useAuth();
  const navigate = useNavigate();

  const [title, setTitle] = useState<string>('');
  const [slug, setSlug] = useState<string>('');
  const [categoryId, setCategoryId] = useState<string>('');
  const [summary, setSummary] = useState<string>('');
  const [content, setContent] = useState<string>('');
  const [tags, setTags] = useState<string>('');
  const [isPublished, setIsPublished] = useState<boolean>(true);

  const [categories, setCategories] = useState<Category[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(isEditing);
  const [isSaving, setIsSaving] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

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

  // Load existing article if in edit mode
  useEffect(() => {
    if (!isEditing || !articleIdOrSlug) return;
    const fetchArticle = async () => {
      setIsLoading(true);
      setErrorMessage(null);
      try {
        const data = await kbService.getArticle(articleIdOrSlug, false);
        setTitle(data.title);
        setSlug(data.slug);
        setCategoryId(data.category_id ? String(data.category_id) : '');
        setSummary(data.summary || '');
        setContent(data.content);
        setTags(data.tags || '');
        setIsPublished(data.is_published);
      } catch (err: unknown) {
        console.error('Failed to load article for editing:', err);
        setErrorMessage(getApiErrorMessage(err, 'Failed to load article for editing.'));
      } finally {
        setIsLoading(false);
      }
    };
    fetchArticle();
  }, [isEditing, articleIdOrSlug]);

  if (!isStaff) {
    return (
      <div className="kb-detail-error glass-card">
        <AlertCircle size={36} color="#f87171" />
        <h2>Access Denied</h2>
        <p>Only authorized support agents and administrators can author knowledge base articles.</p>
        <Link to="/kb" className="btn btn-secondary">
          <ArrowLeft size={16} />
          <span>Back to Knowledge Base</span>
        </Link>
      </div>
    );
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim() || !content.trim()) {
      setErrorMessage('Please provide both an article title and content.');
      return;
    }

    setIsSaving(true);
    setErrorMessage(null);
    setSuccessMessage(null);

    try {
      if (isEditing && articleIdOrSlug) {
        const updated = await kbService.updateArticle(articleIdOrSlug, {
          title: title.trim(),
          slug: slug.trim() || undefined,
          summary: summary.trim() || undefined,
          content: content.trim(),
          category_id: categoryId ? Number(categoryId) : undefined,
          is_published: isPublished,
          tags: tags.trim() || '',
        });
        setSuccessMessage('Article updated successfully.');
        setTimeout(() => navigate(`/kb/${updated.slug || updated.id}`), 1200);
      } else {
        const created = await kbService.createArticle({
          title: title.trim(),
          slug: slug.trim() || undefined,
          summary: summary.trim() || undefined,
          content: content.trim(),
          category_id: categoryId ? Number(categoryId) : undefined,
          is_published: isPublished,
          tags: tags.trim() || '',
        });
        setSuccessMessage('Article created successfully.');
        setTimeout(() => navigate(`/kb/${created.slug || created.id}`), 1200);
      }
    } catch (err: unknown) {
      console.error('Failed to save article:', err);
      setErrorMessage(getApiErrorMessage(err, 'Failed to save knowledge base article.'));
      setIsSaving(false);
    }
  };

  if (isLoading) {
    return (
      <div className="kb-detail-loading">
        <Loader2 size={36} className="spinner" color="#38bdf8" />
        <p>Loading article details...</p>
      </div>
    );
  }

  return (
    <div className="kb-create-edit-page">
      {/* Navigation Breadcrumb */}
      <div className="kb-detail-breadcrumb">
        <Link to="/kb" className="back-link">
          <ArrowLeft size={16} />
          <span>Back to Knowledge Base</span>
        </Link>
      </div>

      <div className="kb-form-container glass-card">
        <div className="kb-form-header">
          <div className="kb-form-title-cluster">
            <div className="kb-form-icon-badge">
              <BookOpen size={20} color="#38bdf8" />
            </div>
            <div>
              <h1 className="kb-form-title">
                {isEditing ? 'Edit Knowledge Article' : 'Create New Knowledge Article'}
              </h1>
              <p className="kb-form-sub">
                Publish verified troubleshooting instructions and procedures to assist support staff and ground AI recommendations.
              </p>
            </div>
          </div>
        </div>

        {errorMessage && (
          <div className="alert alert-error" style={{ marginBottom: '1.25rem' }}>
            <AlertCircle size={18} />
            <span>{errorMessage}</span>
          </div>
        )}

        {successMessage && (
          <div className="alert alert-success" style={{ marginBottom: '1.25rem' }}>
            <CheckCircle size={18} />
            <span>{successMessage}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="kb-editor-form">
          {/* Article Title */}
          <div className="form-group">
            <label className="form-label" htmlFor="kb-title">
              Article Title <span className="required-star">*</span>
            </label>
            <input
              id="kb-title"
              type="text"
              className="form-input"
              placeholder="e.g., VPN Configuration & Troubleshooting Guide"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              required
              minLength={3}
              maxLength={255}
            />
          </div>

          {/* 2-Column Row: Category and Custom Slug */}
          <div className="kb-form-grid-row">
            <div className="form-group">
              <label className="form-label" htmlFor="kb-category">
                <Layers size={14} /> Category
              </label>
              <select
                id="kb-category"
                className="form-select"
                value={categoryId}
                onChange={(e) => setCategoryId(e.target.value)}
              >
                <option value="">— General / Uncategorized —</option>
                {categories.map((cat) => (
                  <option key={cat.id} value={cat.id}>
                    {cat.name}
                  </option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label className="form-label" htmlFor="kb-slug">
                URL Slug <span className="form-hint-inline">(Optional override)</span>
              </label>
              <input
                id="kb-slug"
                type="text"
                className="form-input"
                placeholder="e.g., vpn-troubleshooting-guide"
                value={slug}
                onChange={(e) => setSlug(e.target.value)}
              />
            </div>
          </div>

          {/* Summary / Excerpt */}
          <div className="form-group">
            <label className="form-label" htmlFor="kb-summary">
              <FileText size={14} /> Summary / Overview Excerpt
            </label>
            <textarea
              id="kb-summary"
              className="form-textarea"
              rows={2}
              placeholder="A brief 1-2 sentence overview shown in search results and article header..."
              value={summary}
              onChange={(e) => setSummary(e.target.value)}
            />
          </div>

          {/* Content Body */}
          <div className="form-group">
            <label className="form-label" htmlFor="kb-content">
              Article Content <span className="required-star">*</span>
            </label>
            <textarea
              id="kb-content"
              className="form-textarea kb-content-textarea"
              rows={12}
              placeholder="Write the full verified troubleshooting guide, resolution steps, prerequisites, or policies..."
              value={content}
              onChange={(e) => setContent(e.target.value)}
              required
              minLength={10}
            />
            <p className="form-hint">
              Supports markdown headings (<code># Heading 1</code>, <code>## Heading 2</code>) and bullet lists (<code>- item</code>).
            </p>
          </div>

          {/* Tags */}
          <div className="form-group">
            <label className="form-label" htmlFor="kb-tags">
              <Tag size={14} /> Tags <span className="form-hint-inline">(Comma-separated keywords)</span>
            </label>
            <input
              id="kb-tags"
              type="text"
              className="form-input"
              placeholder="e.g., vpn, network, wifi, macos, okta"
              value={tags}
              onChange={(e) => setTags(e.target.value)}
            />
          </div>

          {/* Publication Status Toggle */}
          <div className="kb-publication-toggle-box">
            <div className="toggle-meta">
              <div className="toggle-title-row">
                {isPublished ? <Globe size={16} color="#38bdf8" /> : <Lock size={16} color="#fbbf24" />}
                <span className="toggle-label">{isPublished ? 'Published' : 'Draft / Unpublished'}</span>
              </div>
              <p className="toggle-sub">
                {isPublished
                  ? 'Article is visible to all company users and used for AI Knowledge Grounding.'
                  : 'Article is saved as a staff-only draft and will not be visible to standard users or AI grounding.'}
              </p>
            </div>
            <label className="switch-wrapper">
              <input
                type="checkbox"
                checked={isPublished}
                onChange={(e) => setIsPublished(e.target.checked)}
              />
              <span className="switch-slider"></span>
            </label>
          </div>

          {/* Actions Bar */}
          <div className="kb-form-actions-row">
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => navigate('/kb')}
              disabled={isSaving}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={isSaving || !title.trim() || !content.trim()}
            >
              {isSaving ? (
                <>
                  <Loader2 size={16} className="spinner" />
                  <span>Saving Article...</span>
                </>
              ) : (
                <>
                  <Save size={16} />
                  <span>{isEditing ? 'Save Changes' : 'Publish Article'}</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
