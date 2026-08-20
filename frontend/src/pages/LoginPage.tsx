import React, { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { getApiErrorMessage } from '../services/api';
import { Zap, Mail, Lock, Eye, EyeOff, AlertCircle, ArrowRight, Loader2, Sparkles, Shield, User, Headphones } from 'lucide-react';

export const LoginPage: React.FC = () => {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [email, setEmail] = useState<string>('');
  const [password, setPassword] = useState<string>('');
  const [showPassword, setShowPassword] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

  const fromPath = (location.state as { from?: { pathname?: string } })?.from?.pathname || '/';

  const validateForm = (): boolean => {
    if (!email.trim()) {
      setErrorMessage('Please enter your email address.');
      return false;
    }
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email.trim())) {
      setErrorMessage('Please enter a valid email address.');
      return false;
    }
    if (!password) {
      setErrorMessage('Please enter your password.');
      return false;
    }
    return true;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);

    if (!validateForm()) {
      return;
    }

    setIsSubmitting(true);
    try {
      await login(email.trim().toLowerCase(), password);
      navigate(fromPath, { replace: true });
    } catch (err: unknown) {
      const msg = getApiErrorMessage(err, 'Failed to sign in. Please verify your credentials.');
      setErrorMessage(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleQuickFill = (fillEmail: string, fillPass: string) => {
    setEmail(fillEmail);
    setPassword(fillPass);
    setErrorMessage(null);
  };

  return (
    <div className="auth-page-wrapper">
      <div className="auth-container">
        {/* Brand Header */}
        <div className="auth-brand-header">
          <div className="auth-logo-badge">
            <Zap size={28} color="#ffffff" />
          </div>
          <h1 className="auth-brand-title">IntelliDesk</h1>
          <p className="auth-brand-subtitle">AI-Powered IT Service Desk & Support Platform</p>
        </div>

        {/* Login Card */}
        <div className="auth-card glass-card">
          <div className="auth-card-header">
            <h2 className="auth-form-title">Sign in to your account</h2>
            <p className="auth-form-subtitle">Enter your corporate credentials to continue</p>
          </div>

          {/* Error Alert */}
          {errorMessage && (
            <div className="alert alert-error" role="alert">
              <AlertCircle size={18} className="alert-icon" />
              <div className="alert-content">
                <span>{errorMessage}</span>
              </div>
            </div>
          )}

          {/* Form */}
          <form onSubmit={handleSubmit} className="auth-form" noValidate>
            <div className="form-group">
              <label htmlFor="login-email" className="form-label">
                Work Email
              </label>
              <div className="input-icon-wrapper">
                <Mail size={18} className="input-icon" />
                <input
                  id="login-email"
                  type="email"
                  className="form-input with-icon"
                  placeholder="name@company.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  disabled={isSubmitting}
                  autoComplete="email"
                  autoFocus
                />
              </div>
            </div>

            <div className="form-group">
              <div className="form-label-row">
                <label htmlFor="login-password" className="form-label">
                  Password
                </label>
              </div>
              <div className="input-icon-wrapper">
                <Lock size={18} className="input-icon" />
                <input
                  id="login-password"
                  type={showPassword ? 'text' : 'password'}
                  className="form-input with-icon with-toggle"
                  placeholder="••••••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  disabled={isSubmitting}
                  autoComplete="current-password"
                />
                <button
                  type="button"
                  className="input-toggle-btn"
                  onClick={() => setShowPassword(!showPassword)}
                  tabIndex={-1}
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              className="btn btn-primary btn-full"
              disabled={isSubmitting}
            >
              {isSubmitting ? (
                <>
                  <Loader2 size={18} className="spinner" />
                  <span>Signing in...</span>
                </>
              ) : (
                <>
                  <span>Sign In</span>
                  <ArrowRight size={18} />
                </>
              )}
            </button>
          </form>

          {/* Quick-fill Pre-seeded Credentials for Demo/Testing */}
          <div className="quick-fill-section">
            <div className="quick-fill-title">
              <Sparkles size={14} color="#60a5fa" />
              <span>Quick-Fill Test Credentials</span>
            </div>
            <div className="quick-fill-chips">
              <button
                type="button"
                className="chip-btn"
                onClick={() => handleQuickFill('admin@intellidesk.com', 'AdminPass123!')}
                title="Fill Admin Credentials"
              >
                <Shield size={13} color="#f87171" />
                <span>Admin</span>
              </button>
              <button
                type="button"
                className="chip-btn"
                onClick={() => handleQuickFill('sarah.chen@intellidesk.com', 'AgentPass123!')}
                title="Fill Support Agent Credentials"
              >
                <Headphones size={13} color="#fbbf24" />
                <span>Agent</span>
              </button>
              <button
                type="button"
                className="chip-btn"
                onClick={() => handleQuickFill('john.doe@company.com', 'UserPass123!')}
                title="Fill End-User Credentials"
              >
                <User size={13} color="#60a5fa" />
                <span>End-User</span>
              </button>
            </div>
          </div>

          {/* Footer Link */}
          <div className="auth-card-footer">
            <span>Don't have an account yet?</span>{' '}
            <Link to="/register" className="auth-link">
              Create an account
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
};
