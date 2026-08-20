import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Loader2 } from 'lucide-react';

interface PublicOnlyRouteProps {
  children?: React.ReactNode;
}

export const PublicOnlyRoute: React.FC<PublicOnlyRouteProps> = ({ children }) => {
  const { user, isAuthenticated, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <div className="auth-loading-screen">
        <div className="auth-loading-card glass-card">
          <Loader2 className="spinner" size={36} color="#3b82f6" />
          <p className="auth-loading-text">Loading...</p>
        </div>
      </div>
    );
  }

  if (isAuthenticated && user) {
    const fromPath = (location.state as { from?: { pathname?: string } })?.from?.pathname || '/';
    return <Navigate to={fromPath} replace />;
  }

  return children ? <>{children}</> : null;
};
