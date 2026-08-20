import React, { useState, useEffect } from 'react';
import { AuthProvider } from './context/AuthContext';
import { apiClient } from './services/api';
import { CheckCircle, Server, Database, Shield, Zap, Lock } from 'lucide-react';

const AppContent: React.FC = () => {
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

  return (
    <div className="app-container">
      {/* Header */}
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2.5rem', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '1.5rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.875rem' }}>
          <div style={{ width: '42px', height: '42px', borderRadius: '10px', background: 'linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%)', display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: 'var(--shadow-glow)' }}>
            <Zap size={24} color="#ffffff" />
          </div>
          <div>
            <h1 style={{ fontSize: '1.5rem', fontWeight: 800, letterSpacing: '-0.025em', background: 'linear-gradient(to right, #ffffff, #93c5fd)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
              IntelliDesk
            </h1>
            <p style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)' }}>Production AI IT Service Desk Platform</p>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <div className={`badge ${backendHealth?.status === 'healthy' ? 'badge-resolved' : 'badge-in_progress'}`}>
            <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: backendHealth?.status === 'healthy' ? '#10b981' : '#f59e0b', display: 'inline-block' }}></span>
            {loadingHealth ? 'Checking Backend...' : backendHealth ? 'Backend Online' : 'Backend Disconnected'}
          </div>
        </div>
      </header>

      {/* Day 1 Completion Overview */}
      <div style={{ marginBottom: '2rem' }}>
        <div className="glass-card" style={{ background: 'linear-gradient(180deg, rgba(30, 41, 59, 0.7) 0%, rgba(15, 23, 42, 0.7) 100%)', border: '1px solid rgba(59, 130, 246, 0.2)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1rem' }}>
            <CheckCircle size={22} color="#10b981" />
            <h2 style={{ fontSize: '1.25rem', fontWeight: 700 }}>Phase 1 Foundation Operational</h2>
          </div>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.9375rem', lineHeight: '1.6', marginBottom: '1.5rem' }}>
            Day 1 backend architecture, database schema, Alembic migrations, JWT authentication, RBAC authorization, and core ticket lifecycle APIs are fully built and verified with a 100% passing test suite.
          </p>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '1rem' }}>
            <div style={{ padding: '1rem', background: 'rgba(0, 0, 0, 0.25)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem', color: '#60a5fa' }}>
                <Server size={18} />
                <span style={{ fontWeight: 600, fontSize: '0.875rem' }}>FastAPI Backend</span>
              </div>
              <p style={{ fontSize: '0.8125rem', color: 'var(--text-muted)' }}>Layered architecture (Routers, Services, Schemas, Dependencies) under <code>/api/v1</code></p>
            </div>

            <div style={{ padding: '1rem', background: 'rgba(0, 0, 0, 0.25)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem', color: '#34d399' }}>
                <Database size={18} />
                <span style={{ fontWeight: 600, fontSize: '0.875rem' }}>PostgreSQL & SQLAlchemy</span>
              </div>
              <p style={{ fontSize: '0.8125rem', color: 'var(--text-muted)' }}>Schema with Users, Categories, Tickets, Comments, KB, and Audit Trails via Alembic</p>
            </div>

            <div style={{ padding: '1rem', background: 'rgba(0, 0, 0, 0.25)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem', color: '#fbbf24' }}>
                <Shield size={18} />
                <span style={{ fontWeight: 600, fontSize: '0.875rem' }}>JWT & Role-Based Access</span>
              </div>
              <p style={{ fontSize: '0.8125rem', color: 'var(--text-muted)' }}>Multi-role guards for <strong>End-User</strong>, <strong>Support Agent</strong>, and <strong>Administrator</strong></p>
            </div>
          </div>
        </div>
      </div>

      {/* Pre-Seeded Accounts for Testing */}
      <div className="glass-card">
        <h3 style={{ fontSize: '1.0625rem', fontWeight: 700, marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <Lock size={18} color="#93c5fd" /> Pre-Seeded Test Credentials
        </h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1rem' }}>
          <div style={{ padding: '1rem', background: 'rgba(0, 0, 0, 0.2)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
            <div className="badge badge-critical" style={{ marginBottom: '0.5rem' }}>Admin Role</div>
            <p style={{ fontSize: '0.875rem', fontWeight: 600 }}>admin@intellidesk.com</p>
            <p style={{ fontSize: '0.8125rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>Password: AdminPass123!</p>
          </div>

          <div style={{ padding: '1rem', background: 'rgba(0, 0, 0, 0.2)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
            <div className="badge badge-in_progress" style={{ marginBottom: '0.5rem' }}>Agent Role</div>
            <p style={{ fontSize: '0.875rem', fontWeight: 600 }}>sarah.chen@intellidesk.com</p>
            <p style={{ fontSize: '0.8125rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>Password: AgentPass123!</p>
          </div>

          <div style={{ padding: '1rem', background: 'rgba(0, 0, 0, 0.2)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
            <div className="badge badge-open" style={{ marginBottom: '0.5rem' }}>User Role</div>
            <p style={{ fontSize: '0.875rem', fontWeight: 600 }}>john.doe@company.com</p>
            <p style={{ fontSize: '0.8125rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>Password: UserPass123!</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}

export default App;
