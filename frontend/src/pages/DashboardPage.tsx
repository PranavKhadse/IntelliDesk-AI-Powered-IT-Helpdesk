import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { ticketService } from '../services/ticketService';
import type { Ticket, TicketListResponse } from '../types';
import {
  PlusCircle,
  Ticket as TicketIcon,
  Clock,
  CheckCircle2,
  AlertTriangle,
  ArrowRight,
  Loader2,
  Sparkles,
  Shield,
  ExternalLink,
} from 'lucide-react';

export const DashboardPage: React.FC = () => {
  const { user } = useAuth();
  const [recentTickets, setRecentTickets] = useState<Ticket[]>([]);
  const [ticketStats, setTicketStats] = useState<{
    total: number;
    openCount: number;
    resolvedCount: number;
    criticalCount: number;
  }>({ total: 0, openCount: 0, resolvedCount: 0, criticalCount: 0 });
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    const fetchDashboardData = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const data: TicketListResponse = await ticketService.getTickets({ page: 1, page_size: 5 });
        if (!isMounted) return;
        setRecentTickets(data.items);

        // Fetch overall stats (or compute from recent if total small)
        const open = data.items.filter((t) => t.status === 'open' || t.status === 'in_progress').length;
        const resolved = data.items.filter((t) => t.status === 'resolved' || t.status === 'closed').length;
        const critical = data.items.filter((t) => t.priority === 'critical' || t.priority === 'high').length;

        setTicketStats({
          total: data.total,
          openCount: open,
          resolvedCount: resolved,
          criticalCount: critical,
        });
      } catch (err: unknown) {
        if (isMounted) {
          console.error('Failed to load dashboard data:', err);
          setError('Unable to load latest ticket statistics. Please check your backend connection.');
        }
      } finally {
        if (isMounted) setIsLoading(false);
      }
    };

    fetchDashboardData();
    return () => {
      isMounted = false;
    };
  }, []);

  const getRoleBadgeClass = (role?: string) => {
    switch (role) {
      case 'admin':
        return 'badge-critical';
      case 'agent':
        return 'badge-in_progress';
      default:
        return 'badge-open';
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

  const formatDate = (isoString: string) => {
    try {
      const date = new Date(isoString);
      return date.toLocaleDateString(undefined, {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return isoString;
    }
  };

  return (
    <div className="dashboard-page">
      {/* Welcome Banner */}
      <section className="welcome-banner glass-card">
        <div className="welcome-banner-content">
          <div className="welcome-tag">
            <Sparkles size={15} color="#60a5fa" />
            <span>IT Service Desk Portal</span>
          </div>
          <h1 className="welcome-heading">
            Welcome back, <span className="gradient-text">{user?.full_name}</span>
          </h1>
          <p className="welcome-subtext">
            You are logged in as{' '}
            <span className={`badge ${getRoleBadgeClass(user?.role)}`}>{user?.role}</span> in the{' '}
            <strong style={{ color: 'var(--text-primary)' }}>{user?.department || 'General'}</strong> department.
            Manage tickets, track SLA compliance, and submit service requests.
          </p>
        </div>

        <div className="welcome-banner-actions">
          <Link to="/tickets/new" className="btn btn-primary">
            <PlusCircle size={17} />
            <span>Create Ticket</span>
          </Link>
          <Link to="/tickets" className="btn btn-secondary">
            <TicketIcon size={17} />
            <span>Browse All</span>
          </Link>
        </div>
      </section>

      {/* KPI Stats Cards */}
      <section className="stats-grid">
        <div className="stat-card glass-card">
          <div className="stat-icon-wrapper blue">
            <TicketIcon size={22} color="#60a5fa" />
          </div>
          <div className="stat-details">
            <span className="stat-label">Total Tickets</span>
            <span className="stat-value">{isLoading ? '—' : ticketStats.total}</span>
          </div>
        </div>

        <div className="stat-card glass-card">
          <div className="stat-icon-wrapper amber">
            <Clock size={22} color="#fbbf24" />
          </div>
          <div className="stat-details">
            <span className="stat-label">Active / In Progress</span>
            <span className="stat-value">{isLoading ? '—' : ticketStats.openCount}</span>
          </div>
        </div>

        <div className="stat-card glass-card">
          <div className="stat-icon-wrapper green">
            <CheckCircle2 size={22} color="#34d399" />
          </div>
          <div className="stat-details">
            <span className="stat-label">Resolved & Closed</span>
            <span className="stat-value">{isLoading ? '—' : ticketStats.resolvedCount}</span>
          </div>
        </div>

        <div className="stat-card glass-card">
          <div className="stat-icon-wrapper red">
            <AlertTriangle size={22} color="#f87171" />
          </div>
          <div className="stat-details">
            <span className="stat-label">High / Critical</span>
            <span className="stat-value">{isLoading ? '—' : ticketStats.criticalCount}</span>
          </div>
        </div>
      </section>

      {/* Recent Tickets Table Section */}
      <section className="recent-tickets-section glass-card">
        <div className="section-header">
          <div className="section-title-group">
            <h2 className="section-title">Recent Tickets</h2>
            <span className="section-subtitle">Latest support issues submitted to the portal</span>
          </div>
          <Link to="/tickets" className="view-all-link">
            <span>View All Tickets</span>
            <ArrowRight size={16} />
          </Link>
        </div>

        {error && (
          <div className="alert alert-error" style={{ marginBottom: '1rem' }}>
            <span>{error}</span>
          </div>
        )}

        {isLoading ? (
          <div className="table-loading-container">
            <Loader2 size={28} className="spinner" color="#3b82f6" />
            <p>Loading recent tickets from backend...</p>
          </div>
        ) : recentTickets.length === 0 ? (
          <div className="empty-state-box">
            <div className="empty-state-icon">
              <TicketIcon size={32} color="#60a5fa" />
            </div>
            <h3 className="empty-state-title">No tickets found</h3>
            <p className="empty-state-desc">You haven't submitted any service tickets yet.</p>
            <Link to="/tickets/new" className="btn btn-primary btn-sm">
              <PlusCircle size={15} />
              <span>Create First Ticket</span>
            </Link>
          </div>
        ) : (
          <div className="table-responsive">
            <table className="tickets-table">
              <thead>
                <tr>
                  <th>Ticket #</th>
                  <th>Title & Category</th>
                  <th>Status</th>
                  <th>Priority</th>
                  <th>Assignee</th>
                  <th>Created</th>
                  <th className="text-right">Action</th>
                </tr>
              </thead>
              <tbody>
                {recentTickets.map((ticket) => (
                  <tr key={ticket.id} className="ticket-table-row">
                    <td className="ticket-id-cell">
                      <Link to={`/tickets/${ticket.id}`} className="ticket-id-badge">
                        {ticket.ticket_number}
                      </Link>
                    </td>
                    <td className="ticket-title-cell">
                      <Link to={`/tickets/${ticket.id}`} className="ticket-title-link">
                        {ticket.title}
                      </Link>
                      {ticket.category && (
                        <span className="category-pill">{ticket.category.name}</span>
                      )}
                    </td>
                    <td>{getStatusBadge(ticket.status)}</td>
                    <td>{getPriorityBadge(ticket.priority)}</td>
                    <td>
                      {ticket.assignee ? (
                        <span className="assignee-text">{ticket.assignee.full_name}</span>
                      ) : (
                        <span className="unassigned-text">Unassigned</span>
                      )}
                    </td>
                    <td className="ticket-date-cell">{formatDate(ticket.created_at)}</td>
                    <td className="text-right">
                      <Link to={`/tickets/${ticket.id}`} className="action-icon-btn" title="View Ticket Details">
                        <ExternalLink size={16} />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* Role Capabilities Guide & Testing Info */}
      <section className="role-guide-grid">
        <div className="role-card glass-card">
          <div className="role-card-header">
            <Shield size={18} color="#f87171" />
            <h3>Role & Permissions Matrix</h3>
          </div>
          <div className="role-items-list">
            <div className="role-item">
              <div className="role-pill-badge badge-critical">ADMIN</div>
              <p>Full system control, user management, category administration, and global ticket triage.</p>
            </div>
            <div className="role-item">
              <div className="role-pill-badge badge-in_progress">AGENT</div>
              <p>Support ticket assignment, status transitions, SLA monitoring, and internal agent notes.</p>
            </div>
            <div className="role-item">
              <div className="role-pill-badge badge-open">USER</div>
              <p>Submit tickets, track own ticket resolution, edit open tickets, and add public comments.</p>
            </div>
          </div>
        </div>

        <div className="role-card glass-card">
          <div className="role-card-header">
            <Sparkles size={18} color="#60a5fa" />
            <h3>Quick Role Switch Credentials</h3>
          </div>
          <p style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)', marginBottom: '1rem' }}>
            Switch accounts via Logout to test different RBAC views:
          </p>
          <div className="credential-chips-vertical">
            <div className="cred-chip">
              <div className="cred-role badge-critical">Admin</div>
              <div className="cred-meta">
                <span className="cred-email">admin@intellidesk.com</span>
                <code className="cred-pass">AdminPass123!</code>
              </div>
            </div>
            <div className="cred-chip">
              <div className="cred-role badge-in_progress">Agent</div>
              <div className="cred-meta">
                <span className="cred-email">sarah.chen@intellidesk.com</span>
                <code className="cred-pass">AgentPass123!</code>
              </div>
            </div>
            <div className="cred-chip">
              <div className="cred-role badge-open">User</div>
              <div className="cred-meta">
                <span className="cred-email">john.doe@company.com</span>
                <code className="cred-pass">UserPass123!</code>
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
};
