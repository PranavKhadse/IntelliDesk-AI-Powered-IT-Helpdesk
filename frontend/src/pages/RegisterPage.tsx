import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { getApiErrorMessage } from '../services/api';
import { Zap, Mail, Lock, Eye, EyeOff, User, Building2, AlertCircle, ArrowRight, Loader2 } from 'lucide-react';

export const RegisterPage: React.FC = () => {
  const { register } = useAuth();
  const navigate = useNavigate();

  const [fullName, setFullName] = useState<string>('');
  const [email, setEmail] = useState<string>('');
  const [department, setDepartment] = useState<string>('General');
  const [password, setPassword] = useState<string>('');
  const [confirmPassword, setConfirmPassword] = useState<string>('');
  const [showPassword, setShowPassword] = useState<boolean>(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

  const departments = [
    'General',
    'IT Operations',
    'Engineering',
    'Finance',
    'Human Resources',
    'Sales',
    'Customer Support',
    'Marketing',
  ];

  const validateForm = (): boolean => {
    if (!fullName.trim()) {
      setErrorMessage('Please enter your full name.');
      return false;
    }
    if (fullName.trim().length < 2) {
      setErrorMessage('Full name must be at least 2 characters.');
      return false;
    }
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
      setErrorMessage('Please enter a password.');
      return false;
    }
    if (password.length < 8) {
      setErrorMessage('Password must be at least 8 characters long.');
      return false;
    }
    if (password !== confirmPassword) {
      setErrorMessage('Passwords do not match. Please check and re-enter.');
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
      await register(email.trim().toLowerCase(), password, fullName.trim(), department);
      navigate('/', { replace: true });
    } catch (err: unknown) {
      const msg = getApiErrorMessage(err, 'Failed to create account. Please try again.');
      setErrorMessage(msg);
    } finally {
      setIsSubmitting(false);
    }
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

        {/* Register Card */}
        <div className="auth-card glass-card">
          <div className="auth-card-header">
            <h2 className="auth-form-title">Create your account</h2>
            <p className="auth-form-subtitle">Join your organization's IT service desk workspace</p>
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
              <label htmlFor="reg-name" className="form-label">
                Full Name
              </label>
              <div className="input-icon-wrapper">
                <User size={18} className="input-icon" />
                <input
                  id="reg-name"
                  type="text"
                  className="form-input with-icon"
                  placeholder="e.g. Alex Morgan"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  disabled={isSubmitting}
                  autoComplete="name"
                  autoFocus
                />
              </div>
            </div>

            <div className="form-group">
              <label htmlFor="reg-email" className="form-label">
                Work Email
              </label>
              <div className="input-icon-wrapper">
                <Mail size={18} className="input-icon" />
                <input
                  id="reg-email"
                  type="email"
                  className="form-input with-icon"
                  placeholder="name@company.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  disabled={isSubmitting}
                  autoComplete="email"
                />
              </div>
            </div>

            <div className="form-group">
              <label htmlFor="reg-department" className="form-label">
                Department
              </label>
              <div className="input-icon-wrapper">
                <Building2 size={18} className="input-icon" />
                <select
                  id="reg-department"
                  className="form-select with-icon"
                  value={department}
                  onChange={(e) => setDepartment(e.target.value)}
                  disabled={isSubmitting}
                >
                  {departments.map((dept) => (
                    <option key={dept} value={dept}>
                      {dept}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="form-group">
              <label htmlFor="reg-password" className="form-label">
                Password
              </label>
              <div className="input-icon-wrapper">
                <Lock size={18} className="input-icon" />
                <input
                  id="reg-password"
                  type={showPassword ? 'text' : 'password'}
                  className="form-input with-icon with-toggle"
                  placeholder="At least 8 characters"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  disabled={isSubmitting}
                  autoComplete="new-password"
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

            <div className="form-group">
              <label htmlFor="reg-confirm-password" className="form-label">
                Confirm Password
              </label>
              <div className="input-icon-wrapper">
                <Lock size={18} className="input-icon" />
                <input
                  id="reg-confirm-password"
                  type={showConfirmPassword ? 'text' : 'password'}
                  className="form-input with-icon with-toggle"
                  placeholder="Re-enter password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  disabled={isSubmitting}
                  autoComplete="new-password"
                />
                <button
                  type="button"
                  className="input-toggle-btn"
                  onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                  tabIndex={-1}
                  aria-label={showConfirmPassword ? 'Hide confirm password' : 'Show confirm password'}
                >
                  {showConfirmPassword ? <EyeOff size={18} /> : <Eye size={18} />}
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
                  <span>Creating account...</span>
                </>
              ) : (
                <>
                  <span>Create Account</span>
                  <ArrowRight size={18} />
                </>
              )}
            </button>
          </form>

          {/* Footer Link */}
          <div className="auth-card-footer">
            <span>Already have an account?</span>{' '}
            <Link to="/login" className="auth-link">
              Sign in
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
};
