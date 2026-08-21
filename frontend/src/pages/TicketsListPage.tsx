import React, { useState, useEffect, useCallback } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { ticketService } from '../services/ticketService';
import type { Ticket, Category, TicketFilterParams } from '../types';
import {
  Ticket as TicketIcon,
  PlusCircle,
  Search,
  RotateCcw,
  ChevronLeft,
  ChevronRight,
  Loader2,
  ExternalLink,
  UserCheck,
  AlertCircle,
} from 'lucide-react';

export const TicketsListPage: React.FC = () => {
  const { user } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const requestedPage = Number(searchParams.get('page'));

  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [totalCount, setTotalCount] = useState<number>(0);
  const [totalPages, setTotalPages] = useState<number>(1);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Filters
  const [searchTerm, setSearchTerm] = useState<string>(searchParams.get('search') || '');
  const [selectedStatus, setSelectedStatus] = useState<string>(searchParams.get('status') || '');
  const [selectedPriority, setSelectedPriority] = useState<string>(searchParams.get('priority') || '');
  const [selectedCategory, setSelectedCategory] = useState<string>(searchParams.get('category_id') || '');
  const [assignedToMe, setAssignedToMe] = useState<boolean>(searchParams.get('assigned_to_me') === 'true');
  const [currentPage, setCurrentPage] = useState<number>(
    Number.isInteger(requestedPage) && requestedPage > 0 ? requestedPage : 1
  );
  const pageSize = 15;

  const isStaff = user?.role === 'agent' || user?.role === 'admin';

  // Load categories for filter dropdown
  useEffect(() => {
    const loadCategories = async () => {
      try {
        const cats = await ticketService.getCategories();
        setCategories(cats);
      } catch (err) {
        console.error('Failed to load categories:', err);
      }
    };
    loadCategories();
  }, []);

  // Fetch tickets with active filters
  const fetchTickets = useCallback(async () => {
    setIsLoading(true);
    setErrorMessage(null);

    const params: TicketFilterParams = {
      page: currentPage,
      page_size: pageSize,
    };

    if (searchTerm.trim()) params.search = searchTerm.trim();
    if (selectedStatus) params.status = selectedStatus;
    if (selectedPriority) params.priority = selectedPriority;
    const categoryId = Number(selectedCategory);
    if (Number.isInteger(categoryId) && categoryId > 0) params.category_id = categoryId;
    if (assignedToMe && isStaff) params.assigned_to_me = true;

    try {
      const res = await ticketService.getTickets(params);
      setTickets(res.items);
      setTotalCount(res.total);
      setTotalPages(res.total_pages);
    } catch (err: unknown) {
      console.error('Error fetching tickets:', err);
      setErrorMessage('Could not load tickets from the server. Please check your connection.');
    } finally {
      setIsLoading(false);
    }
  }, [currentPage, pageSize, searchTerm, selectedStatus, selectedPriority, selectedCategory, assignedToMe, isStaff]);

  useEffect(() => {
    fetchTickets();
  }, [fetchTickets]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setCurrentPage(1);
  };

  const handleResetFilters = () => {
    setSearchTerm('');
    setSelectedStatus('');
    setSelectedPriority('');
    setSelectedCategory('');
    setAssignedToMe(false);
    setCurrentPage(1);
    setSearchParams({});
  };

  const hasActiveFilters = Boolean(
    searchTerm || selectedStatus || selectedPriority || selectedCategory || assignedToMe
  );

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
        year: 'numeric',
      });
    } catch {
      return isoString;
    }
  };

  return (
    <div className="tickets-page">
      {/* Page Header */}
      <div className="page-header">
        <div className="page-header-left">
          <div className="page-icon-badge">
            <TicketIcon size={24} color="#60a5fa" />
          </div>
          <div>
            <div className="page-title-row">
              <h1 className="page-title">{isStaff ? 'Service Desk Tickets' : 'My Tickets'}</h1>
              <span className="count-badge">{totalCount} Total</span>
            </div>
            <p className="page-subtitle">
              {isStaff
                ? 'Manage, assign, and resolve support tickets across the organization.'
                : 'Track the status and resolution timeline of your service requests.'}
            </p>
          </div>
        </div>

        <Link to="/tickets/new" className="btn btn-primary">
          <PlusCircle size={17} />
          <span>New Ticket</span>
        </Link>
      </div>

      {/* Filter & Search Toolbar */}
      <div className="filter-toolbar glass-card">
        <form onSubmit={handleSearchSubmit} className="search-form">
          <div className="input-icon-wrapper search-input-wrapper">
            <Search size={18} className="input-icon" />
            <input
              type="text"
              className="form-input with-icon"
              placeholder="Search by ticket number, title, or issue description..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
        </form>

        <div className="filters-row">
          {/* Status Dropdown */}
          <div className="filter-select-wrapper">
            <select
              className="form-select filter-select"
              value={selectedStatus}
              onChange={(e) => {
                setSelectedStatus(e.target.value);
                setCurrentPage(1);
              }}
            >
              <option value="">All Statuses</option>
              <option value="open">Open</option>
              <option value="in_progress">In Progress</option>
              <option value="pending_customer">Pending Customer</option>
              <option value="resolved">Resolved</option>
              <option value="closed">Closed</option>
            </select>
          </div>

          {/* Priority Dropdown */}
          <div className="filter-select-wrapper">
            <select
              className="form-select filter-select"
              value={selectedPriority}
              onChange={(e) => {
                setSelectedPriority(e.target.value);
                setCurrentPage(1);
              }}
            >
              <option value="">All Priorities</option>
              <option value="critical">Critical</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </select>
          </div>

          {/* Category Dropdown */}
          <div className="filter-select-wrapper">
            <select
              className="form-select filter-select"
              value={selectedCategory}
              onChange={(e) => {
                setSelectedCategory(e.target.value);
                setCurrentPage(1);
              }}
            >
              <option value="">All Categories</option>
              {categories.map((cat) => (
                <option key={cat.id} value={cat.id}>
                  {cat.name}
                </option>
              ))}
            </select>
          </div>

          {/* Assigned to me toggle for Staff */}
          {isStaff && (
            <label className="assigned-toggle-label" title="Show only tickets assigned to you">
              <input
                type="checkbox"
                checked={assignedToMe}
                onChange={(e) => {
                  setAssignedToMe(e.target.checked);
                  setCurrentPage(1);
                }}
              />
              <UserCheck size={16} color={assignedToMe ? '#3b82f6' : 'var(--text-muted)'} />
              <span>Assigned to me</span>
            </label>
          )}

          {/* Reset Filters */}
          {hasActiveFilters && (
            <button
              type="button"
              className="btn btn-secondary btn-sm reset-btn"
              onClick={handleResetFilters}
              title="Clear all active filters"
            >
              <RotateCcw size={14} />
              <span>Reset</span>
            </button>
          )}
        </div>
      </div>

      {/* Error Alert */}
      {errorMessage && (
        <div className="alert alert-error" style={{ marginBottom: '1.5rem' }}>
          <AlertCircle size={18} className="alert-icon" />
          <div className="alert-content">
            <span>{errorMessage}</span>
          </div>
          <button type="button" className="btn btn-secondary btn-sm" onClick={fetchTickets} style={{ marginLeft: 'auto' }}>
            Retry
          </button>
        </div>
      )}

      {/* Tickets List / Table */}
      <div className="tickets-content-card glass-card">
        {isLoading ? (
          <div className="table-loading-container">
            <Loader2 size={32} className="spinner" color="#3b82f6" />
            <p>Loading tickets from database...</p>
          </div>
        ) : tickets.length === 0 ? (
          <div className="empty-state-box">
            <div className="empty-state-icon">
              <TicketIcon size={36} color="#60a5fa" />
            </div>
            <h3 className="empty-state-title">
              {hasActiveFilters ? 'No tickets match your filters' : 'No tickets submitted yet'}
            </h3>
            <p className="empty-state-desc">
              {hasActiveFilters
                ? 'Try adjusting your search criteria or resetting filters.'
                : 'Need assistance? Create a new support ticket to get help from the IT team.'}
            </p>
            {hasActiveFilters ? (
              <button type="button" className="btn btn-secondary" onClick={handleResetFilters}>
                <RotateCcw size={15} />
                <span>Reset Filters</span>
              </button>
            ) : (
              <Link to="/tickets/new" className="btn btn-primary">
                <PlusCircle size={17} />
                <span>Create Ticket</span>
              </Link>
            )}
          </div>
        ) : (
          <>
            <div className="table-responsive">
              <table className="tickets-table">
                <thead>
                  <tr>
                    <th>Ticket ID</th>
                    <th>Title & Category</th>
                    <th>Status</th>
                    <th>Priority</th>
                    <th>Assignee</th>
                    <th>Created</th>
                    <th className="text-right">Action</th>
                  </tr>
                </thead>
                <tbody>
                  {tickets.map((ticket) => (
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
                        <div className="ticket-meta-subtitle">
                          {ticket.category ? (
                            <span className="category-pill">{ticket.category.name}</span>
                          ) : (
                            <span className="category-pill muted">General</span>
                          )}
                          {isStaff && ticket.creator && (
                            <span className="creator-pill">by {ticket.creator.full_name}</span>
                          )}
                        </div>
                      </td>
                      <td>{getStatusBadge(ticket.status)}</td>
                      <td>{getPriorityBadge(ticket.priority)}</td>
                      <td>
                        {ticket.assignee ? (
                          <div className="assignee-pill">
                            <span className="assignee-dot"></span>
                            <span className="assignee-text">{ticket.assignee.full_name}</span>
                          </div>
                        ) : (
                          <span className="unassigned-text">Unassigned</span>
                        )}
                      </td>
                      <td className="ticket-date-cell">{formatDate(ticket.created_at)}</td>
                      <td className="text-right">
                        <Link
                          to={`/tickets/${ticket.id}`}
                          className="btn btn-secondary btn-sm action-view-btn"
                          title="View full details and conversation"
                        >
                          <span>View</span>
                          <ExternalLink size={14} />
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination Controls */}
            <div className="pagination-bar">
              <div className="pagination-info">
                Showing{' '}
                <strong>
                  {totalCount === 0 ? 0 : (currentPage - 1) * pageSize + 1} -{' '}
                  {Math.min(currentPage * pageSize, totalCount)}
                </strong>{' '}
                of <strong>{totalCount}</strong> tickets
              </div>

              {totalPages > 1 && (
                <div className="pagination-controls">
                  <button
                    type="button"
                    className="pagination-btn"
                    disabled={currentPage <= 1}
                    onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                    aria-label="Previous Page"
                  >
                    <ChevronLeft size={18} />
                    <span>Previous</span>
                  </button>

                  <span className="pagination-current-page">
                    Page {currentPage} of {totalPages}
                  </span>

                  <button
                    type="button"
                    className="pagination-btn"
                    disabled={currentPage >= totalPages}
                    onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                    aria-label="Next Page"
                  >
                    <span>Next</span>
                    <ChevronRight size={18} />
                  </button>
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
};
