import React, { useEffect, useState, useMemo } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import {
  Inbox,
  Clock,
  AlertTriangle,
  CheckCircle2,
  Filter,
  ArrowUpDown,
  RefreshCw,
  MapPin,
  ExternalLink,
  ShieldCheck,
  User,
} from 'lucide-react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Cell,
} from 'recharts';
import { getComplaints, getDepartments, getUsers } from '../lib/api';
import StatusBadge from '../components/StatusBadge';
import SeverityBadge from '../components/SeverityBadge';
import PriorityBadge from '../components/PriorityBadge';
import StatCard from '../components/StatCard';
import LoadingState from '../components/LoadingState';
import ErrorState from '../components/ErrorState';

const PRIORITY_ORDER = { EMERGENCY: 4, HIGH: 3, STANDARD: 2, NORMAL: 1 };
const WAITING_ON_ADMIN_STATUSES = new Set(['CLASSIFIED', 'UNDER_REVIEW', 'HUMAN_REVIEW', 'ADMIN_VERIFICATION']);

const STATUS_COLORS = {
  SUBMITTED: '#64748b',
  AI_ANALYZING: '#06b6d4',
  CLASSIFIED: '#3b82f6',
  UNDER_REVIEW: '#6366f1',
  ASSIGNED: '#0284c7',
  IN_PROGRESS: '#2563eb',
  RESOLUTION_SUBMITTED: '#8b5cf6',
  AI_VERIFICATION: '#a855f7',
  ADMIN_VERIFICATION: '#9333ea',
  CITIZEN_CONFIRMATION: '#d97706',
  RESOLVED: '#10b981',
  HUMAN_REVIEW: '#f59e0b',
  ESCALATED: '#f43f5e',
  REOPENED: '#ea580c',
};

export default function AdminDashboard() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [complaints, setComplaints] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [officers, setOfficers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Filters
  const initialQuickFilter = searchParams.get('filter') === 'needs_review' ? 'needs_review' : '';
  const [quickFilter, setQuickFilter] = useState(initialQuickFilter);
  const [statusFilter, setStatusFilter] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [deptFilter, setDeptFilter] = useState('');

  // Sync with URL params
  useEffect(() => {
    if (searchParams.get('filter') === 'needs_review') {
      setQuickFilter('needs_review');
    }
  }, [searchParams]);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [compList, deptList, officerList] = await Promise.all([
        getComplaints({ limit: 150 }),
        getDepartments().catch(() => []),
        getUsers('OFFICER').catch(() => []),
      ]);
      if (!Array.isArray(compList)) {
        throw new Error('Invalid data received from server for complaints.');
      }
      setComplaints(compList);
      setDepartments(Array.isArray(deptList) ? deptList : []);
      setOfficers(Array.isArray(officerList) ? officerList : []);
    } catch (err) {
      setError(err.message || 'Failed to fetch municipal complaints from server');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  // Compute stat card metrics
  const stats = useMemo(() => {
    const total = complaints.length;
    const needsReview = complaints.filter(
      (c) => c.needs_review || c.status === 'HUMAN_REVIEW'
    ).length;
    const waitingOnAdmin = complaints.filter(
      (c) => WAITING_ON_ADMIN_STATUSES.has(c.status)
    ).length;
    const escalated = complaints.filter((c) => c.status === 'ESCALATED').length;
    const resolved = complaints.filter((c) => c.status === 'RESOLVED').length;
    return { total, needsReview, waitingOnAdmin, escalated, resolved };
  }, [complaints]);

  // Status distribution chart data
  const chartData = useMemo(() => {
    const counts = {};
    complaints.forEach((c) => {
      counts[c.status] = (counts[c.status] || 0) + 1;
    });
    return Object.entries(counts).map(([status, count]) => ({
      status: status.replace(/_/g, ' '),
      rawStatus: status,
      count,
    }));
  }, [complaints]);

  // Filter and sort complaints: by Priority then Age (older first)
  const filteredComplaints = useMemo(() => {
    let result = [...complaints];

    if (quickFilter === 'needs_review') {
      result = result.filter((c) => c.needs_review || c.status === 'HUMAN_REVIEW');
    } else if (quickFilter === 'waiting_on_admin') {
      result = result.filter((c) => WAITING_ON_ADMIN_STATUSES.has(c.status));
    }

    if (statusFilter) {
      result = result.filter((c) => c.status === statusFilter);
    }
    if (categoryFilter) {
      result = result.filter((c) => c.category === categoryFilter);
    }
    if (deptFilter) {
      result = result.filter((c) => String(c.department_id) === String(deptFilter));
    }

    return result.sort((a, b) => {
      const pDiff = (PRIORITY_ORDER[b.priority] || 0) - (PRIORITY_ORDER[a.priority] || 0);
      if (pDiff !== 0) return pDiff;
      // Older complaints have earlier created_at timestamps (higher age)
      return new Date(a.created_at) - new Date(b.created_at);
    });
  }, [complaints, quickFilter, statusFilter, categoryFilter, deptFilter]);

  // Unique categories for filter dropdown
  const uniqueCategories = useMemo(() => {
    return Array.from(new Set(complaints.map((c) => c.category))).sort();
  }, [complaints]);

  // Unique statuses for filter dropdown
  const uniqueStatuses = useMemo(() => {
    return Array.from(new Set(complaints.map((c) => c.status))).sort();
  }, [complaints]);

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-12">
        <LoadingState message="Fetching municipal complaints, SLA stats and department work queues..." />
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-12">
        <ErrorState message={error} onRetry={loadData} />
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Municipal Command Center</h1>
            <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-slate-100 text-slate-700 border border-slate-200">
              {complaints.length} complaints on server
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Real-time closed-loop civic issue intake, department routing and deterministic SLA status.
          </p>
        </div>

        <button
          type="button"
          onClick={loadData}
          className="inline-flex items-center gap-2 px-3.5 py-2 text-xs font-semibold text-slate-700 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 shadow-2xs transition-colors self-start sm:self-auto"
        >
          <RefreshCw className="w-3.5 h-3.5 text-slate-500" />
          Refresh
        </button>
      </div>

      {/* Stat Cards Row */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
        <StatCard
          title="Total Complaints"
          value={stats.total}
          subtitle={`${complaints.length} on server`}
          icon={Inbox}
          color="blue"
        />
        <StatCard
          title="Needs Review"
          value={stats.needsReview}
          subtitle="Low conf / AI review"
          icon={AlertTriangle}
          color="amber"
        />
        <StatCard
          title="Waiting on Admin"
          value={stats.waitingOnAdmin}
          subtitle="Triage & verify"
          icon={Clock}
          color="purple"
        />
        <StatCard
          title="Escalated"
          value={stats.escalated}
          subtitle="SLA breached"
          icon={AlertTriangle}
          color="rose"
        />
        <StatCard
          title="Resolved"
          value={stats.resolved}
          subtitle="Verified & closed"
          icon={CheckCircle2}
          color="emerald"
        />
      </div>

      {/* Status Distribution Chart */}
      <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs">
        <h3 className="text-sm font-bold text-slate-900 mb-4">Complaint Lifecycle Distribution</h3>
        <div className="h-64 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 20 }}>
              <XAxis
                dataKey="status"
                tick={{ fontSize: 10, fill: '#64748b' }}
                interval={0}
                angle={-25}
                textAnchor="end"
              />
              <YAxis tick={{ fontSize: 11, fill: '#64748b' }} allowDecimals={false} />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#0f172a',
                  border: 'none',
                  borderRadius: '8px',
                  color: '#f8fafc',
                  fontSize: '12px',
                }}
              />
              <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                {chartData.map((entry, index) => (
                  <Cell
                    key={`cell-${index}`}
                    fill={STATUS_COLORS[entry.rawStatus] || '#3b82f6'}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Work-queue Table with Filters */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
        {/* Quick Filter Chips and Dropdown Bar */}
        <div className="p-4 border-b border-slate-200 bg-slate-50/50 flex flex-col gap-3">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <Filter className="w-4 h-4 text-slate-500" />
              <span className="text-xs font-bold text-slate-800 uppercase tracking-wider">
                Work Queue ({filteredComplaints.length} of {complaints.length})
              </span>
              <span className="text-[11px] text-slate-400 font-medium ml-1">
                Sorted by Priority, then Age
              </span>
            </div>

            {/* Quick Filter Chips */}
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => {
                  setQuickFilter('');
                  setSearchParams({});
                }}
                className={`px-3 py-1 rounded-full text-xs font-semibold transition-colors cursor-pointer ${
                  !quickFilter
                    ? 'bg-brand-600 text-white shadow-2xs'
                    : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                }`}
              >
                All
              </button>

              <button
                type="button"
                onClick={() => {
                  setQuickFilter('needs_review');
                  setSearchParams({ filter: 'needs_review' });
                }}
                className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold transition-colors cursor-pointer ${
                  quickFilter === 'needs_review'
                    ? 'bg-amber-600 text-white shadow-2xs'
                    : 'bg-amber-50 text-amber-800 hover:bg-amber-100 border border-amber-200'
                }`}
              >
                <AlertTriangle className="w-3.5 h-3.5" />
                Needs Review ({stats.needsReview})
              </button>

              <button
                type="button"
                onClick={() => {
                  setQuickFilter('waiting_on_admin');
                  setSearchParams({});
                }}
                className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold transition-colors cursor-pointer ${
                  quickFilter === 'waiting_on_admin'
                    ? 'bg-purple-600 text-white shadow-2xs'
                    : 'bg-purple-50 text-purple-800 hover:bg-purple-100 border border-purple-200'
                }`}
              >
                <Clock className="w-3.5 h-3.5" />
                Waiting on Admin ({stats.waitingOnAdmin})
              </button>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-slate-200/60">
            {/* Status Filter */}
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="px-2.5 py-1.5 text-xs rounded-lg border border-slate-300 bg-white text-slate-700 focus:outline-none focus:ring-1 focus:ring-brand-500"
            >
              <option value="">All Statuses</option>
              {uniqueStatuses.map((st) => (
                <option key={st} value={st}>
                  {st}
                </option>
              ))}
            </select>

            {/* Category Filter */}
            <select
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
              className="px-2.5 py-1.5 text-xs rounded-lg border border-slate-300 bg-white text-slate-700 focus:outline-none focus:ring-1 focus:ring-brand-500"
            >
              <option value="">All Categories</option>
              {uniqueCategories.map((cat) => (
                <option key={cat} value={cat}>
                  {cat}
                </option>
              ))}
            </select>

            {/* Department Filter */}
            <select
              value={deptFilter}
              onChange={(e) => setDeptFilter(e.target.value)}
              className="px-2.5 py-1.5 text-xs rounded-lg border border-slate-300 bg-white text-slate-700 focus:outline-none focus:ring-1 focus:ring-brand-500"
            >
              <option value="">All Departments</option>
              {departments.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name}
                </option>
              ))}
            </select>

            {(statusFilter || categoryFilter || deptFilter || quickFilter) && (
              <button
                type="button"
                onClick={() => {
                  setQuickFilter('');
                  setStatusFilter('');
                  setCategoryFilter('');
                  setDeptFilter('');
                  setSearchParams({});
                }}
                className="text-xs text-rose-600 hover:text-rose-800 font-medium px-2 py-1 cursor-pointer"
              >
                Clear all filters
              </button>
            )}
          </div>
        </div>

        {/* Table */}
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-600">
            <thead className="bg-slate-50 text-[11px] font-semibold text-slate-500 uppercase tracking-wider border-b border-slate-200">
              <tr>
                <th className="py-3 px-4">Priority & Severity</th>
                <th className="py-3 px-4">Issue / Review Reason</th>
                <th className="py-3 px-4">Category & Department</th>
                <th className="py-3 px-4">Assigned Officer</th>
                <th className="py-3 px-4">Status & SLA State</th>
                <th className="py-3 px-4">Submitted (Age)</th>
                <th className="py-3 px-4 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 font-medium">
              {filteredComplaints.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-12 text-center text-slate-400">
                    No complaints match current filters.
                  </td>
                </tr>
              ) : (
                filteredComplaints.map((c) => {
                  const dept = departments.find((d) => d.id === c.department_id);
                  const officerObj = officers.find((o) => o.id === c.assigned_officer_id);
                  const dateStr = new Date(c.created_at).toLocaleDateString('en-IN', {
                    day: 'numeric',
                    month: 'short',
                  });

                  const isOverdue = c.sla_deadline && new Date(c.sla_deadline) < new Date() && c.status !== 'RESOLVED' && c.status !== 'OUT_OF_SCOPE';
                  const slaStr = c.sla_deadline
                    ? new Date(c.sla_deadline).toLocaleDateString('en-IN', {
                        day: 'numeric',
                        month: 'short',
                        hour: '2-digit',
                        minute: '2-digit',
                      })
                    : null;

                  return (
                    <tr key={c.id} className="hover:bg-slate-50/80 transition-colors">
                      <td className="py-3 px-4 whitespace-nowrap">
                        <div className="flex items-center gap-1.5">
                          <PriorityBadge priority={c.priority} size="sm" />
                          <SeverityBadge level={c.severity_level} score={c.severity_score} size="sm" />
                        </div>
                      </td>

                      <td className="py-3 px-4 max-w-xs">
                        <Link
                          to={`/admin/complaints/${c.id}`}
                          className="font-bold text-slate-900 hover:text-brand-600 transition-colors block truncate"
                        >
                          {c.issue.replace(/_/g, ' ')}
                        </Link>
                        <p className="text-[11px] text-slate-500 truncate mt-0.5">{c.address_text}</p>

                        {/* Review reason row display */}
                        {(c.needs_review || c.review_reason) && (
                          <div className="mt-1 flex items-center gap-1 text-[11px] text-amber-800 bg-amber-50 px-1.5 py-0.5 rounded border border-amber-200 max-w-fit">
                            <AlertTriangle className="w-3 h-3 text-amber-600 shrink-0" />
                            <span className="truncate max-w-[200px]" title={c.review_reason || 'Needs human review'}>
                              {c.review_reason || 'Flagged for review'}
                            </span>
                          </div>
                        )}
                      </td>

                      <td className="py-3 px-4 whitespace-nowrap">
                        <span className="text-xs font-semibold text-slate-700 block">{c.category}</span>
                        <span className="text-[11px] text-slate-400 block">{dept?.name || `Dept #${c.department_id}`}</span>
                      </td>

                      <td className="py-3 px-4 whitespace-nowrap">
                        {officerObj ? (
                          <span className="text-slate-800 font-semibold flex items-center gap-1">
                            <User className="w-3 h-3 text-slate-400" />
                            {officerObj.name}
                          </span>
                        ) : c.assigned_officer_id ? (
                          <span className="text-slate-600 font-mono text-[11px]">Officer #{c.assigned_officer_id}</span>
                        ) : (
                          <span className="text-slate-400 italic text-[11px]">Unassigned</span>
                        )}
                      </td>

                      <td className="py-3 px-4 whitespace-nowrap">
                        <div className="space-y-1">
                          <StatusBadge status={c.status} size="sm" />
                          {slaStr && (
                            <div className="text-[10px] flex items-center gap-1">
                              <Clock className="w-3 h-3 text-slate-400" />
                              <span className={isOverdue ? 'text-rose-600 font-bold' : 'text-slate-500'}>
                                {isOverdue ? `Overdue (${slaStr})` : `Due: ${slaStr}`}
                              </span>
                            </div>
                          )}
                        </div>
                      </td>

                      <td className="py-3 px-4 whitespace-nowrap text-slate-500">
                        {dateStr}
                      </td>

                      <td className="py-3 px-4 text-right whitespace-nowrap">
                        <Link
                          to={`/admin/complaints/${c.id}`}
                          className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-semibold text-brand-700 bg-brand-50 hover:bg-brand-100 rounded-md transition-colors"
                        >
                          Review
                          <ExternalLink className="w-3 h-3" />
                        </Link>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
