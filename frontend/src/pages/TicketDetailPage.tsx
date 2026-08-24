import React, { useState, useEffect, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { ticketService } from '../services/ticketService';
import { kbService } from '../services/kbService';
import { slaService } from '../services/slaService';
import { getApiErrorMessage } from '../services/api';
import type {
  TicketDetail,
  Category,
  AgentSummary,
  TicketStatus,
  TicketPriority,
  CommentType,
  TicketTriageRecommendation,
  AIResponseDraft,
  TicketSummary,
  GroundedArticleReference,
  TicketGroundingResponse,
  TicketSLAMetrics,
  AISLARiskAssessment,
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
  CheckCircle2,
  Sparkles,
  Copy,
  Check,
  RotateCw,
  FileText,
  Bot,
  BookOpen,
  ExternalLink,
  HelpCircle,
  AlertOctagon,
  Timer,
  Activity,
  ShieldAlert,
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

  // AI Summary state (staff-only)
  const [ticketSummary, setTicketSummary] = useState<TicketSummary | null>(null);
  const [isLoadingSummary, setIsLoadingSummary] = useState<boolean>(false);
  const [summaryError, setSummaryError] = useState<string | null>(null);
  const [copiedSummary, setCopiedSummary] = useState<boolean>(false);

  // AI Response Draft state (staff-only)
  const [responseDraft, setResponseDraft] = useState<AIResponseDraft | null>(null);
  const [isLoadingDraft, setIsLoadingDraft] = useState<boolean>(false);
  const [draftError, setDraftError] = useState<string | null>(null);
  const [copiedDraft, setCopiedDraft] = useState<boolean>(false);
  const [draftAppliedMsg, setDraftAppliedMsg] = useState<string | null>(null);

  // AI triage state (recommendation-only)
  const [triageRecommendation, setTriageRecommendation] = useState<TicketTriageRecommendation | null>(null);
  const [isLoadingTriage, setIsLoadingTriage] = useState<boolean>(false);
  const [triageError, setTriageError] = useState<string | null>(null);
  const [isSubmittingTriageDecision, setIsSubmittingTriageDecision] = useState<boolean>(false);
  const [triageDecisionState, setTriageDecisionState] = useState<'accepted' | 'rejected' | null>(null);
  const [triageDecisionMessage, setTriageDecisionMessage] = useState<string | null>(null);

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

  // AI Grounding & Knowledge Base Matching state
  const [groundingResponse, setGroundingResponse] = useState<TicketGroundingResponse | null>(null);
  const [isLoadingGrounding, setIsLoadingGrounding] = useState<boolean>(false);
  const [groundingError, setGroundingError] = useState<string | null>(null);
  const [matchedArticles, setMatchedArticles] = useState<GroundedArticleReference[]>([]);
  const [isLoadingMatches, setIsLoadingMatches] = useState<boolean>(false);

  // SLA State & Metrics
  const [slaMetrics, setSlaMetrics] = useState<TicketSLAMetrics | null>(null);
  const [isLoadingSLA, setIsLoadingSLA] = useState<boolean>(false);
  const [slaError, setSlaError] = useState<string | null>(null);

  // AI SLA Risk & Escalation Intelligence state (staff-only)
  const [slaRiskAssessment, setSlaRiskAssessment] = useState<AISLARiskAssessment | null>(null);
  const [isLoadingRisk, setIsLoadingRisk] = useState<boolean>(false);
  const [riskError, setRiskError] = useState<string | null>(null);
  const [isSubmittingEscalation, setIsSubmittingEscalation] = useState<boolean>(false);
  const [escalationDecisionState, setEscalationDecisionState] = useState<'accepted' | 'rejected' | null>(null);
  const [escalationDecisionMessage, setEscalationDecisionMessage] = useState<string | null>(null);

  const isStaff = user?.role === 'agent' || user?.role === 'admin';
  const isCreator = user?.id === ticket?.creator_id;
  const canUserEdit = isCreator && user?.role === 'user' && ticket?.status === 'open';

  // Load relevant published KB articles matching the ticket
  const loadKBMatches = useCallback(async (ticketIdToFetch: string) => {
    setIsLoadingMatches(true);
    try {
      const matches = await kbService.getTicketKBMatches(ticketIdToFetch);
      setMatchedArticles(matches);
    } catch (err) {
      console.error('Failed to load KB matches:', err);
    } finally {
      setIsLoadingMatches(false);
    }
  }, []);

  // Load SLA Metrics
  const loadSLAMetrics = useCallback(async (ticketIdToFetch: string) => {
    setIsLoadingSLA(true);
    setSlaError(null);
    try {
      const data = await slaService.getTicketSLA(ticketIdToFetch);
      setSlaMetrics(data.sla_metrics);
    } catch (err) {
      console.error('Failed to load SLA metrics:', err);
      setSlaError('SLA metrics currently unavailable.');
    } finally {
      setIsLoadingSLA(false);
    }
  }, []);

  // Load ticket details
  const loadTicket = useCallback(async () => {
    if (!ticketId) return;
    setIsLoading(true);
    setErrorMessage(null);
    setTicket(null);
    try {
      const data = await ticketService.getTicketDetail(ticketId);
      setTicket(data);
      setSelectedStatus(data.status);
      setSelectedPriority(data.priority);
      setSelectedAssignee(data.assignee_id || '');
      setSelectedCategory(data.category_id ? String(data.category_id) : '');
      setEditTitle(data.title);
      setEditDescription(data.description);
      loadKBMatches(data.id);
      loadSLAMetrics(data.id);
    } catch (err: unknown) {
      console.error('Failed to load ticket:', err);
      const msg = getApiErrorMessage(err, 'Failed to retrieve ticket details.');
      setErrorMessage(msg);
    } finally {
      setIsLoading(false);
    }
  }, [ticketId, loadKBMatches, loadSLAMetrics]);

  // Trigger AI Grounding
  const handleGenerateGrounding = async () => {
    if (!ticket || isLoadingGrounding) return;
    setIsLoadingGrounding(true);
    setGroundingError(null);
    try {
      const response = await kbService.getTicketGrounding(ticket.id);
      setGroundingResponse(response);
    } catch (err: unknown) {
      setGroundingError(getApiErrorMessage(err, 'AI knowledge grounding is currently unavailable. Please try again later.'));
    } finally {
      setIsLoadingGrounding(false);
    }
  };

  // Trigger AI SLA Risk & Escalation Analysis
  const handleAnalyzeSLARisk = async () => {
    if (!ticket || isLoadingRisk) return;
    setIsLoadingRisk(true);
    setRiskError(null);
    try {
      const response = await slaService.analyzeTicketSLARisk(ticket.id);
      setSlaRiskAssessment(response.ai_risk_assessment);
      if (response.sla_metrics) {
        setSlaMetrics(response.sla_metrics);
      }
    } catch (err: unknown) {
      setRiskError(getApiErrorMessage(err, 'AI SLA risk analysis is currently unavailable. Please try again later.'));
    } finally {
      setIsLoadingRisk(false);
    }
  };

  // Approve Escalation
  const handleApproveEscalation = async () => {
    if (!ticket || !slaRiskAssessment || isSubmittingEscalation) return;
    setIsSubmittingEscalation(true);
    try {
      const res = await slaService.approveTicketEscalation(ticket.id, {
        recommendation_id: slaRiskAssessment.recommendation_id,
        apply_priority: true,
      });
      setEscalationDecisionState('accepted');
      setEscalationDecisionMessage(res.message);
      if (res.applied_priority) {
        setSelectedPriority(res.applied_priority as TicketPriority);
      }
      loadTicket();
    } catch (err: unknown) {
      setRiskError(getApiErrorMessage(err, 'Failed to approve escalation recommendation.'));
    } finally {
      setIsSubmittingEscalation(false);
    }
  };

  // Reject Escalation
  const handleRejectEscalation = async () => {
    if (!ticket || !slaRiskAssessment || isSubmittingEscalation) return;
    setIsSubmittingEscalation(true);
    try {
      const res = await slaService.rejectTicketEscalation(ticket.id, {
        recommendation_id: slaRiskAssessment.recommendation_id,
      });
      setEscalationDecisionState('rejected');
      setEscalationDecisionMessage(res.message);
    } catch (err: unknown) {
      setRiskError(getApiErrorMessage(err, 'Failed to reject escalation recommendation.'));
    } finally {
      setIsSubmittingEscalation(false);
    }
  };

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

  const getConfidenceLabel = (score: number): string => {
    if (score >= 0.75) return 'High';
    if (score >= 0.4) return 'Medium';
    return 'Low';
  };

  const formatDuration = (seconds: number): string => {
    if (seconds <= 0) return '0m';
    const hrs = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    if (hrs > 0) {
      return `${hrs}h ${mins}m`;
    }
    return `${mins}m`;
  };

  const handleTriage = async () => {
    if (!ticket || isLoadingTriage) return;

    setIsLoadingTriage(true);
    setTriageError(null);
    setTriageDecisionState(null);
    setTriageDecisionMessage(null);
    try {
      const recommendation = await ticketService.getTicketTriage(ticket.id);
      setTriageRecommendation(recommendation);
    } catch (err: unknown) {
      setTriageError(getApiErrorMessage(err, 'AI triage is currently unavailable. Please try again later.'));
    } finally {
      setIsLoadingTriage(false);
    }
  };

  const handleTriageDecision = async (decision: 'accept' | 'reject') => {
    if (!ticket || !triageRecommendation?.recommendation_id || isSubmittingTriageDecision) return;

    setIsSubmittingTriageDecision(true);
    setTriageError(null);
    setTriageDecisionMessage(null);
    try {
      const response = decision === 'accept'
        ? await ticketService.approveTicketTriage(ticket.id, triageRecommendation.recommendation_id)
        : await ticketService.rejectTicketTriage(ticket.id, triageRecommendation.recommendation_id);

      setTriageDecisionState(response.decision);
      setTriageDecisionMessage(
        response.decision === 'accepted'
          ? 'AI recommendation accepted. Ticket values were refreshed.'
          : 'AI recommendation rejected. The ticket remains unchanged.'
      );
      await loadTicket();
    } catch (err: unknown) {
      setTriageError(getApiErrorMessage(err, 'Unable to record the recommendation decision.'));
    } finally {
      setIsSubmittingTriageDecision(false);
    }
  };

  const handleGenerateSummary = async () => {
    if (!ticket || isLoadingSummary) return;

    setIsLoadingSummary(true);
    setSummaryError(null);
    try {
      const summary = await ticketService.getTicketSummary(ticket.id);
      setTicketSummary(summary);
    } catch (err: unknown) {
      setSummaryError(getApiErrorMessage(err, 'AI ticket summarization is currently unavailable. Please try again later.'));
    } finally {
      setIsLoadingSummary(false);
    }
  };

  const handleCopySummary = async () => {
    if (!ticketSummary) return;
    try {
      const textToCopy = `TICKET SUMMARY: ${ticket?.ticket_number || ''} - ${ticket?.title || ''}
--------------------------------------------------
SUMMARY:
${ticketSummary.summary}

CUSTOMER ISSUE:
${ticketSummary.customer_issue}

IMPORTANT FACTS:
${ticketSummary.important_facts.map((fact) => `• ${fact}`).join('\n')}

ACTIONS TAKEN:
${ticketSummary.actions_taken.map((action) => `• ${action}`).join('\n')}

SUGGESTED NEXT STEPS:
${ticketSummary.suggested_next_steps.map((step) => `• ${step}`).join('\n')}

MISSING INFORMATION:
${ticketSummary.missing_information && ticketSummary.missing_information.length > 0 ? ticketSummary.missing_information.map((info) => `• ${info}`).join('\n') : '• None'}

RISK FLAGS:
${ticketSummary.risk_flags && ticketSummary.risk_flags.length > 0 ? ticketSummary.risk_flags.map((risk) => `• ${risk}`).join('\n') : '• None'}

CONFIDENCE: ${Math.round(ticketSummary.confidence * 100)}%`;

      await navigator.clipboard.writeText(textToCopy);
      setCopiedSummary(true);
      setTimeout(() => setCopiedSummary(false), 2500);
    } catch (err) {
      console.error('Failed to copy summary to clipboard', err);
    }
  };

  const handleGenerateDraft = async () => {
    if (!ticket || isLoadingDraft) return;

    setIsLoadingDraft(true);
    setDraftError(null);
    setDraftAppliedMsg(null);
    try {
      const draft = await ticketService.getResponseDraft(ticket.id);
      setResponseDraft(draft);
    } catch (err: unknown) {
      setDraftError(getApiErrorMessage(err, 'AI response drafting is currently unavailable. Please try again later.'));
    } finally {
      setIsLoadingDraft(false);
    }
  };

  const handleCopyDraft = async () => {
    if (!responseDraft?.draft_response) return;
    try {
      await navigator.clipboard.writeText(responseDraft.draft_response);
      setCopiedDraft(true);
      setTimeout(() => setCopiedDraft(false), 2000);
    } catch (err) {
      console.error('Failed to copy draft to clipboard', err);
    }
  };

  const handleUseAsCommentDraft = () => {
    if (!responseDraft?.draft_response) return;
    setCommentContent(responseDraft.draft_response);
    setCommentType('public');
    setDraftAppliedMsg('AI draft loaded into response box. Review and edit before sending.');
    setTimeout(() => setDraftAppliedMsg(null), 5000);
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

          {/* Staff AI Ticket Summary & Action Insights */}
          {isStaff && (
            <div className="ticket-ai-summary-card glass-card">
              <div className="ai-summary-card-header">
                <div className="ai-summary-title-cluster">
                  <div className="ai-summary-icon-wrapper">
                    <Sparkles size={18} color="#38bdf8" />
                  </div>
                  <div>
                    <h3 className="card-section-title">AI Summary & Action Insights</h3>
                    <p className="ai-summary-subtitle">
                      Grounded conversation overview, key facts, actions taken, and risk flags for staff.
                    </p>
                  </div>
                </div>

                {!ticketSummary && !isLoadingSummary && (
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm ai-summary-trigger-btn"
                    onClick={handleGenerateSummary}
                    disabled={isLoadingSummary}
                  >
                    <Sparkles size={14} color="#38bdf8" />
                    <span>Generate Summary</span>
                  </button>
                )}

                {ticketSummary && (
                  <div className="ai-summary-header-actions">
                    <button
                      type="button"
                      className="btn btn-secondary btn-sm"
                      onClick={handleCopySummary}
                      title="Copy full summary to clipboard"
                    >
                      {copiedSummary ? (
                        <>
                          <Check size={14} color="#10b981" />
                          <span>Copied!</span>
                        </>
                      ) : (
                        <>
                          <Copy size={14} />
                          <span>Copy Summary</span>
                        </>
                      )}
                    </button>
                    <button
                      type="button"
                      className="btn btn-secondary btn-sm"
                      onClick={handleGenerateSummary}
                      disabled={isLoadingSummary}
                      title="Regenerate summary"
                    >
                      <RotateCw size={14} className={isLoadingSummary ? 'spinner' : ''} />
                      <span>Regenerate</span>
                    </button>
                  </div>
                )}
              </div>

              {summaryError && (
                <div className="alert alert-error" style={{ marginTop: '0.75rem' }}>
                  <AlertCircle size={16} />
                  <span>{summaryError}</span>
                </div>
              )}

              {isLoadingSummary && (
                <div className="ai-summary-loading-box">
                  <Loader2 size={24} className="spinner" color="#38bdf8" />
                  <p>Analyzing conversation, public comments, and history...</p>
                </div>
              )}

              {ticketSummary && !isLoadingSummary && (
                <div className="ai-summary-body">
                  {/* Badges Bar */}
                  <div className="ai-summary-badge-bar">
                    <span className="ai-summary-pill">AI SUMMARY</span>
                    <span className="ai-summary-confidence-pill">
                      {Math.round(ticketSummary.confidence * 100)}% Confidence ({getConfidenceLabel(ticketSummary.confidence)})
                    </span>
                  </div>

                  {/* Executive Summary */}
                  <div className="ai-summary-lead-box">
                    <h4 className="ai-summary-section-label">Summary</h4>
                    <p className="ai-summary-lead-text">{ticketSummary.summary}</p>
                  </div>

                  {/* Customer Issue */}
                  <div className="ai-summary-issue-box">
                    <h4 className="ai-summary-section-label">Customer Issue</h4>
                    <p className="ai-summary-issue-text">{ticketSummary.customer_issue}</p>
                  </div>

                  {/* 2-Column Insights Grid */}
                  <div className="ai-summary-insights-grid">
                    {/* Important Facts */}
                    <div className="ai-insight-panel">
                      <h4 className="ai-insight-panel-title">Important Facts</h4>
                      {ticketSummary.important_facts && ticketSummary.important_facts.length > 0 ? (
                        <ul className="ai-insight-list">
                          {ticketSummary.important_facts.map((fact, idx) => (
                            <li key={idx}>{fact}</li>
                          ))}
                        </ul>
                      ) : (
                        <p className="ai-insight-empty">No specific facts reported.</p>
                      )}
                    </div>

                    {/* Actions Taken */}
                    <div className="ai-insight-panel">
                      <h4 className="ai-insight-panel-title">Actions Already Taken</h4>
                      {ticketSummary.actions_taken && ticketSummary.actions_taken.length > 0 ? (
                        <ul className="ai-insight-list">
                          {ticketSummary.actions_taken.map((action, idx) => (
                            <li key={idx}>{action}</li>
                          ))}
                        </ul>
                      ) : (
                        <p className="ai-insight-empty">No prior actions documented yet.</p>
                      )}
                    </div>

                    {/* Suggested Next Steps */}
                    <div className="ai-insight-panel">
                      <h4 className="ai-insight-panel-title">Suggested Next Steps</h4>
                      {ticketSummary.suggested_next_steps && ticketSummary.suggested_next_steps.length > 0 ? (
                        <ul className="ai-insight-list next-steps-list">
                          {ticketSummary.suggested_next_steps.map((step, idx) => (
                            <li key={idx}>{step}</li>
                          ))}
                        </ul>
                      ) : (
                        <p className="ai-insight-empty">No specific next steps suggested.</p>
                      )}
                    </div>

                    {/* Missing Information */}
                    <div className="ai-insight-panel">
                      <h4 className="ai-insight-panel-title">Missing Information</h4>
                      {ticketSummary.missing_information && ticketSummary.missing_information.length > 0 ? (
                        <ul className="ai-insight-list missing-info-list">
                          {ticketSummary.missing_information.map((item, idx) => (
                            <li key={idx}>{item}</li>
                          ))}
                        </ul>
                      ) : (
                        <p className="ai-insight-empty text-muted">All necessary information appears to be present.</p>
                      )}
                    </div>
                  </div>

                  {/* Risk Flags */}
                  {ticketSummary.risk_flags && ticketSummary.risk_flags.length > 0 && (
                    <div className="ai-summary-risks-box">
                      <div className="ai-risk-heading-row">
                        <Flag size={15} color="#f87171" />
                        <h4 className="ai-risk-title">Identified Risk Flags</h4>
                      </div>
                      <div className="ai-risk-tags-cluster">
                        {ticketSummary.risk_flags.map((flag, idx) => (
                          <div key={idx} className="ai-risk-tag">
                            <span className="risk-tag-bullet">⚠️</span>
                            <span>{flag}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Bottom Action Footer */}
                  <div className="ai-summary-footer-bar">
                    <button
                      type="button"
                      className="btn btn-secondary btn-sm"
                      onClick={handleCopySummary}
                    >
                      {copiedSummary ? (
                        <>
                          <Check size={14} color="#10b981" />
                          <span>Copied to Clipboard!</span>
                        </>
                      ) : (
                        <>
                          <Copy size={14} />
                          <span>Copy Summary</span>
                        </>
                      )}
                    </button>
                    <button
                      type="button"
                      className="btn btn-secondary btn-sm"
                      onClick={handleGenerateSummary}
                      disabled={isLoadingSummary}
                    >
                      <RotateCw size={14} className={isLoadingSummary ? 'spinner' : ''} />
                      <span>Regenerate Summary</span>
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Knowledge Base AI Grounding & Verified Sources Card */}
          <div className="ticket-ai-grounding-card glass-card">
            <div className="ai-grounding-header">
              <div className="ai-grounding-title-cluster">
                <div className="ai-grounding-icon-wrapper">
                  <BookOpen size={18} color="#38bdf8" />
                </div>
                <div>
                  <h3 className="card-section-title">Knowledge Base Grounding & Verified Solutions</h3>
                  <p className="ai-grounding-subtitle">
                    AI recommendation strictly grounded in published knowledge base articles with verified citations.
                  </p>
                </div>
              </div>

              {!groundingResponse && !isLoadingGrounding && (
                <button
                  type="button"
                  className="btn btn-primary btn-sm ai-grounding-trigger-btn"
                  onClick={handleGenerateGrounding}
                  disabled={isLoadingGrounding}
                >
                  <Sparkles size={14} />
                  <span>Ground Solution with AI</span>
                </button>
              )}

              {groundingResponse && (
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  onClick={handleGenerateGrounding}
                  disabled={isLoadingGrounding}
                  title="Regenerate grounded recommendation"
                >
                  <RotateCw size={14} className={isLoadingGrounding ? 'spinner' : ''} />
                  <span>Regenerate</span>
                </button>
              )}
            </div>

            {groundingError && (
              <div className="alert alert-error" style={{ marginTop: '0.75rem' }}>
                <AlertCircle size={16} />
                <span>{groundingError}</span>
              </div>
            )}

            {isLoadingGrounding && (
              <div className="ai-grounding-loading-box">
                <Loader2 size={24} className="spinner" color="#38bdf8" />
                <p>Retrieving published knowledge articles and synthesizing verified solution...</p>
              </div>
            )}

            {/* When Grounding Response is available */}
            {groundingResponse && !isLoadingGrounding && (
              <div className="ai-grounding-body">
                {/* Status Badges Bar */}
                <div className="ai-grounding-status-bar">
                  {groundingResponse.grounding_status === 'grounded' && (
                    <span className="grounding-badge grounded">
                      <CheckCircle2 size={14} />
                      <span>Grounded in Verified KB</span>
                    </span>
                  )}
                  {groundingResponse.grounding_status === 'partially_grounded' && (
                    <span className="grounding-badge partially-grounded">
                      <AlertCircle size={14} />
                      <span>Partially Grounded</span>
                    </span>
                  )}
                  {groundingResponse.grounding_status === 'no_match' && (
                    <span className="grounding-badge no-match">
                      <HelpCircle size={14} />
                      <span>No Reliable KB Match</span>
                    </span>
                  )}

                  {groundingResponse.confidence > 0 && (
                    <span className="grounding-confidence-pill">
                      {Math.round(groundingResponse.confidence * 100)}% Confidence
                    </span>
                  )}
                </div>

                {/* No Match State Explanation */}
                {groundingResponse.grounding_status === 'no_match' ? (
                  <div className="grounding-no-match-box">
                    <div className="no-match-icon-circle">
                      <HelpCircle size={20} color="#94a3b8" />
                    </div>
                    <div className="no-match-text-col">
                      <h4 className="no-match-title">No Reliable Knowledge Match</h4>
                      <p className="no-match-desc">{groundingResponse.recommendation}</p>
                      {groundingResponse.no_match_reason && (
                        <p className="no-match-reason">Note: {groundingResponse.no_match_reason}</p>
                      )}
                    </div>
                  </div>
                ) : (
                  /* Grounded / Partially Grounded Content */
                  <>
                    {/* Recommendation Box */}
                    <div className="grounding-recommendation-box">
                      <h4 className="grounding-section-label">Grounded Guidance</h4>
                      <p className="grounding-recommendation-text">{groundingResponse.recommendation}</p>
                    </div>

                    {/* Key Solution Steps / Points */}
                    {groundingResponse.key_points && groundingResponse.key_points.length > 0 && (
                      <div className="grounding-key-points-box">
                        <h4 className="grounding-section-label">Verified Action Steps</h4>
                        <ul className="grounding-points-list">
                          {groundingResponse.key_points.map((point, idx) => (
                            <li key={idx}>
                              <CheckCircle size={14} className="point-icon" color="#10b981" />
                              <span>{point}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* Verified Sources / Citations */}
                    {groundingResponse.sources && groundingResponse.sources.length > 0 && (
                      <div className="grounding-sources-box">
                        <h4 className="grounding-section-label">Cited Knowledge Base Sources</h4>
                        <div className="grounding-sources-grid">
                          {groundingResponse.sources.map((source) => (
                            <div key={source.article_id} className="grounding-source-card">
                              <div className="source-card-top">
                                <Link
                                  to={`/kb/${source.slug || source.article_id}`}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="source-title-link"
                                >
                                  <span>{source.title}</span>
                                  <ExternalLink size={13} />
                                </Link>
                                <span className="source-match-badge">
                                  {Math.round(source.relevance_score * 100)}% Match
                                </span>
                              </div>
                              {source.category && (
                                <span className="source-category-tag">{source.category}</span>
                              )}
                              <p className="source-snippet">{source.snippet}</p>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </>
                )}
              </div>
            )}

            {/* Initial preview of matched KB articles when grounding has not been generated yet */}
            {!groundingResponse && !isLoadingGrounding && (
              isLoadingMatches ? (
                <div className="kb-matched-preview-box">
                  <div className="matched-preview-header" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <Loader2 size={14} className="spinner" color="#38bdf8" />
                    <span className="preview-label">Checking for relevant knowledge articles...</span>
                  </div>
                </div>
              ) : matchedArticles.length > 0 ? (
                <div className="kb-matched-preview-box">
                  <div className="matched-preview-header">
                    <span className="preview-label">Found {matchedArticles.length} Related Articles in Knowledge Base:</span>
                  </div>
                  <div className="preview-articles-list">
                    {matchedArticles.map((art) => (
                      <Link
                        key={art.article_id}
                        to={`/kb/${art.slug || art.article_id}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="preview-article-row"
                      >
                        <BookOpen size={14} color="#38bdf8" />
                        <span className="preview-article-title">{art.title}</span>
                        <span className="preview-article-score">{Math.round(art.relevance_score * 100)}% relevant</span>
                        <ExternalLink size={12} className="preview-ext-icon" />
                      </Link>
                    ))}
                  </div>
                </div>
              ) : null
            )}
          </div>

          {/* Staff AI SLA Risk & Escalation Intelligence Card */}
          {isStaff && (
            <div className="ticket-ai-sla-risk-card glass-card">
              <div className="ai-risk-header">
                <div className="ai-risk-title-cluster">
                  <div className="ai-risk-icon-wrapper">
                    <Activity size={18} color="#f59e0b" />
                  </div>
                  <div>
                    <h3 className="card-section-title">AI SLA Risk & Escalation Intelligence</h3>
                    <p className="ai-risk-subtitle">
                      Predictive breach analysis & advisory escalation recommendations (requires human review).
                    </p>
                  </div>
                </div>

                {!slaRiskAssessment && !isLoadingRisk && (
                  <button
                    type="button"
                    className="btn btn-primary btn-sm ai-risk-trigger-btn"
                    onClick={handleAnalyzeSLARisk}
                    disabled={isLoadingRisk}
                  >
                    <Sparkles size={14} />
                    <span>Assess SLA Risk with AI</span>
                  </button>
                )}

                {slaRiskAssessment && (
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm"
                    onClick={handleAnalyzeSLARisk}
                    disabled={isLoadingRisk}
                    title="Re-run SLA Risk Analysis"
                  >
                    <RotateCw size={14} className={isLoadingRisk ? 'spinner' : ''} />
                    <span>Re-evaluate</span>
                  </button>
                )}
              </div>

              {riskError && (
                <div className="alert alert-error" style={{ marginTop: '0.75rem' }}>
                  <AlertCircle size={16} />
                  <span>{riskError}</span>
                </div>
              )}

              {isLoadingRisk && (
                <div className="ai-risk-loading-box">
                  <Loader2 size={24} className="spinner" color="#f59e0b" />
                  <p>Analyzing ticket progression, elapsed SLA metrics, and breach probability...</p>
                </div>
              )}

              {/* Assessment Body */}
              {slaRiskAssessment && !isLoadingRisk && (
                <div className="ai-risk-body">
                  {/* Status & Prediction Bar */}
                  <div className="ai-risk-status-bar">
                    <span className={`risk-level-badge ${slaRiskAssessment.risk_level}`}>
                      <AlertOctagon size={13} />
                      <span>{slaRiskAssessment.risk_level.toUpperCase()} RISK</span>
                    </span>

                    <span className="risk-confidence-pill">
                      {Math.round(slaRiskAssessment.confidence * 100)}% Confidence ({slaRiskAssessment.confidence_level})
                    </span>

                    {slaRiskAssessment.predicted_time_to_breach && (
                      <span className="risk-time-pill">
                        <Clock size={12} />
                        <span>{slaRiskAssessment.predicted_time_to_breach}</span>
                      </span>
                    )}
                  </div>

                  {/* Recommended Action & Advice */}
                  <div className="risk-action-box">
                    <h4 className="risk-section-label">Recommended Support Action</h4>
                    <p className="risk-action-text">{slaRiskAssessment.recommended_action}</p>
                  </div>

                  {/* Contributing Risk Factors */}
                  {slaRiskAssessment.risk_factors && slaRiskAssessment.risk_factors.length > 0 && (
                    <div className="risk-factors-box">
                      <h4 className="risk-section-label">Contributing Risk Factors</h4>
                      <ul className="risk-factors-list">
                        {slaRiskAssessment.risk_factors.map((factor, idx) => (
                          <li key={idx}>
                            <AlertCircle size={14} className="factor-icon" color="#f59e0b" />
                            <span>{factor}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Escalation Recommendation & Human Review Box */}
                  <div className={`escalation-review-card ${slaRiskAssessment.escalation_recommended ? 'recommended' : 'not-recommended'}`}>
                    <div className="escalation-header-row">
                      <div className="escalation-title-row">
                        <ShieldAlert size={16} color={slaRiskAssessment.escalation_recommended ? '#ef4444' : '#10b981'} />
                        <h4 className="escalation-card-title">
                          {slaRiskAssessment.escalation_recommended
                            ? `Escalation Recommended (${slaRiskAssessment.escalation_urgency.toUpperCase()} Urgency)`
                            : 'No Immediate Escalation Required'}
                        </h4>
                      </div>
                      <span className="human-review-tag">Advisory • Staff Approval Required</span>
                    </div>

                    {slaRiskAssessment.escalation_recommended && (
                      <div className="escalation-details-grid">
                        <div className="esc-detail-cell">
                          <span className="esc-label">Recommended Priority</span>
                          <span className="esc-val priority-tag" style={{ textTransform: 'uppercase' }}>
                            {slaRiskAssessment.recommended_priority}
                          </span>
                        </div>
                        <div className="esc-detail-cell">
                          <span className="esc-label">Recommended Team</span>
                          <span className="esc-val team-tag">{slaRiskAssessment.recommended_team}</span>
                        </div>
                      </div>
                    )}

                    {/* Human Approval Decision State or Buttons */}
                    {escalationDecisionState ? (
                      <div className={`escalation-decision-result ${escalationDecisionState}`}>
                        {escalationDecisionState === 'accepted' ? (
                          <>
                            <CheckCircle2 size={16} color="#34d399" />
                            <span>{escalationDecisionMessage || 'Escalation accepted and priority updated.'}</span>
                          </>
                        ) : (
                          <>
                            <X size={16} color="#94a3b8" />
                            <span>{escalationDecisionMessage || 'Escalation recommendation rejected.'}</span>
                          </>
                        )}
                      </div>
                    ) : (
                      <div className="escalation-decision-actions">
                        <button
                          type="button"
                          className="btn btn-primary btn-sm"
                          onClick={handleApproveEscalation}
                          disabled={isSubmittingEscalation}
                        >
                          {isSubmittingEscalation ? (
                            <Loader2 size={14} className="spinner" />
                          ) : (
                            <CheckCircle size={14} />
                          )}
                          <span>Accept & Apply Escalation</span>
                        </button>
                        <button
                          type="button"
                          className="btn btn-secondary btn-sm"
                          onClick={handleRejectEscalation}
                          disabled={isSubmittingEscalation}
                        >
                          {isSubmittingEscalation ? (
                            <Loader2 size={14} className="spinner" />
                          ) : (
                            <X size={14} />
                          )}
                          <span>Reject Recommendation</span>
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}

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

            {/* Staff AI Response Assistant */}
            {isStaff && (
              <div className="ai-response-assistant-section">
                <div className="ai-assistant-header-row">
                  <div className="ai-assistant-title">
                    <Bot size={16} color="#c084fc" />
                    <span>AI Response Assistant</span>
                  </div>
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm ai-draft-btn"
                    onClick={handleGenerateDraft}
                    disabled={isLoadingDraft}
                  >
                    {isLoadingDraft ? (
                      <>
                        <Loader2 size={14} className="spinner" />
                        <span>Drafting Response...</span>
                      </>
                    ) : (
                      <>
                        <Sparkles size={14} color="#c084fc" />
                        <span>{responseDraft ? 'Regenerate Draft' : 'Draft Response with AI'}</span>
                      </>
                    )}
                  </button>
                </div>

                {draftError && (
                  <div className="alert alert-error" style={{ margin: 0 }}>
                    <AlertCircle size={15} />
                    <span>{draftError}</span>
                  </div>
                )}

                {draftAppliedMsg && (
                  <div className="alert alert-success" style={{ margin: 0 }}>
                    <CheckCircle size={15} />
                    <span>{draftAppliedMsg}</span>
                  </div>
                )}

                {responseDraft && (
                  <div className="ai-draft-card glass-card">
                    <div className="ai-draft-card-header">
                      <div className="ai-draft-badge-row">
                        <span className="ai-draft-pill">DRAFT ONLY</span>
                        <span className="ai-draft-tone-pill">Tone: {responseDraft.tone}</span>
                        <span className="ai-draft-confidence-pill">
                          {Math.round(responseDraft.confidence * 100)}% Confidence
                        </span>
                      </div>
                      <button
                        type="button"
                        className="ai-draft-dismiss-btn"
                        onClick={() => setResponseDraft(null)}
                        title="Dismiss draft"
                      >
                        <X size={14} />
                      </button>
                    </div>

                    {responseDraft.key_points && responseDraft.key_points.length > 0 && (
                      <div className="ai-draft-key-points">
                        <span className="key-points-title">Key Points Addressed:</span>
                        <ul className="key-points-list">
                          {responseDraft.key_points.map((point, idx) => (
                            <li key={idx}>{point}</li>
                          ))}
                        </ul>
                      </div>
                    )}

                    <div className="ai-draft-content-box">
                      <p>{responseDraft.draft_response}</p>
                    </div>

                    <div className="ai-draft-actions-bar">
                      <button
                        type="button"
                        className="btn btn-primary btn-sm"
                        onClick={handleUseAsCommentDraft}
                      >
                        <FileText size={14} />
                        <span>Use as Comment Draft</span>
                      </button>
                      <button
                        type="button"
                        className="btn btn-secondary btn-sm"
                        onClick={handleCopyDraft}
                      >
                        {copiedDraft ? (
                          <>
                            <Check size={14} color="#10b981" />
                            <span>Copied!</span>
                          </>
                        ) : (
                          <>
                            <Copy size={14} />
                            <span>Copy Draft</span>
                          </>
                        )}
                      </button>
                      <button
                        type="button"
                        className="btn btn-secondary btn-sm"
                        onClick={handleGenerateDraft}
                        disabled={isLoadingDraft}
                      >
                        <RotateCw size={14} className={isLoadingDraft ? 'spinner' : ''} />
                        <span>Regenerate</span>
                      </button>
                    </div>
                  </div>
                )}
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
          {/* SLA Performance & Timeline Card */}
          <div className="ticket-sla-card glass-card">
            <div className="sidebar-card-header">
              <Timer size={17} color="#38bdf8" />
              <h3>SLA Performance & Target</h3>
            </div>

            {isLoadingSLA ? (
              <div className="sla-card-loading">
                <Loader2 size={18} className="spinner" color="#38bdf8" />
                <span>Calculating SLA metrics...</span>
              </div>
            ) : slaMetrics ? (
              <div className="sla-card-body">
                {/* Status Bar */}
                <div className="sla-status-row">
                  <span className="sla-policy-tag">{slaMetrics.policy_name}</span>
                  <span className={`sla-badge ${slaMetrics.sla_state.toLowerCase()}`}>
                    {slaMetrics.sla_state.replace('_', ' ')}
                  </span>
                </div>

                {/* Consumed Progress Bar */}
                <div className="sla-progress-block">
                  <div className="sla-progress-header">
                    <span className="progress-label">Resolution SLA Consumed</span>
                    <span className="progress-value">{slaMetrics.percentage_consumed}%</span>
                  </div>
                  <div className="sla-progress-track">
                    <div
                      className={`sla-progress-fill ${
                        slaMetrics.is_breached
                          ? 'breached'
                          : slaMetrics.is_at_risk
                          ? 'at-risk'
                          : slaMetrics.sla_state === 'PAUSED'
                          ? 'paused'
                          : 'on-track'
                      }`}
                      style={{ width: `${Math.min(100, Math.max(5, slaMetrics.percentage_consumed))}%` }}
                    />
                  </div>
                </div>

                {/* Metrics Grid */}
                <div className="sla-metrics-grid">
                  <div className="sla-metric-cell">
                    <span className="cell-label">First Response</span>
                    <span className={`first-resp-badge ${slaMetrics.first_response_status}`}>
                      {slaMetrics.first_response_status === 'met' && <CheckCircle size={12} />}
                      {slaMetrics.first_response_status === 'breached' && <AlertOctagon size={12} />}
                      {slaMetrics.first_response_status.toUpperCase()}
                    </span>
                    <span className="cell-sub">
                      Target: {slaMetrics.target_first_response_hours}h
                      {slaMetrics.first_response_elapsed_seconds !== null &&
                        slaMetrics.first_response_elapsed_seconds !== undefined &&
                        ` (${formatDuration(slaMetrics.first_response_elapsed_seconds)})`}
                    </span>
                  </div>

                  <div className="sla-metric-cell">
                    <span className="cell-label">Resolution Target</span>
                    <span className="cell-val">
                      {ticket.resolved_at ? 'Resolved' : formatDuration(slaMetrics.remaining_seconds) + ' left'}
                    </span>
                    <span className="cell-sub">
                      Target: {slaMetrics.target_resolution_hours}h ({formatDuration(slaMetrics.resolution_elapsed_seconds)} elapsed)
                    </span>
                  </div>
                </div>
              </div>
            ) : (
              <div className="sla-card-empty">
                <span>{slaError || 'SLA metrics unavailable.'}</span>
              </div>
            )}
          </div>

          <div className="ticket-metadata-card glass-card">
            <div className="sidebar-card-header">
              <Sparkles size={17} color="#a78bfa" />
              <h3>AI Recommendation</h3>
            </div>
            <p className="form-hint" style={{ marginBottom: '1rem' }}>
              Review this recommendation before making any ticket changes.
            </p>

            {triageError && (
              <div className="alert alert-error" style={{ marginBottom: '0.75rem' }}>
                <AlertCircle size={16} />
                <span>{triageError}</span>
              </div>
            )}

            <button
              type="button"
              className="btn btn-secondary btn-full"
              onClick={handleTriage}
              disabled={isLoadingTriage}
            >
              {isLoadingTriage ? (
                <>
                  <Loader2 size={16} className="spinner" />
                  <span>Analyzing Ticket...</span>
                </>
              ) : (
                <>
                  <Sparkles size={16} />
                  <span>AI Triage</span>
                </>
              )}
            </button>

            {triageRecommendation && (
              <div className="meta-property-list" style={{ marginTop: '1rem' }}>
                <div className="meta-property-item">
                  <span className="meta-prop-label">Category</span>
                  <span className="meta-prop-value">{triageRecommendation.category}</span>
                </div>
                <div className="meta-property-item">
                  <span className="meta-prop-label">Priority</span>
                  <span className="meta-prop-value" style={{ textTransform: 'capitalize' }}>{triageRecommendation.priority}</span>
                </div>
                <div className="meta-property-item">
                  <span className="meta-prop-label">Urgency</span>
                  <span className="meta-prop-value" style={{ textTransform: 'capitalize' }}>{triageRecommendation.urgency}</span>
                </div>
                <div className="meta-property-item">
                  <span className="meta-prop-label">Impact</span>
                  <span className="meta-prop-value" style={{ textTransform: 'capitalize' }}>
                    {triageRecommendation.impact.replace('_', ' ')}
                  </span>
                </div>
                <div className="meta-property-item">
                  <span className="meta-prop-label">Suggested Team</span>
                  <span className="meta-prop-value">{triageRecommendation.suggested_team}</span>
                </div>
                <div className="meta-property-item">
                  <span className="meta-prop-label">Confidence</span>
                  <span className="meta-prop-value">
                    {Math.round(triageRecommendation.confidence * 100)}% ({triageRecommendation.confidence_level || getConfidenceLabel(triageRecommendation.confidence)})
                  </span>
                </div>
                <div className="meta-property-item">
                  <span className="meta-prop-label">Evidence</span>
                  <span className="meta-prop-sub">
                    {(triageRecommendation.evidence && triageRecommendation.evidence.length > 0)
                      ? triageRecommendation.evidence.join(' • ')
                      : triageRecommendation.explanation}
                  </span>
                </div>
                <div className="meta-property-item">
                  <span className="meta-prop-label">Priority Reason</span>
                  <span className="meta-prop-sub">{triageRecommendation.priority_reason || triageRecommendation.explanation}</span>
                </div>
                <div className="meta-property-item">
                  <span className="meta-prop-label">Category Reason</span>
                  <span className="meta-prop-sub">{triageRecommendation.category_reason || triageRecommendation.explanation}</span>
                </div>
                <div className="meta-property-item">
                  <span className="meta-prop-label">Urgency / Impact Reason</span>
                  <span className="meta-prop-sub">{triageRecommendation.urgency_impact_reason || triageRecommendation.explanation}</span>
                </div>
                <div className="meta-property-item">
                  <span className="meta-prop-label">Explanation</span>
                  <span className="meta-prop-sub">{triageRecommendation.explanation}</span>
                </div>
              </div>
            )}

            {isStaff && triageRecommendation && (
              <div style={{ marginTop: '1rem', display: 'flex', gap: '0.5rem', flexDirection: 'column' }}>
                {triageDecisionState && triageDecisionMessage && (
                  <div className={`alert ${triageDecisionState === 'accepted' ? 'alert-success' : 'alert-info'}`}>
                    <CheckCircle size={16} />
                    <span>{triageDecisionMessage}</span>
                  </div>
                )}
                <button
                  type="button"
                  className="btn btn-primary btn-full"
                  onClick={() => handleTriageDecision('accept')}
                  disabled={isSubmittingTriageDecision || triageDecisionState === 'accepted'}
                >
                  {isSubmittingTriageDecision ? (
                    <>
                      <Loader2 size={16} className="spinner" />
                      <span>Processing...</span>
                    </>
                  ) : (
                    <>
                      <CheckCircle size={16} />
                      <span>Accept Recommendation</span>
                    </>
                  )}
                </button>
                <button
                  type="button"
                  className="btn btn-secondary btn-full"
                  onClick={() => handleTriageDecision('reject')}
                  disabled={isSubmittingTriageDecision || triageDecisionState === 'rejected'}
                >
                  {isSubmittingTriageDecision ? (
                    <>
                      <Loader2 size={16} className="spinner" />
                      <span>Updating...</span>
                    </>
                  ) : (
                    <>
                      <X size={16} />
                      <span>Reject Recommendation</span>
                    </>
                  )}
                </button>
              </div>
            )}
          </div>

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
