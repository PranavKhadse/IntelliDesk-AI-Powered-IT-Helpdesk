import React, { useState, useEffect, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { ticketService } from '../services/ticketService';
import { getApiErrorMessage } from '../services/api';
import type {
  TicketDetail,
  Category,
  AgentSummary,
  TicketStatus,
  TicketPriority,
  CommentType,
} from '../types';
import {
  ArrowLeft,
  Clock,
  User,
  Shield,
  Send,
  MessageSquare,
  History,
  Lock,
  Layers,
  Flag,
  AlertCircle,
  Loader2,
  Edit3,
  Save,
  X,
  CheckCircle,
} from 'lucide-react';

export const TicketDetailPage: React.FC = () => {
  const { ticketId } = useParams<{ ticketId: string }>();
  const { user } = useAuth();

  const [ticket, setTicket] = useState<TicketDetail | null>(null);
  const [categories, setCategories] = useState<Category[]>([]);
  const [agents, setAgents] = useState<AgentSummary[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Comment state
  const [commentContent, setCommentContent] = useState<string>('');
  const [commentType, setCommentType] = useState<CommentType>('public');
  const [isSubmittingComment, setIsSubmittingComment] = useState<boolean>(false);
  const [commentError, setCommentError] = useState<string | null>(null);

  // Staff update controls state
  const [selectedStatus, setSelectedStatus] = useState<TicketStatus>('open');
  const [selectedPriority, setSelectedPriority] = useState<TicketPriority>('medium');
  const [selectedAssignee, setSelectedAssignee] = useState<string>('');
  const [selectedCategory, setSelectedCategory] = useState<string>('');
  const [isUpdatingStaffFields, setIsUpdatingStaffFields] = useState<boolean>(false);
  const [updateSuccessMsg, setUpdateSuccessMsg] = useState<string | null>(null);

  // User edit title/description state
  const [isEditingContent, setIsEditingContent] = useState<boolean>(false);
  const [editTitle, setEditTitle] = useState<string>('');
  const [editDescription, setEditDescription] = useState<string>('');
  const [isSavingContent, setIsSavingContent] = useState<boolean>(false);

  const isStaff = user?.role === 'agent' || user?.role === 'admin';
  const isCreator = user?.id === ticket?.creator_id;
  const canUserEdit = isCreator && user?.role === 'user' && ticket?.status === 'open';

  // Load ticket details
  const loadTicket = useCallback(async () => {
    if (!ticketId) return;
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const data = await ticketService.getTicketDetail(ticketId);
      setTicket(data);
      setSelectedStatus(data.status);
      setSelectedPriority(data.priority);
      setSelectedAssignee(data.assignee_id || '');
      setSelectedCategory(data.category_id ? String(data.category_id) : '');
      setEditTitle(data.title);
      setEditDescription(data.description);
    } catch (err: unknown) {
      console.error('Failed to load ticket:', err);
      const msg = getApiErrorMessage(err, 'Failed to retrieve ticket details.');
      setErrorMessage(msg);
    } finally {
      setIsLoading(false);
    }
  }, [ticketId]);

  useEffect(() => {
    loadTicket();
  }, [loadTicket]);

  // Load staff options (agents and categories)
  useEffect(() => {
    const loadOptions = async () => {
      try {
        const cats = await ticketService.getCategories();
        setCategories(cats);
        if (isStaff) {
          const agentList = await ticketService.getAgents();
          setAgents(agentList);
        }
      } catch (err) {
        console.error('Failed to load options:', err);
      }
    };
    loadOptions();
  }, [isStaff]);

  // Handle Comment Submission
  const handleCommentSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!ticket || !commentContent.trim()) return;

    setIsSubmittingComment(true);
    setCommentError(null);
    try {
      await ticketService.addComment(ticket.id, {
        content: commentContent.trim(),
        comment_type: isStaff ? commentType : 'public',
      });
      setCommentContent('');
      // Reload ticket to refresh comment timeline and status transition
      await loadTicket();
    } catch (err: unknown) {
      const msg = getApiErrorMessage(err, 'Failed to post comment.');
      setCommentError(msg);
    } finally {
      setIsSubmittingComment(false);
    }
  };

  // Handle Staff Ticket Updates (Status, Priority, Assignee, Category)
  const handleStaffUpdate = async () => {
    if (!ticket) return;
    setIsUpdatingStaffFields(true);
    setUpdateSuccessMsg(null);
    setErrorMessage(null);
    try {
      await ticketService.updateTicket(ticket.id, {
        status: selectedStatus,
        priority: selectedPriority,
        assignee_id: selectedAssignee || null,
        category_id: selectedCategory ? Number(selectedCategory) : undefined,
      });
      setUpdateSuccessMsg('Ticket updated successfully.');
      setTimeout(() => setUpdateSuccessMsg(null), 4000);
      await loadTicket();
    } catch (err: unknown) {
      const msg = getApiErrorMessage(err, 'Failed to update ticket properties.');
      setErrorMessage(msg);
    } finally {
      setIsUpdatingStaffFields(false);
    }
  };

  // Handle User Edit Content (Title/Description)
  const handleSaveContent = async () => {
    if (!ticket) return;
    if (!editTitle.trim() || !editDescription.trim()) return;

    setIsSavingContent(true);
    setErrorMessage(null);
    try {
      await ticketService.updateTicket(ticket.id, {
        title: editTitle.trim(),
        description: editDescription.trim(),
      });
      setIsEditingContent(false);
      await loadTicket();
    } catch (err: unknown) {
      const msg = getApiErrorMessage(err, 'Failed to save ticket changes.');
      setErrorMessage(msg);
    } finally {
      setIsSavingContent(false);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'open':
        return <span className="badge badge-open">Open</span>;
      case 'in_progress':
        return <span className="badge badge-in_progress">In Progress</span>;
      case 'pending_customer':
        return <span className="badge badge-pending_customer">Pending</span>;
      case 'resolved':
        return <span className="badge badge-resolved">Resolved</span>;
      case 'closed':
        return <span className="badge badge-closed">Closed</span>;
      default:
        return <span className="badge">{status}</span>;
    }
  };

  const getPriorityBadge = (priority: string) => {
    switch (priority) {
      case 'critical':
        return <span className="badge badge-critical">Critical</span>;
      case 'high':
        return <span className="badge badge-high">High</span>;
      case 'medium':
        return <span className="badge badge-medium">Medium</span>;
      case 'low':
        return <span className="badge badge-low">Low</span>;
      default:
        return <span className="badge">{priority}</span>;
    }
  };

  const formatDate = (isoString?: string) => {
    if (!isoString) return '—';
    try {
      const date = new Date(isoString);
      return date.toLocaleDateString(undefined, {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return isoString;
    }
  };

  if (isLoading) {
    return (
      <div className="ticket-detail-loading">
        <Loader2 size={36} className="spinner" color="#3b82f6" />
        <p>Retrieving ticket details from database...</p>
      </div>
    );
  }

  if (errorMessage && !ticket) {
    return (
      <div className="ticket-detail-error glass-card">
        <AlertCircle size={36} color="#f87171" />
        <h2>Unable to Access Ticket</h2>
        <p>{errorMessage}</p>
        <Link to="/tickets" className="btn btn-secondary">
          <ArrowLeft size={16} />
          <span>Back to Tickets</span>
        </Link>
      </div>
    );
  }

  if (!ticket) return null;

  return (
    <div className="ticket-detail-page">
      {/* Navigation Breadcrumb */}
      <div className="page-nav-back">
        <Link to="/tickets" className="back-link">
          <ArrowLeft size={16} />
          <span>Back to Tickets</span>
        </Link>
      </div>

      {/* Main Ticket Banner Header */}
      <div className="ticket-main-header glass-card">
        <div className="header-left-col">
          <div className="ticket-id-headline">
            <span className="ticket-id-tag">{ticket.ticket_number}</span>
            <div className="ticket-badge-cluster">
              {getStatusBadge(ticket.status)}
              {getPriorityBadge(ticket.priority)}
              {ticket.category && <span className="category-pill">{ticket.category.name}</span>}
            </div>
          </div>

          {!isEditingContent ? (
            <h1 className="ticket-headline-title">{ticket.title}</h1>
          ) : (
            <div className="edit-title-field">
              <input
                type="text"
                className="form-input"
                value={editTitle}
                onChange={(e) => setEditTitle(e.target.value)}
                placeholder="Ticket Title"
              />
            </div>
          )}

          <div className="ticket-meta-info-row">
            <span>
              Opened by <strong>{ticket.creator?.full_name || 'User'}</strong> on {formatDate(ticket.created_at)}
            </span>
            {ticket.updated_at && ticket.updated_at !== ticket.created_at && (
              <span>• Last activity {formatDate(ticket.updated_at)}</span>
            )}
          </div>
        </div>

        {/* User Edit Button */}
        {canUserEdit && !isEditingContent && (
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={() => setIsEditingContent(true)}
          >
            <Edit3 size={15} />
            <span>Edit Details</span>
          </button>
        )}
      </div>

      {/* Update Success Alert */}
      {updateSuccessMsg && (
        <div className="alert alert-success" style={{ marginBottom: '1rem' }}>
          <CheckCircle size={18} className="alert-icon" />
          <span>{updateSuccessMsg}</span>
        </div>
      )}

      {/* 2-Column Main Layout */}
      <div className="ticket-detail-grid">
        {/* Left Column: Description, Timeline, Add Comment */}
        <div className="ticket-timeline-col">
          {/* Ticket Description Card */}
          <div className="ticket-description-card glass-card">
            <h3 className="card-section-title">Issue Description</h3>
            {!isEditingContent ? (
              <div className="ticket-description-body">
                {ticket.description.split('\n').map((paragraph, idx) => (
                  <p key={idx}>{paragraph}</p>
                ))}
              </div>
            ) : (
              <div className="edit-description-field">
                <textarea
                  className="form-textarea"
                  rows={6}
                  value={editDescription}
                  onChange={(e) => setEditDescription(e.target.value)}
                />
                <div className="edit-actions-row">
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm"
                    onClick={() => {
                      setIsEditingContent(false);
                      setEditTitle(ticket.title);
                      setEditDescription(ticket.description);
                    }}
                    disabled={isSavingContent}
                  >
                    <X size={14} />
                    <span>Cancel</span>
                  </button>
                  <button
                    type="button"
                    className="btn btn-primary btn-sm"
                    onClick={handleSaveContent}
                    disabled={isSavingContent}
                  >
                    {isSavingContent ? <Loader2 size={14} className="spinner" /> : <Save size={14} />}
                    <span>Save Changes</span>
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Activity / Timeline (Comments & Audit Events) */}
          <div className="ticket-activity-section glass-card">
            <div className="activity-section-header">
              <div className="header-with-icon">
                <MessageSquare size={18} color="#60a5fa" />
                <h3 className="card-section-title">Activity & Conversation</h3>
              </div>
              <span className="comment-count-pill">{ticket.comments.length} Comments</span>
            </div>

            {/* Comments List */}
            {ticket.comments.length === 0 ? (
              <div className="no-comments-box">
                <p>No comments on this ticket yet.</p>
              </div>
            ) : (
              <div className="comments-stream">
                {ticket.comments.map((comment) => {
                  const isInternal = comment.comment_type === 'internal_note';
                  return (
                    <div
                      key={comment.id}
                      className={`comment-bubble ${isInternal ? 'internal-note-bubble' : 'public-comment-bubble'}`}
                    >
                      <div className="comment-bubble-header">
                        <div className="comment-author-info">
                          <div className="comment-author-avatar">
                            {comment.author?.full_name ? comment.author.full_name[0].toUpperCase() : 'U'}
                          </div>
                          <div className="comment-author-meta">
                            <span className="comment-author-name">{comment.author?.full_name || 'System / Staff'}</span>
                            <span className="comment-timestamp">{formatDate(comment.created_at)}</span>
                          </div>
                        </div>

                        {isInternal && (
                          <div className="internal-note-badge" title="Only visible to IT Support Agents & Admins">
                            <Lock size={12} />
                            <span>Internal Agent Note</span>
                          </div>
                        )}
                      </div>

                      <div className="comment-bubble-content">
                        {comment.content.split('\n').map((line, idx) => (
                          <p key={idx}>{line}</p>
                        ))}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}

            {/* Add Comment Form */}
            <form onSubmit={handleCommentSubmit} className="add-comment-form">
              <h4 className="add-comment-heading">Add a Response</h4>

              {commentError && (
                <div className="alert alert-error" style={{ marginBottom: '0.75rem' }}>
                  <AlertCircle size={16} />
                  <span>{commentError}</span>
                </div>
              )}

              {/* Staff internal note toggle */}
              {isStaff && (
                <div className="comment-type-selector">
                  <button
                    type="button"
                    className={`comment-type-btn ${commentType === 'public' ? 'active public' : ''}`}
                    onClick={() => setCommentType('public')}
                  >
                    <MessageSquare size={14} />
                    <span>Public Reply</span>
                  </button>
                  <button
                    type="button"
                    className={`comment-type-btn ${commentType === 'internal_note' ? 'active internal' : ''}`}
                    onClick={() => setCommentType('internal_note')}
                  >
                    <Lock size={14} />
                    <span>Internal Note (Staff only)</span>
                  </button>
                </div>
              )}

              <textarea
                className="form-textarea comment-input"
                rows={3}
                placeholder={
                  isStaff && commentType === 'internal_note'
                    ? 'Write an internal note visible only to support agents...'
                    : 'Write a response to the customer / IT team...'
                }
                value={commentContent}
                onChange={(e) => setCommentContent(e.target.value)}
                disabled={isSubmittingComment}
              />

              <div className="comment-submit-row">
                <button
                  type="submit"
                  className={`btn ${commentType === 'internal_note' ? 'btn-secondary' : 'btn-primary'}`}
                  disabled={isSubmittingComment || !commentContent.trim()}
                >
                  {isSubmittingComment ? (
                    <>
                      <Loader2 size={16} className="spinner" />
                      <span>Sending...</span>
                    </>
                  ) : (
                    <>
                      <Send size={15} />
                      <span>{commentType === 'internal_note' ? 'Post Internal Note' : 'Send Reply'}</span>
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>

          {/* Audit Trail Timeline */}
          {ticket.audit_logs && ticket.audit_logs.length > 0 && (
            <div className="audit-logs-card glass-card">
              <div className="header-with-icon" style={{ marginBottom: '1rem' }}>
                <History size={17} color="#94a3b8" />
                <h3 className="card-section-title">Audit History</h3>
              </div>
              <div className="audit-timeline-list">
                {ticket.audit_logs.map((log) => (
                  <div key={log.id} className="audit-log-item">
                    <span className="audit-dot"></span>
                    <div className="audit-log-content">
                      <span className="audit-action-text">
                        <strong>{log.actor?.full_name || 'System'}</strong> performed action{' '}
                        <code className="audit-action-tag">{log.action}</code>
                      </span>
                      <span className="audit-time">{formatDate(log.created_at)}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Right Column: Staff Controls & Ticket Metadata */}
        <div className="ticket-sidebar-col">
          {/* Staff Quick Actions (Status, Priority, Assignee) */}
          {isStaff && (
            <div className="staff-control-card glass-card">
              <div className="sidebar-card-header">
                <Shield size={17} color="#fbbf24" />
                <h3>Staff Triage & Controls</h3>
              </div>

              <div className="staff-form-group">
                <label className="sidebar-field-label">Ticket Status</label>
                <select
                  className="form-select"
                  value={selectedStatus}
                  onChange={(e) => setSelectedStatus(e.target.value as TicketStatus)}
                  disabled={isUpdatingStaffFields}
                >
                  <option value="open">Open</option>
                  <option value="in_progress">In Progress</option>
                  <option value="pending_customer">Pending Customer</option>
                  <option value="resolved">Resolved</option>
                  <option value="closed">Closed</option>
                </select>
              </div>

              <div className="staff-form-group">
                <label className="sidebar-field-label">Priority</label>
                <select
                  className="form-select"
                  value={selectedPriority}
                  onChange={(e) => setSelectedPriority(e.target.value as TicketPriority)}
                  disabled={isUpdatingStaffFields}
                >
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                  <option value="critical">Critical</option>
                </select>
              </div>

              <div className="staff-form-group">
                <label className="sidebar-field-label">Assigned Agent</label>
                <select
                  className="form-select"
                  value={selectedAssignee}
                  onChange={(e) => setSelectedAssignee(e.target.value)}
                  disabled={isUpdatingStaffFields}
                >
                  <option value="">— Unassigned —</option>
                  {agents.map((agent) => (
                    <option key={agent.id} value={agent.id}>
                      {agent.full_name} ({agent.department})
                    </option>
                  ))}
                </select>
              </div>

              <div className="staff-form-group">
                <label className="sidebar-field-label">Category</label>
                <select
                  className="form-select"
                  value={selectedCategory}
                  onChange={(e) => setSelectedCategory(e.target.value)}
                  disabled={isUpdatingStaffFields}
                >
                  <option value="">— Select Category —</option>
                  {categories.map((cat) => (
                    <option key={cat.id} value={cat.id}>
                      {cat.name} ({cat.default_sla_hours}h SLA)
                    </option>
                  ))}
                </select>
              </div>

              <button
                type="button"
                className="btn btn-primary btn-full"
                onClick={handleStaffUpdate}
                disabled={isUpdatingStaffFields}
                style={{ marginTop: '0.5rem' }}
              >
                {isUpdatingStaffFields ? (
                  <>
                    <Loader2 size={16} className="spinner" />
                    <span>Updating Ticket...</span>
                  </>
                ) : (
                  <span>Apply Properties</span>
                )}
              </button>
            </div>
          )}

          {/* Ticket Metadata Properties Card */}
          <div className="ticket-metadata-card glass-card">
            <h3 className="card-section-title" style={{ marginBottom: '1rem' }}>
              Ticket Details
            </h3>

            <div className="meta-property-list">
              <div className="meta-property-item">
                <span className="meta-prop-label">
                  <User size={14} /> Requester
                </span>
                <span className="meta-prop-value">{ticket.creator?.full_name || 'Unknown'}</span>
                <span className="meta-prop-sub">{ticket.creator?.email}</span>
                <span className="meta-prop-sub">Dept: {ticket.creator?.department || 'General'}</span>
              </div>

              <div className="meta-property-item">
                <span className="meta-prop-label">
                  <Shield size={14} /> Assignee
                </span>
                {ticket.assignee ? (
                  <>
                    <span className="meta-prop-value">{ticket.assignee.full_name}</span>
                    <span className="meta-prop-sub">{ticket.assignee.email}</span>
                  </>
                ) : (
                  <span className="meta-prop-value unassigned">Unassigned</span>
                )}
              </div>

              <div className="meta-property-item">
                <span className="meta-prop-label">
                  <Layers size={14} /> Category
                </span>
                <span className="meta-prop-value">{ticket.category?.name || 'General'}</span>
                {ticket.category && (
                  <span className="meta-prop-sub">Default SLA: {ticket.category.default_sla_hours} hrs</span>
                )}
              </div>

              <div className="meta-property-item">
                <span className="meta-prop-label">
                  <Flag size={14} /> Priority Multiplier
                </span>
                <span className="meta-prop-value" style={{ textTransform: 'capitalize' }}>
                  {ticket.priority}
                </span>
              </div>

              <div className="meta-property-item">
                <span className="meta-prop-label">
                  <Clock size={14} /> SLA Due Target
                </span>
                <span className="meta-prop-value">{formatDate(ticket.sla_due_at)}</span>
              </div>

              {ticket.resolved_at && (
                <div className="meta-property-item">
                  <span className="meta-prop-label">
                    <CheckCircle size={14} color="#34d399" /> Resolved Date
                  </span>
                  <span className="meta-prop-value">{formatDate(ticket.resolved_at)}</span>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
