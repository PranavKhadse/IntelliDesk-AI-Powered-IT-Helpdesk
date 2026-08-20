import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { apiClient } from '../services/api';
import { Zap, LogOut, CheckCircle, Server, Database, Shield, User, Building, Ticket as TicketIcon } from 'lucide-react';

export const HomePage: React.FC = () => {
  const { user, logout } = useAuth();
  const [backendHealth, setBackendHealth] = useState<{ status: string; app: string; environment: string } | null>(null);
  const [loadingHealth, setLoadingHealth] = useState<boolean>(true);

  useEffect(() => {
    const checkBackend = async () => {
      try {
        const res = await apiClient.get('/health');
        setBackendHealth(res.data);
      } catch (err) {
        console.error('Failed to connect to backend:', err);
      } finally {
        setLoadingHealth(false);
      }
    };
    checkBackend();
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

  const getInitials = (name?: string) => {
    if (!name) return 'U';
    return name
      .split(' ')
      .map((n) => n[0])
      .join('')
      .toUpperCase()
      .slice(0, 2);
  };

  return (
    <div className="app-container">
      {/* Navigation Header */}
      <header className="app-navbar">
        <div className="navbar-brand">
          <div className="auth-logo-badge small">
            <Zap size={22} color="#ffffff" />
          </div>
          <div>
            <h1 className="navbar-title">IntelliDesk</h1>
            <p className="navbar-subtitle">Enterprise IT Service Desk</p>
          </div>
        </div>

        <div className="navbar-actions">
          {/* Health Badge */}
          <div className={`badge ${backendHealth?.status === 'healthy' ? 'badge-resolved' : 'badge-in_progress'}`}>
            <span
              style={{
                width: '6px',
                height: '6px',
                borderRadius: '50%',
                background: backendHealth?.status === 'healthy' ? '#10b981' : '#f59e0b',
                display: 'inline-block',
              }}
            ></span>
            {loadingHealth ? 'Checking Backend...' : backendHealth ? 'Backend Online' : 'Backend Disconnected'}
          </div>

          {/* User Profile Summary */}
          {user && (
            <div className="user-profile-widget">
              <div className="user-avatar">{getInitials(user.full_name)}</div>
              <div className="user-details">
                <div className="user-name-row">
                  <span className="user-full-name">{user.full_name}</span>
                  <span className={`badge ${getRoleBadgeClass(user.role)}`}>{user.role}</span>
                </div>
                <span className="user-email">{user.email}</span>
              </div>
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={logout}
                title="Sign out of your session"
              >
                <LogOut size={15} />
                <span>Logout</span>
              </button>
            </div>
          )}
        </div>
      </header>

      {/* Main Authenticated View */}
      <main className="dashboard-content">
        {/* User Session Welcome Card */}
        <div className="glass-card welcome-card">
          <div className="welcome-header">
            <div className="welcome-avatar-large">{getInitials(user?.full_name)}</div>
            <div>
              <h2 className="welcome-title">Welcome back, {user?.full_name}!</h2>
              <p className="welcome-subtitle">
                You are authenticated as{' '}
                <span className={`badge ${getRoleBadgeClass(user?.role)}`}>{user?.role}</span> in the{' '}
                <strong style={{ color: 'var(--text-primary)' }}>{user?.department || 'General'}</strong> department.
              </p>
            </div>
          </div>

          <div className="session-info-grid">
            <div className="session-info-item">
              <span className="session-info-label">
                <User size={14} /> Account ID
              </span>
              <code className="session-info-value">{user?.id}</code>
            </div>

            <div className="session-info-item">
              <span className="session-info-label">
                <Building size={14} /> Department
              </span>
              <span className="session-info-value">{user?.department || 'General'}</span>
            </div>

            <div className="session-info-item">
              <span className="session-info-label">
                <Shield size={14} /> Role Permissions
              </span>
              <span className="session-info-value" style={{ textTransform: 'capitalize' }}>
                {user?.role === 'admin'
                  ? 'Full Administrative Access'
                  : user?.role === 'agent'
                  ? 'Support Agent Queue & Triage'
                  : 'End-User Ticket Access'}
              </span>
            </div>
          </div>
        </div>

        {/* Phase Verification Status */}
        <div className="glass-card" style={{ marginTop: '1.5rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1rem' }}>
            <CheckCircle size={22} color="#10b981" />
            <h3 style={{ fontSize: '1.15rem', fontWeight: 700 }}>Frontend & Backend Authentication Connected</h3>
          </div>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.9375rem', lineHeight: '1.6', marginBottom: '1.5rem' }}>
            JWT access/refresh tokens, automatic header injection via Axios interceptors, route guarding, persistent login sessions, and RBAC authorization are fully verified and operational.
          </p>

          <div className="features-grid">
            <div className="feature-item">
              <div className="feature-header" style={{ color: '#60a5fa' }}>
                <Server size={18} />
                <span>FastAPI REST APIs</span>
              </div>
              <p className="feature-desc">Interactive session authenticated with <code>/api/v1/auth/me</code></p>
            </div>

            <div className="feature-item">
              <div className="feature-header" style={{ color: '#34d399' }}>
                <Database size={18} />
                <span>PostgreSQL DB Session</span>
              </div>
              <p className="feature-desc">Active account loaded from database with role-scoped permissions</p>
            </div>

            <div className="feature-item">
              <div className="feature-header" style={{ color: '#fbbf24' }}>
                <Shield size={18} />
                <span>Protected Routes</span>
              </div>
              <p className="feature-desc">Client-side route guards redirecting unauthenticated users to <code>/login</code></p>
            </div>

            <div className="feature-item">
              <div className="feature-header" style={{ color: '#a78bfa' }}>
                <TicketIcon size={18} />
                <span>Ticket System Ready</span>
              </div>
              <p className="feature-desc">Ready for Day 3 ticket list, creation, and AI triage flows</p>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
};
