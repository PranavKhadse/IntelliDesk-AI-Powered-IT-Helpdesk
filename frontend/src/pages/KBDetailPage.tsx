import React, { useState, useEffect, useCallback } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { kbService } from '../services/kbService';
import { getApiErrorMessage } from '../services/api';
import type { KBArticle } from '../types';
import {
  ArrowLeft,
  BookOpen,
  Calendar,
  Eye,
  ThumbsUp,
  Edit3,
  Trash2,
  Layers,
  AlertCircle,
  Loader2,
  CheckCircle,
  Clock,
  Tag,
} from 'lucide-react';

export const KBDetailPage: React.FC = () => {
  const { articleIdOrSlug } = useParams<{ articleIdOrSlug: string }>();
  const { user } = useAuth();
  const navigate = useNavigate();

  const [article, setArticle] = useState<KBArticle | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [hasVotedHelpful, setHasVotedHelpful] = useState<boolean>(false);
  const [helpfulSuccessMsg, setHelpfulSuccessMsg] = useState<string | null>(null);
  const [isDeleting, setIsDeleting] = useState<boolean>(false);
  const [showDeleteModal, setShowDeleteModal] = useState<boolean>(false);

  const isStaff = user?.role === 'agent' || user?.role === 'admin';
  const isAdmin = user?.role === 'admin';

  const loadArticle = useCallback(async () => {
    if (!articleIdOrSlug) return;
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const data = await kbService.getArticle(articleIdOrSlug, true);
      setArticle(data);
    } catch (err: unknown) {
      console.error('Failed to load KB article:', err);
      setErrorMessage(getApiErrorMessage(err, 'Knowledge base article not found or unavailable.'));
    } finally {
      setIsLoading(false);
    }
  }, [articleIdOrSlug]);

  useEffect(() => {
    loadArticle();
  }, [loadArticle]);

  const handleHelpfulVote = async () => {
    if (!article || hasVotedHelpful) return;
    try {
      const res = await kbService.markHelpful(article.id);
      setArticle((prev) => (prev ? { ...prev, helpful_count: res.helpful_count } : null));
      setHasVotedHelpful(true);
      setHelpfulSuccessMsg('Thank you for your feedback!');
      setTimeout(() => setHelpfulSuccessMsg(null), 4000);
    } catch (err) {
      console.error('Failed to record helpful vote', err);
    }
  };

  const handleDeleteArticle = async () => {
    if (!article || !isAdmin || isDeleting) return;
    setIsDeleting(true);
    try {
      await kbService.deleteArticle(article.id);
      navigate('/kb', { replace: true });
    } catch (err: unknown) {
      console.error('Failed to delete article:', err);
      setErrorMessage(getApiErrorMessage(err, 'Failed to delete knowledge base article.'));
      setShowDeleteModal(false);
      setIsDeleting(false);
    }
  };

  const formatDate = (isoString?: string) => {
    if (!isoString) return '—';
    try {
      return new Date(isoString).toLocaleDateString(undefined, {
        month: 'long',
        day: 'numeric',
        year: 'numeric',
      });
    } catch {
      return isoString;
    }
  };

  if (isLoading) {
    return (
      <div className="kb-detail-loading">
        <Loader2 size={36} className="spinner" color="#38bdf8" />
        <p>Loading knowledge base article...</p>
      </div>
    );
  }

  if (errorMessage && !article) {
    return (
      <div className="kb-detail-error glass-card">
        <AlertCircle size={40} color="#f87171" />
        <h2>Article Unavailable</h2>
        <p>{errorMessage}</p>
        <Link to="/kb" className="btn btn-secondary">
          <ArrowLeft size={16} />
          <span>Back to Knowledge Base</span>
        </Link>
      </div>
    );
  }

  if (!article) return null;

  const tagList = article.tags
    ? article.tags.split(',').map((t) => t.trim()).filter(Boolean)
    : [];

  return (
    <div className="kb-detail-page">
      {/* Navigation Breadcrumb */}
      <div className="kb-detail-breadcrumb">
        <Link to="/kb" className="back-link">
          <ArrowLeft size={16} />
          <span>Back to Knowledge Base</span>
        </Link>
      </div>

      {/* Main Article Glass Card */}
      <article className="kb-detail-card glass-card">
        {/* Article Header */}
        <header className="kb-detail-header">
          <div className="kb-detail-category-row">
            {article.category ? (
              <span className="kb-category-pill">
                <Layers size={13} />
                <span>{article.category.name}</span>
              </span>
            ) : (
              <span className="kb-category-pill">General</span>
            )}

            {isStaff && (
              <span className={`kb-publish-badge ${article.is_published ? 'published' : 'draft'}`}>
                {article.is_published ? 'Published' : 'Draft'}
              </span>
            )}
          </div>

          <h1 className="kb-detail-title">{article.title}</h1>

          {/* Meta details & staff actions */}
          <div className="kb-detail-meta-actions-bar">
            <div className="kb-detail-meta-group">
              <div className="kb-detail-author-box">
                <div className="kb-author-avatar">
                  {article.author?.full_name ? article.author.full_name[0].toUpperCase() : 'S'}
                </div>
                <div className="kb-author-text">
                  <span className="kb-author-name">{article.author?.full_name || 'IT Support Team'}</span>
                  <span className="kb-author-role">Author ({article.author?.role || 'Staff'})</span>
                </div>
              </div>

              <div className="kb-meta-timestamps">
                <span title="Published Date">
                  <Calendar size={13} />
                  <span>Published {formatDate(article.created_at)}</span>
                </span>
                {article.updated_at && article.updated_at !== article.created_at && (
                  <span title="Updated Date">
                    <Clock size={13} />
                    <span>Updated {formatDate(article.updated_at)}</span>
                  </span>
                )}
              </div>
            </div>

            {/* Staff Controls */}
            {isStaff && (
              <div className="kb-staff-actions-cluster">
                <Link to={`/kb/${article.id}/edit`} className="btn btn-secondary btn-sm">
                  <Edit3 size={14} />
                  <span>Edit</span>
                </Link>

                {isAdmin && (
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm delete-action-btn"
                    onClick={() => setShowDeleteModal(true)}
                  >
                    <Trash2 size={14} color="#f87171" />
                    <span>Delete</span>
                  </button>
                )}
              </div>
            )}
          </div>
        </header>

        {/* Executive Summary / Lead Box */}
        {article.summary && (
          <div className="kb-lead-summary-box">
            <h3 className="kb-summary-heading">Overview</h3>
            <p>{article.summary}</p>
          </div>
        )}

        {/* Article Body Content */}
        <div className="kb-article-body">
          {article.content.split('\n\n').map((block, idx) => {
            if (block.startsWith('# ')) {
              return <h2 key={idx} className="kb-body-h2">{block.replace('# ', '')}</h2>;
            }
            if (block.startsWith('## ')) {
              return <h3 key={idx} className="kb-body-h3">{block.replace('## ', '')}</h3>;
            }
            if (block.startsWith('### ')) {
              return <h4 key={idx} className="kb-body-h4">{block.replace('### ', '')}</h4>;
            }
            if (block.startsWith('- ') || block.startsWith('* ')) {
              const items = block.split('\n').map((line) => line.replace(/^[-*]\s+/, ''));
              return (
                <ul key={idx} className="kb-body-list">
                  {items.map((item, itemIdx) => (
                    <li key={itemIdx}>{item}</li>
                  ))}
                </ul>
              );
            }
            return (
              <p key={idx} className="kb-body-paragraph">
                {block}
              </p>
            );
          })}
        </div>

        {/* Tags Section */}
        {tagList.length > 0 && (
          <div className="kb-detail-tags-section">
            <span className="kb-tags-label">
              <Tag size={14} />
              <span>Related Tags:</span>
            </span>
            <div className="kb-tags-cluster">
              {tagList.map((tag, idx) => (
                <Link
                  key={idx}
                  to={`/kb?tag=${encodeURIComponent(tag)}`}
                  className="kb-tag-pill"
                >
                  #{tag}
                </Link>
              ))}
            </div>
          </div>
        )}

        {/* Article Footer & Helpful Feedback Bar */}
        <footer className="kb-detail-footer">
          <div className="kb-helpful-feedback-box">
            <div className="helpful-question">
              <BookOpen size={18} color="#38bdf8" />
              <span>Was this article helpful?</span>
            </div>

            <div className="helpful-action-row">
              <button
                type="button"
                className={`btn btn-sm ${hasVotedHelpful ? 'btn-primary' : 'btn-secondary'} helpful-btn`}
                onClick={handleHelpfulVote}
                disabled={hasVotedHelpful}
              >
                <ThumbsUp size={14} />
                <span>{hasVotedHelpful ? 'Voted Helpful' : 'Yes, this helped'}</span>
                <span className="helpful-counter-badge">{article.helpful_count}</span>
              </button>

              {helpfulSuccessMsg && (
                <div className="helpful-toast">
                  <CheckCircle size={15} color="#10b981" />
                  <span>{helpfulSuccessMsg}</span>
                </div>
              )}
            </div>
          </div>

          <div className="kb-views-stat">
            <Eye size={14} />
            <span>{article.view_count} views</span>
          </div>
        </footer>
      </article>

      {/* Admin Delete Confirmation Modal */}
      {showDeleteModal && (
        <div className="modal-backdrop">
          <div className="modal-content glass-card">
            <div className="modal-header">
              <AlertCircle size={24} color="#f87171" />
              <h3>Confirm Article Deletion</h3>
            </div>
            <p>
              Are you sure you want to permanently delete <strong>"{article.title}"</strong>? This action cannot be undone.
            </p>
            <div className="modal-actions-row">
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => setShowDeleteModal(false)}
                disabled={isDeleting}
              >
                Cancel
              </button>
              <button
                type="button"
                className="btn btn-danger"
                onClick={handleDeleteArticle}
                disabled={isDeleting}
              >
                {isDeleting ? <Loader2 size={15} className="spinner" /> : <Trash2 size={15} />}
                <span>Delete Permanently</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
