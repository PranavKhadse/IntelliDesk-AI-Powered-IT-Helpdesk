import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../context/AuthContext';
import { analyticsService } from '../services/analyticsService';
import { getApiErrorMessage } from '../services/api';
import type {
  OperationsAnalyticsDashboardResponse,
  AnalyticsTimePreset,
} from '../types';
import {
  TrendingUp,
  Clock,
  CheckCircle2,
  Users,
  Sparkles,
  RotateCw,
  Loader2,
  AlertCircle,
  BookOpen,
  Layers,
  Flag,
  Activity,
  CheckCircle,
  XCircle,
  BarChart3,
  Calendar,
} from 'lucide-react';

export const AnalyticsPage: React.FC = () => {
  const { user } = useAuth();
  const [data, setData] = useState<OperationsAnalyticsDashboardResponse | null>(null);
  const [preset, setPreset] = useState<AnalyticsTimePreset>('30d');
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const loadAnalytics = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await analyticsService.getDashboardAnalytics(preset);
      setData(res);
    } catch (err: unknown) {
      console.error('Failed to load analytics:', err);
      setError(getApiErrorMessage(err, 'Failed to retrieve operations analytics data.'));
    } finally {
      setIsLoading(false);
    }
  }, [preset]);

  useEffect(() => {
    loadAnalytics();
  }, [loadAnalytics]);

  const formatHours = (hrs: number): string => {
    if (hrs <= 0) return '0h';
    if (hrs < 1) {
      return `${Math.round(hrs * 60)}m`;
    }
    return `${hrs.toFixed(1)}h`;
  };

  const getMaxTrendCount = (): number => {
    if (!data?.volume_trend || data.volume_trend.length === 0) return 1;
    const maxVal = Math.max(
      ...data.volume_trend.map((p) => Math.max(p.created_count, p.resolved_count))
    );
    return Math.max(maxVal, 1);
  };

  return (
    <div className="analytics-page">
      {/* Header & Date Range Controls */}
      <section className="analytics-header-section glass-card">
        <div className="analytics-title-group">
          <div className="header-badge-row">
            <div className="analytics-icon-badge">
              <BarChart3 size={20} color="#60a5fa" />
            </div>
            <span className="analytics-badge-label">
              {user?.role === 'admin' ? 'Executive Operations Dashboard' : 'Team Operations Analytics'}
            </span>
          </div>
          <h1 className="analytics-main-title">
            Operations & Management <span className="gradient-text">Analytics</span>
          </h1>
          <p className="analytics-subtitle">
            Real-time ticket throughput, SLA compliance metrics, agent workload distribution, and AI operational intelligence.
          </p>
        </div>

        <div className="analytics-controls-bar">
          <div className="preset-toggle-group">
            <button
              type="button"
              className={`preset-btn ${preset === '7d' ? 'active' : ''}`}
              onClick={() => setPreset('7d')}
              disabled={isLoading}
            >
              7 Days
            </button>
            <button
              type="button"
              className={`preset-btn ${preset === '30d' ? 'active' : ''}`}
              onClick={() => setPreset('30d')}
              disabled={isLoading}
            >
              30 Days
            </button>
            <button
              type="button"
              className={`preset-btn ${preset === '90d' ? 'active' : ''}`}
              onClick={() => setPreset('90d')}
              disabled={isLoading}
            >
              90 Days
            </button>
            <button
              type="button"
              className={`preset-btn ${preset === 'all' ? 'active' : ''}`}
              onClick={() => setPreset('all')}
              disabled={isLoading}
            >
              All Time
            </button>
          </div>

          <button
            type="button"
            className="btn btn-secondary btn-sm refresh-btn"
            onClick={loadAnalytics}
            disabled={isLoading}
            title="Refresh analytics data"
          >
            <RotateCw size={15} className={isLoading ? 'spinner' : ''} />
            <span>Refresh</span>
          </button>
        </div>
      </section>

      {/* Error Alert */}
      {error && (
        <div className="alert alert-error" style={{ marginBottom: '1.5rem' }}>
          <AlertCircle size={18} />
          <span>{error}</span>
        </div>
      )}

      {/* Loading Overlay */}
      {isLoading && !data && (
        <div className="analytics-loading-box glass-card">
          <Loader2 size={36} className="spinner" color="#38bdf8" />
          <p>Aggregating operations metrics and calculating SLA performance...</p>
        </div>
      )}

      {data && (
        <>
          {/* Executive KPI Ribbon */}
          <section className="analytics-kpi-grid">
            <div className="analytics-kpi-card glass-card">
              <div className="kpi-icon-wrapper blue">
                <TrendingUp size={22} color="#60a5fa" />
              </div>
              <div className="kpi-data">
                <span className="kpi-label">Total Volume</span>
                <span className="kpi-value">{data.volume_metrics.total_tickets}</span>
                <span className="kpi-subtext">
                  Resolution Rate: <strong>{data.volume_metrics.resolution_rate_pct}%</strong>
                </span>
              </div>
            </div>

            <div className="analytics-kpi-card glass-card">
              <div className="kpi-icon-wrapper amber">
                <Clock size={22} color="#fbbf24" />
              </div>
              <div className="kpi-data">
                <span className="kpi-label">Active Backlog</span>
                <span className="kpi-value">{data.volume_metrics.active_backlog}</span>
                <span className="kpi-subtext">
                  {data.volume_metrics.open_tickets} Open • {data.volume_metrics.in_progress_tickets} In Progress
                </span>
              </div>
            </div>

            <div className="analytics-kpi-card glass-card">
              <div className={`kpi-icon-wrapper ${data.sla_metrics.compliance_rate_pct >= 85 ? 'green' : 'red'}`}>
                <CheckCircle2 size={22} color={data.sla_metrics.compliance_rate_pct >= 85 ? '#34d399' : '#f87171'} />
              </div>
              <div className="kpi-data">
                <span className="kpi-label">SLA Compliance</span>
                <span className="kpi-value">{data.sla_metrics.compliance_rate_pct}%</span>
                <span className="kpi-subtext">
                  {data.sla_metrics.breached_count + data.sla_metrics.resolved_breached_count} Breached Tickets
                </span>
              </div>
            </div>

            <div className="analytics-kpi-card glass-card">
              <div className="kpi-icon-wrapper cyan">
                <Activity size={22} color="#38bdf8" />
              </div>
              <div className="kpi-data">
                <span className="kpi-label">Avg First Response</span>
                <span className="kpi-value">{formatHours(data.first_response_metrics.avg_first_response_hours)}</span>
                <span className="kpi-subtext">
                  Compliance: <strong>{data.first_response_metrics.first_response_compliance_pct}%</strong>
                </span>
              </div>
            </div>

            <div className="analytics-kpi-card glass-card">
              <div className="kpi-icon-wrapper purple">
                <Clock size={22} color="#a78bfa" />
              </div>
              <div className="kpi-data">
                <span className="kpi-label">Avg Resolution</span>
                <span className="kpi-value">{formatHours(data.resolution_metrics.avg_resolution_hours)}</span>
                <span className="kpi-subtext">
                  Median: {formatHours(data.resolution_metrics.median_resolution_hours)}
                </span>
              </div>
            </div>

            <div className="analytics-kpi-card glass-card">
              <div className="kpi-icon-wrapper indigo">
                <Sparkles size={22} color="#818cf8" />
              </div>
              <div className="kpi-data">
                <span className="kpi-label">AI Acceptance Rate</span>
                <span className="kpi-value">{data.ai_adoption.triage_acceptance_rate_pct}%</span>
                <span className="kpi-subtext">
                  {data.ai_adoption.triage_accepted} Accepted • {data.ai_adoption.total_sla_risk_evaluations} SLA Risks
                </span>
              </div>
            </div>
          </section>

          {/* Primary Operations Visualizations Grid */}
          <section className="analytics-charts-grid">
            {/* Ticket Volume Trends */}
            <div className="chart-card glass-card">
              <div className="chart-card-header">
                <div className="chart-header-title">
                  <Calendar size={18} color="#60a5fa" />
                  <h3>Ticket Volume & Throughput Trend</h3>
                </div>
                <div className="trend-legend">
                  <span className="legend-item created">
                    <span className="legend-dot created" /> Created ({data.volume_metrics.total_tickets})
                  </span>
                  <span className="legend-item resolved">
                    <span className="legend-dot resolved" /> Resolved ({data.volume_metrics.resolved_tickets + data.volume_metrics.closed_tickets})
                  </span>
                </div>
              </div>

              {data.volume_trend.length === 0 ? (
                <div className="chart-empty-state">
                  <p>No ticket activity in the selected date window.</p>
                </div>
              ) : (
                <div className="trend-bars-container">
                  {data.volume_trend.map((pt) => {
                    const maxCount = getMaxTrendCount();
                    const createdH = Math.max(4, Math.round((pt.created_count / maxCount) * 120));
                    const resolvedH = Math.max(4, Math.round((pt.resolved_count / maxCount) * 120));
                    return (
                      <div key={pt.date} className="trend-bar-col" title={`${pt.date}: Created ${pt.created_count}, Resolved ${pt.resolved_count}`}>
                        <div className="bar-pair">
                          <div className="bar created-bar" style={{ height: `${createdH}px` }}>
                            {pt.created_count > 0 && <span className="bar-count">{pt.created_count}</span>}
                          </div>
                          <div className="bar resolved-bar" style={{ height: `${resolvedH}px` }}>
                            {pt.resolved_count > 0 && <span className="bar-count">{pt.resolved_count}</span>}
                          </div>
                        </div>
                        <span className="bar-date-label">{pt.date.slice(5)}</span>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            {/* SLA Performance & Breach Analysis */}
            <div className="chart-card glass-card">
              <div className="chart-card-header">
                <div className="chart-header-title">
                  <CheckCircle2 size={18} color="#34d399" />
                  <h3>SLA State Distribution & Health</h3>
                </div>
                <span className="sla-total-evaluated-tag">
                  {data.sla_metrics.total_evaluated} Evaluated
                </span>
              </div>

              <div className="sla-distribution-body">
                <div className="sla-multi-progress-track">
                  {data.sla_metrics.total_evaluated > 0 ? (
                    <>
                      <div
                        className="multi-bar on-track"
                        style={{
                          width: `${((data.sla_metrics.on_track_count + data.sla_metrics.resolved_met_count) / data.sla_metrics.total_evaluated) * 100}%`,
                        }}
                        title={`Compliant: ${data.sla_metrics.on_track_count + data.sla_metrics.resolved_met_count}`}
                      />
                      <div
                        className="multi-bar at-risk"
                        style={{
                          width: `${(data.sla_metrics.at_risk_count / data.sla_metrics.total_evaluated) * 100}%`,
                        }}
                        title={`At Risk: ${data.sla_metrics.at_risk_count}`}
                      />
                      <div
                        className="multi-bar paused"
                        style={{
                          width: `${(data.sla_metrics.paused_count / data.sla_metrics.total_evaluated) * 100}%`,
                        }}
                        title={`Paused: ${data.sla_metrics.paused_count}`}
                      />
                      <div
                        className="multi-bar breached"
                        style={{
                          width: `${((data.sla_metrics.breached_count + data.sla_metrics.resolved_breached_count) / data.sla_metrics.total_evaluated) * 100}%`,
                        }}
                        title={`Breached: ${data.sla_metrics.breached_count + data.sla_metrics.resolved_breached_count}`}
                      />
                    </>
                  ) : (
                    <div className="multi-bar empty" style={{ width: '100%' }} />
                  )}
                </div>

                <div className="sla-breakdown-list">
                  <div className="sla-breakdown-item">
                    <span className="sla-dot on-track" />
                    <span className="item-label">On Track & Met</span>
                    <span className="item-value">{data.sla_metrics.on_track_count + data.sla_metrics.resolved_met_count}</span>
                  </div>

                  <div className="sla-breakdown-item">
                    <span className="sla-dot at-risk" />
                    <span className="item-label">At Risk (Warning)</span>
                    <span className="item-value">{data.sla_metrics.at_risk_count}</span>
                  </div>

                  <div className="sla-breakdown-item">
                    <span className="sla-dot paused" />
                    <span className="item-label">Paused (Customer)</span>
                    <span className="item-value">{data.sla_metrics.paused_count}</span>
                  </div>

                  <div className="sla-breakdown-item">
                    <span className="sla-dot breached" />
                    <span className="item-label">Breached</span>
                    <span className="item-value">{data.sla_metrics.breached_count + data.sla_metrics.resolved_breached_count}</span>
                  </div>
                </div>
              </div>
            </div>
          </section>

          {/* Secondary Distributions Grid */}
          <section className="analytics-breakdown-grid">
            {/* Priority Distribution */}
            <div className="breakdown-card glass-card">
              <div className="breakdown-card-header">
                <Flag size={17} color="#f87171" />
                <h3>Ticket Priority Distribution</h3>
              </div>
              <div className="priority-items-list">
                {data.priority_distribution.map((prio) => (
                  <div key={prio.priority} className="priority-row-item">
                    <div className="prio-label-row">
                      <span className={`prio-tag ${prio.priority}`}>{prio.priority.toUpperCase()}</span>
                      <span className="prio-stats">
                        {prio.ticket_count} tickets ({prio.percentage}%)
                        {prio.breached_count > 0 && (
                          <span className="prio-breach-warn"> • {prio.breached_count} breached</span>
                        )}
                      </span>
                    </div>
                    <div className="distribution-progress-track">
                      <div
                        className={`distribution-progress-fill prio-${prio.priority}`}
                        style={{ width: `${Math.min(100, prio.percentage)}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Category Distribution */}
            <div className="breakdown-card glass-card">
              <div className="breakdown-card-header">
                <Layers size={17} color="#38bdf8" />
                <h3>Category Distribution & SLA</h3>
              </div>
              <div className="category-items-list">
                {data.category_distribution.length === 0 ? (
                  <p className="empty-subtext">No category data available.</p>
                ) : (
                  data.category_distribution.map((cat) => (
                    <div key={cat.category_name} className="category-row-item">
                      <div className="cat-label-row">
                        <span className="cat-name">{cat.category_name}</span>
                        <span className="cat-stats">
                          {cat.ticket_count} tickets ({cat.percentage}%) •{' '}
                          <strong style={{ color: cat.sla_compliance_pct >= 80 ? '#34d399' : '#fbbf24' }}>
                            {cat.sla_compliance_pct}% SLA
                          </strong>
                        </span>
                      </div>
                      <div className="distribution-progress-track">
                        <div
                          className="distribution-progress-fill cat-fill"
                          style={{ width: `${Math.min(100, cat.percentage)}%` }}
                        />
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </section>

          {/* Agent & Team Workload Leaderboard */}
          <section className="analytics-team-section glass-card">
            <div className="section-header">
              <div className="section-title-group">
                <div className="header-with-icon">
                  <Users size={18} color="#60a5fa" />
                  <h2 className="section-title">Support Team & Agent Workload</h2>
                </div>
                <span className="section-subtitle">
                  Active ticket allocation, resolved volumes, and individual SLA compliance rates
                </span>
              </div>
            </div>

            {data.agent_workload.length === 0 ? (
              <div className="empty-state-box">
                <p>No active agent workload data found.</p>
              </div>
            ) : (
              <div className="table-responsive">
                <table className="tickets-table">
                  <thead>
                    <tr>
                      <th>Agent Name</th>
                      <th>Department</th>
                      <th>Active Assigned</th>
                      <th>Resolved (Period)</th>
                      <th>Avg Resolution</th>
                      <th>SLA Compliance</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.agent_workload.map((agent) => (
                      <tr key={agent.agent_id} className="ticket-table-row">
                        <td className="agent-profile-cell">
                          <div className="agent-table-avatar">
                            {agent.agent_name.slice(0, 2).toUpperCase()}
                          </div>
                          <div>
                            <div className="agent-name-bold">{agent.agent_name}</div>
                            <div className="agent-email-sub">{agent.agent_email}</div>
                          </div>
                        </td>
                        <td>
                          <span className="category-pill">{agent.department}</span>
                        </td>
                        <td>
                          <span className="active-assigned-badge">{agent.active_tickets_count} Active</span>
                        </td>
                        <td>
                          <span className="resolved-count-val">{agent.resolved_tickets_count}</span>
                        </td>
                        <td>
                          <span className="duration-val">{formatHours(agent.avg_resolution_hours)}</span>
                        </td>
                        <td>
                          <span
                            className={`badge ${
                              agent.sla_compliance_pct >= 85
                                ? 'badge-resolved'
                                : agent.sla_compliance_pct >= 70
                                ? 'badge-in_progress'
                                : 'badge-critical'
                            }`}
                          >
                            {agent.sla_compliance_pct}%
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>

          {/* AI Intelligence & Knowledge Base Operations Grid */}
          <section className="analytics-ai-section glass-card">
            <div className="section-header">
              <div className="section-title-group">
                <div className="header-with-icon">
                  <Sparkles size={18} color="#a78bfa" />
                  <h2 className="section-title">AI Automation & Grounding Operations</h2>
                </div>
                <span className="section-subtitle">
                  Adoption rates, human review decisions, and knowledge base utilization
                </span>
              </div>
            </div>

            <div className="ai-metrics-grid">
              <div className="ai-metric-box">
                <span className="ai-box-label">AI Triage Recommendations</span>
                <span className="ai-box-value">{data.ai_adoption.total_triage_generated}</span>
                <div className="ai-sub-stats">
                  <span className="stat-pill green">
                    <CheckCircle size={12} /> {data.ai_adoption.triage_accepted} Accepted
                  </span>
                  <span className="stat-pill red">
                    <XCircle size={12} /> {data.ai_adoption.triage_rejected} Rejected
                  </span>
                </div>
              </div>

              <div className="ai-metric-box">
                <span className="ai-box-label">SLA Risk Assessments</span>
                <span className="ai-box-value">{data.ai_adoption.total_sla_risk_evaluations}</span>
                <div className="ai-sub-stats">
                  <span className="stat-pill green">
                    <CheckCircle size={12} /> {data.escalation_metrics.accepted_count} Escalated
                  </span>
                  <span className="stat-pill slate">
                    <XCircle size={12} /> {data.escalation_metrics.rejected_count} Declined
                  </span>
                </div>
              </div>

              <div className="ai-metric-box">
                <span className="ai-box-label">Knowledge Base Articles</span>
                <span className="ai-box-value">{data.ai_adoption.total_kb_articles}</span>
                <div className="ai-sub-stats">
                  <span className="stat-pill blue">
                    <BookOpen size={12} /> {data.ai_adoption.total_kb_views} Total Views
                  </span>
                  <span className="stat-pill emerald">
                    <CheckCircle2 size={12} /> {data.ai_adoption.total_kb_helpful_votes} Helpful Votes
                  </span>
                </div>
              </div>
            </div>
          </section>
        </>
      )}
    </div>
  );
};
