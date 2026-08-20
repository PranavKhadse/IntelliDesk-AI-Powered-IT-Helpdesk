import React, { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { ticketService } from '../services/ticketService';
import { getApiErrorMessage } from '../services/api';
import type { Category, TicketPriority } from '../types';
import {
  ArrowLeft,
  PlusCircle,
  Clock,
  Info,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Layers,
  Flag,
} from 'lucide-react';

export const CreateTicketPage: React.FC = () => {
  const navigate = useNavigate();

  const [categories, setCategories] = useState<Category[]>([]);
  const [title, setTitle] = useState<string>('');
  const [categoryId, setCategoryId] = useState<string>('');
  const [priority, setPriority] = useState<TicketPriority>('medium');
  const [description, setDescription] = useState<string>('');

  const [isLoadingCategories, setIsLoadingCategories] = useState<boolean>(true);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Load categories
  useEffect(() => {
    let isMounted = true;
    const loadCategories = async () => {
      try {
        const cats = await ticketService.getCategories();
        if (!isMounted) return;
        setCategories(cats);
        if (cats.length > 0) {
          setCategoryId(String(cats[0].id));
        }
      } catch (err) {
        console.error('Failed to load categories:', err);
      } finally {
        if (isMounted) setIsLoadingCategories(false);
      }
    };
    loadCategories();
    return () => {
      isMounted = false;
    };
  }, []);

  const selectedCatObj = categories.find((c) => String(c.id) === categoryId);

  // Estimate SLA turnaround based on backend multiplier logic
  const calculateEstimatedSlaHours = (): number => {
    const baseHours = selectedCatObj?.default_sla_hours || 24;
    const multipliers: Record<TicketPriority, number> = {
      critical: 0.25,
      high: 0.5,
      medium: 1.0,
      low: 2.0,
    };
    return Math.max(1, Math.round(baseHours * (multipliers[priority] || 1.0)));
  };

  const validateForm = (): boolean => {
    if (!title.trim()) {
      setErrorMessage('Please enter a ticket title.');
      return false;
    }
    if (title.trim().length < 3) {
      setErrorMessage('Title must be at least 3 characters.');
      return false;
    }
    if (!description.trim()) {
      setErrorMessage('Please provide a description of the issue.');
      return false;
    }
    if (description.trim().length < 5) {
      setErrorMessage('Description must be at least 5 characters.');
      return false;
    }
    return true;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);

    if (!validateForm()) return;

    setIsSubmitting(true);
    try {
      const createdTicket = await ticketService.createTicket({
        title: title.trim(),
        description: description.trim(),
        category_id: categoryId ? Number(categoryId) : undefined,
        priority: priority,
      });

      // Navigate directly to the newly created ticket detail
      navigate(`/tickets/${createdTicket.id}`);
    } catch (err: unknown) {
      const msg = getApiErrorMessage(err, 'Failed to create ticket. Please check your submission.');
      setErrorMessage(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="create-ticket-page">
      {/* Back Button */}
      <div className="page-nav-back">
        <Link to="/tickets" className="back-link">
          <ArrowLeft size={16} />
          <span>Back to Tickets</span>
        </Link>
      </div>

      <div className="create-ticket-layout">
        {/* Main Form Column */}
        <div className="create-ticket-form-card glass-card">
          <div className="form-card-header">
            <div className="header-icon-badge">
              <PlusCircle size={22} color="#3b82f6" />
            </div>
            <div>
              <h1 className="form-title">Create New Support Ticket</h1>
              <p className="form-subtitle">Submit your IT issue or service request to the support team</p>
            </div>
          </div>

          {/* Error Banner */}
          {errorMessage && (
            <div className="alert alert-error" role="alert">
              <AlertCircle size={18} className="alert-icon" />
              <div className="alert-content">
                <span>{errorMessage}</span>
              </div>
            </div>
          )}

          <form onSubmit={handleSubmit} className="ticket-form" noValidate>
            {/* Title */}
            <div className="form-group">
              <label htmlFor="ticket-title" className="form-label required">
                Ticket Title / Summary
              </label>
              <input
                id="ticket-title"
                type="text"
                className="form-input"
                placeholder="e.g. Unable to connect to VPN from home office"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                disabled={isSubmitting}
                maxLength={255}
                autoFocus
              />
              <span className="form-hint">Summarize the issue clearly in a few words.</span>
            </div>

            {/* Category and Priority Row */}
            <div className="form-row-2col">
              {/* Category */}
              <div className="form-group">
                <label htmlFor="ticket-category" className="form-label">
                  <Layers size={14} style={{ display: 'inline', marginRight: '4px' }} />
                  Issue Category
                </label>
                <select
                  id="ticket-category"
                  className="form-select"
                  value={categoryId}
                  onChange={(e) => setCategoryId(e.target.value)}
                  disabled={isSubmitting || isLoadingCategories}
                >
                  {isLoadingCategories ? (
                    <option value="">Loading categories...</option>
                  ) : (
                    categories.map((cat) => (
                      <option key={cat.id} value={cat.id}>
                        {cat.name} (Default SLA: {cat.default_sla_hours}h)
                      </option>
                    ))
                  )}
                </select>
              </div>

              {/* Priority */}
              <div className="form-group">
                <label htmlFor="ticket-priority" className="form-label">
                  <Flag size={14} style={{ display: 'inline', marginRight: '4px' }} />
                  Urgency / Priority
                </label>
                <select
                  id="ticket-priority"
                  className="form-select"
                  value={priority}
                  onChange={(e) => setPriority(e.target.value as TicketPriority)}
                  disabled={isSubmitting}
                >
                  <option value="low">Low — Minor request or inquiry</option>
                  <option value="medium">Medium — Standard service request</option>
                  <option value="high">High — Work impaired / critical system</option>
                  <option value="critical">Critical — Complete blocker / outage</option>
                </select>
              </div>
            </div>

            {/* Description */}
            <div className="form-group">
              <label htmlFor="ticket-description" className="form-label required">
                Detailed Description
              </label>
              <textarea
                id="ticket-description"
                className="form-textarea"
                rows={6}
                placeholder="Please describe what happened, steps to reproduce the issue, any error messages displayed, and any troubleshooting already attempted..."
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                disabled={isSubmitting}
              />
              <span className="form-hint">The more details provided, the faster our IT engineers can triage and resolve your request.</span>
            </div>

            {/* Action Buttons */}
            <div className="form-actions-row">
              <Link to="/tickets" className="btn btn-secondary">
                Cancel
              </Link>
              <button
                type="submit"
                className="btn btn-primary"
                disabled={isSubmitting || isLoadingCategories}
              >
                {isSubmitting ? (
                  <>
                    <Loader2 size={18} className="spinner" />
                    <span>Creating Ticket...</span>
                  </>
                ) : (
                  <>
                    <PlusCircle size={18} />
                    <span>Submit Ticket</span>
                  </>
                )}
              </button>
            </div>
          </form>
        </div>

        {/* Side Informational Guide Column */}
        <div className="create-ticket-sidebar">
          {/* SLA Target Card */}
          <div className="sidebar-card glass-card">
            <div className="sidebar-card-header">
              <Clock size={18} color="#60a5fa" />
              <h3>Estimated SLA Target</h3>
            </div>
            <div className="sla-target-display">
              <span className="sla-hours-big">{calculateEstimatedSlaHours()} Hours</span>
              <span className="sla-target-sub">
                Target resolution for <strong>{priority.toUpperCase()}</strong> priority in{' '}
                <strong>{selectedCatObj?.name || 'General'}</strong>
              </span>
            </div>
            <p className="sla-disclaimer">
              SLA clock starts as soon as ticket is created in the queue.
            </p>
          </div>

          {/* Ticket Guidelines */}
          <div className="sidebar-card glass-card">
            <div className="sidebar-card-header">
              <Info size={18} color="#34d399" />
              <h3>Submission Tips</h3>
            </div>
            <ul className="tips-list">
              <li>
                <CheckCircle2 size={15} color="#34d399" />
                <span>Specify exact hardware models or software versions when applicable.</span>
              </li>
              <li>
                <CheckCircle2 size={15} color="#34d399" />
                <span>Include error codes or the exact wording of error popups.</span>
              </li>
              <li>
                <CheckCircle2 size={15} color="#34d399" />
                <span>Reserve <strong>Critical</strong> for widespread company-impacting blockers.</span>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
};
