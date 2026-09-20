import React, { useEffect, useState, useMemo } from 'react';
import { Link } from 'react-router-dom';
import {
  Briefcase,
  Play,
  Clock,
  AlertTriangle,
  RefreshCw,
  MapPin,
  Calendar,
  ArrowRight,
  Shield,
  Loader2,
  CheckCircle2,
} from 'lucide-react';
import { useAuth } from '../lib/auth';
import { getComplaints, runAction } from '../lib/api';
import StatusBadge from '../components/StatusBadge';
import PriorityBadge from '../components/PriorityBadge';
import SeverityBadge from '../components/SeverityBadge';
import LoadingState from '../components/LoadingState';
import ErrorState from '../components/ErrorState';
import EmptyState from '../components/EmptyState';

const PRIORITY_ORDER = { EMERGENCY: 4, HIGH: 3, STANDARD: 2, NORMAL: 1 };
const OFFICER_STATUSES = new Set(['ASSIGNED', 'IN_PROGRESS', 'REOPENED']);

export default function OfficerDashboard() {
  const { session } = useAuth();
  const [complaints, setComplaints] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [startingWorkId, setStartingWorkId] = useState(null);
  const [actionNotice, setActionNotice] = useState('');

  const fetchOfficerWork = async () => {
    setLoading(true);
    setError(null);
    try {
      const officerId = session?.userId;
      const filters = officerId ? { assigned_officer_id: String(officerId), limit: 100 } : { limit: 100 };
      const data = await getComplaints(filters);

      if (!Array.isArray(data)) {
        throw new Error('Invalid data format received from server.');
      }

      // Filter to complaints assigned to this officer and in active states: ASSIGNED, IN_PROGRESS, REOPENED
      const myWork = data.filter((c) => {
        const matchesOfficer = officerId ? Number(c.assigned_officer_id) === Number(officerId) : true;
        return matchesOfficer && OFFICER_STATUSES.has(c.status);
      });

      setComplaints(myWork);
    } catch (err) {
      setError(err.message || 'Failed to load officer work queue.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchOfficerWork();
  }, [session?.userId]);

  // Sort by priority then SLA deadline (earliest deadline first)
  const sortedComplaints = useMemo(() => {
    return [...complaints].sort((a, b) => {
      const pDiff = (PRIORITY_ORDER[b.priority] || 0) - (PRIORITY_ORDER[a.priority] || 0);
      if (pDiff !== 0) return pDiff;

      const aTime = a.sla_deadline ? new Date(a.sla_deadline).getTime() : Infinity;
      const bTime = b.sla_deadline ? new Date(b.sla_deadline).getTime() : Infinity;
      return aTime - bTime;
    });
  }, [complaints]);

  const handleStartWork = async (complaintId) => {
    setStartingWorkId(complaintId);
    setActionNotice('');
    try {
      await runAction(complaintId, 'start_work');
      setActionNotice(`Started work on complaint #${complaintId}. Status is now IN PROGRESS.`);
      await fetchOfficerWork();
    } catch (err) {
      setError(`Failed to start work: ${err.message}`);
    } finally {
      setStartingWorkId(null);
    }
  };

  const now = new Date();

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
              <Briefcase className="w-6 h-6 text-brand-600" />
              Field Officer Work Queue
            </h1>
            <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-brand-50 text-brand-700 border border-brand-200">
              {complaints.length} active tasks
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Complaints assigned to <span className="font-semibold text-slate-700">{session?.name || 'Officer'}</span> in{' '}
            <span className="font-semibold text-slate-700">{session?.departmentName || 'your department'}</span>.
          </p>
        </div>

        <button
          type="button"
          onClick={fetchOfficerWork}
          className="inline-flex items-center gap-2 px-3.5 py-2 text-xs font-semibold text-slate-700 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 shadow-2xs transition-colors self-start sm:self-auto cursor-pointer"
        >
          <RefreshCw className={`w-3.5 h-3.5 text-slate-500 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {actionNotice && (
        <div className="p-3.5 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
            <span>{actionNotice}</span>
          </div>
          <button
            type="button"
            onClick={() => setActionNotice('')}
            className="text-emerald-700 hover:text-emerald-900 font-bold ml-2 cursor-pointer"
          >
            &times;
          </button>
        </div>
      )}

      {loading ? (
        <LoadingState message="Loading your assigned complaints and SLA deadlines..." />
      ) : error ? (
        <ErrorState message={error} onRetry={fetchOfficerWork} />
      ) : sortedComplaints.length === 0 ? (
        <EmptyState
          title="Work queue is clear"
          description="You have no active complaints in ASSIGNED, IN PROGRESS, or REOPENED status."
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {sortedComplaints.map((c) => {
            const isOverdue = c.sla_deadline && new Date(c.sla_deadline) < now;
            const slaFormatted = c.sla_deadline
              ? new Date(c.sla_deadline).toLocaleString('en-IN', {
                  dateStyle: 'medium',
                  timeStyle: 'short',
                })
              : null;

            return (
              <div
                key={c.id}
                className="bg-white rounded-2xl border border-slate-200 p-5 shadow-xs hover:shadow-md transition-all flex flex-col justify-between gap-4"
              >
                <div className="space-y-3">
                  {/* Status & Badges Row */}
                  <div className="flex items-center justify-between gap-2">
                    <StatusBadge status={c.status} size="sm" />
                    <div className="flex items-center gap-1.5">
                      <PriorityBadge priority={c.priority} size="sm" />
                      <SeverityBadge level={c.severity_level} score={c.severity_score} size="sm" />
                    </div>
                  </div>

                  {/* Overdue SLA Alert Badge */}
                  {isOverdue && (
                    <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-rose-50 border border-rose-200 text-rose-800 text-[11px] font-bold animate-pulse">
                      <AlertTriangle className="w-3.5 h-3.5 text-rose-600 shrink-0" />
                      <span>SLA BREACHED (Overdue)</span>
                    </div>
                  )}

                  {/* Issue Title & Address */}
                  <div>
                    <span className="font-mono text-[10px] text-slate-400 block mb-0.5">#{c.id}</span>
                    <Link
                      to={`/officer/complaints/${c.id}`}
                      className="font-bold text-slate-900 hover:text-brand-600 transition-colors text-sm block"
                    >
                      {c.issue.replace(/_/g, ' ')}
                    </Link>
                    <p className="text-xs text-slate-500 mt-1 flex items-center gap-1">
                      <MapPin className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                      <span className="truncate">{c.address_text}</span>
                    </p>
                  </div>

                  {/* SLA Deadline info */}
                  {slaFormatted && (
                    <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-100 text-xs">
                      <div className="flex items-center justify-between text-[11px] text-slate-500 mb-0.5">
                        <span className="flex items-center gap-1">
                          <Clock className="w-3 h-3" />
                          SLA Deadline:
                        </span>
                        <span className={`font-mono font-bold ${isOverdue ? 'text-rose-600' : 'text-slate-700'}`}>
                          {slaFormatted}
                        </span>
                      </div>
                    </div>
                  )}
                </div>

                {/* Card Actions */}
                <div className="pt-3 border-t border-slate-100 flex items-center justify-between gap-2">
                  {c.status === 'ASSIGNED' ? (
                    <button
                      type="button"
                      onClick={() => handleStartWork(c.id)}
                      disabled={startingWorkId === c.id}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-brand-600 hover:bg-brand-700 text-white text-xs font-semibold shadow-2xs transition-colors cursor-pointer disabled:bg-slate-300"
                    >
                      {startingWorkId === c.id ? (
                        <>
                          <Loader2 className="w-3.5 h-3.5 animate-spin" />
                          Starting...
                        </>
                      ) : (
                        <>
                          <Play className="w-3.5 h-3.5" />
                          Start Work
                        </>
                      )}
                    </button>
                  ) : (
                    <span className="text-[11px] font-semibold text-slate-500">
                      {c.status === 'IN_PROGRESS' ? 'Work in progress' : 'Awaiting action'}
                    </span>
                  )}

                  <Link
                    to={`/officer/complaints/${c.id}`}
                    className="inline-flex items-center gap-1 text-xs font-semibold text-brand-600 hover:text-brand-700 transition-colors ml-auto"
                  >
                    View Dossier
                    <ArrowRight className="w-3.5 h-3.5" />
                  </Link>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
