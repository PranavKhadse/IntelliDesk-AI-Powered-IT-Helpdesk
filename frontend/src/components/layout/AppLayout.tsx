import React, { useState, useEffect } from 'react';
import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { apiClient } from '../../services/api';
import {
  Zap,
  LayoutDashboard,
  Ticket,
  PlusCircle,
  LogOut,
  Menu,
  X,
  User,
  Shield,
  Headphones,
  BookOpen,
  BarChart3,
} from 'lucide-react';

export const AppLayout: React.FC = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [backendHealthy, setBackendHealthy] = useState<boolean | null>(null);

  const isStaff = user?.role === 'agent' || user?.role === 'admin';

  useEffect(() => {
    let isMounted = true;
    const checkHealth = async () => {
      try {
        const res = await apiClient.get('/health');
        if (isMounted) setBackendHealthy(res.data?.status === 'healthy');
      } catch {
        if (isMounted) setBackendHealthy(false);
      }
    };
    checkHealth();
    const interval = setInterval(checkHealth, 30000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  const handleLogout = () => {
    logout();
    navigate('/login', { replace: true });
  };

  const getRoleIcon = (role?: string) => {
    switch (role) {
      case 'admin':
        return <Shield size={13} color="#f87171" />;
      case 'agent':
        return <Headphones size={13} color="#fbbf24" />;
      default:
        return <User size={13} color="#60a5fa" />;
    }
  };

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
    <div className="app-shell">
      {/* Top Main Navigation Header */}
      <header className="main-navbar">
        <div className="navbar-left">
          {/* Logo */}
          <NavLink to="/" className="brand-logo-link">
            <div className="auth-logo-badge small">
              <Zap size={20} color="#ffffff" />
            </div>
            <div className="brand-text">
              <span className="brand-title">IntelliDesk</span>
              <span className="brand-sub">IT Service Desk</span>
            </div>
          </NavLink>

          {/* Desktop Navigation Links */}
          <nav className="desktop-nav">
            <NavLink
              to="/"
              end
              className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
            >
              <LayoutDashboard size={17} />
              <span>Dashboard</span>
            </NavLink>

            {isStaff && (
              <NavLink
                to="/analytics"
                className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
              >
                <BarChart3 size={17} />
                <span>Analytics</span>
              </NavLink>
            )}

            <NavLink
              to="/tickets"
              end
              className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
            >
              <Ticket size={17} />
              <span>My Tickets</span>
            </NavLink>

            <NavLink
              to="/kb"
              className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
            >
              <BookOpen size={17} />
              <span>Knowledge Base</span>
            </NavLink>

            <NavLink
              to="/tickets/new"
              className={({ isActive }) => `nav-link create-link ${isActive ? 'active' : ''}`}
            >
              <PlusCircle size={17} />
              <span>Create Ticket</span>
            </NavLink>
          </nav>
        </div>

        {/* Right Section: Health, Profile & Logout */}
        <div className="navbar-right">
          {/* Backend Status Indicator */}
          <div
            className={`status-pill ${
              backendHealthy === true ? 'healthy' : backendHealthy === false ? 'offline' : 'checking'
            }`}
            title={backendHealthy ? 'Backend API connected' : 'Backend offline'}
          >
            <span className="status-dot"></span>
            <span className="status-label">
              {backendHealthy === true ? 'Online' : backendHealthy === false ? 'Offline' : 'Connecting'}
            </span>
          </div>

          {/* User Profile Summary */}
          {user && (
            <div className="user-nav-profile">
              <div className="user-nav-avatar">{getInitials(user.full_name)}</div>
              <div className="user-nav-meta">
                <div className="user-nav-name">{user.full_name}</div>
                <div className="user-nav-badge-row">
                  <span className={`badge ${getRoleBadgeClass(user.role)} small-badge`}>
                    {getRoleIcon(user.role)}
                    <span>{user.role}</span>
                  </span>
                  <span className="user-nav-dept">{user.department}</span>
                </div>
              </div>
            </div>
          )}

          {/* Logout Button */}
          <button
            type="button"
            className="btn btn-secondary btn-sm logout-btn"
            onClick={handleLogout}
            title="Sign out of IntelliDesk"
          >
            <LogOut size={15} />
            <span className="logout-text">Logout</span>
          </button>

          {/* Mobile Menu Toggle */}
          <button
            type="button"
            className="mobile-menu-btn"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            aria-label="Toggle navigation menu"
          >
            {mobileMenuOpen ? <X size={22} /> : <Menu size={22} />}
          </button>
        </div>
      </header>

      {/* Mobile Navigation Dropdown */}
      {mobileMenuOpen && (
        <div className="mobile-nav-drawer glass-card">
          <NavLink
            to="/"
            end
            className={({ isActive }) => `mobile-nav-link ${isActive ? 'active' : ''}`}
            onClick={() => setMobileMenuOpen(false)}
          >
            <LayoutDashboard size={18} />
            <span>Dashboard</span>
          </NavLink>

          {isStaff && (
            <NavLink
              to="/analytics"
              className={({ isActive }) => `mobile-nav-link ${isActive ? 'active' : ''}`}
              onClick={() => setMobileMenuOpen(false)}
            >
              <BarChart3 size={18} />
              <span>Analytics</span>
            </NavLink>
          )}

          <NavLink
            to="/tickets"
            end
            className={({ isActive }) => `mobile-nav-link ${isActive ? 'active' : ''}`}
            onClick={() => setMobileMenuOpen(false)}
          >
            <Ticket size={18} />
            <span>My Tickets</span>
          </NavLink>

          <NavLink
            to="/kb"
            className={({ isActive }) => `mobile-nav-link ${isActive ? 'active' : ''}`}
            onClick={() => setMobileMenuOpen(false)}
          >
            <BookOpen size={18} />
            <span>Knowledge Base</span>
          </NavLink>

          <NavLink
            to="/tickets/new"
            className={({ isActive }) => `mobile-nav-link ${isActive ? 'active' : ''}`}
            onClick={() => setMobileMenuOpen(false)}
          >
            <PlusCircle size={18} />
            <span>Create Ticket</span>
          </NavLink>
        </div>
      )}

      {/* Main Page Outlet */}
      <main className="main-content-container">
        <Outlet />
      </main>
    </div>
  );
};
