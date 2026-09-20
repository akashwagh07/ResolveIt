import React, { useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  CheckCircle2,
  AlertTriangle,
  HelpCircle,
  ArrowRight,
  PlusCircle,
  ListFilter,
  Shield,
  Clock,
  Layers,
  Sparkles,
  Info,
} from 'lucide-react';
import StatusBadge from './StatusBadge';
import SeverityBadge from './SeverityBadge';
import PriorityBadge from './PriorityBadge';
import { useAuth } from '../lib/auth';

export default function ResultPanel({ result, citizenName, citizenContact, onReset }) {
  const { setSession } = useAuth();

  // Save the citizen identity in the demo session so /citizen dashboard immediately lists the new report
  useEffect(() => {
    if (citizenContact) {
      setSession('CITIZEN', citizenName, citizenContact);
    }
  }, [citizenName, citizenContact, setSession]);

  const {
    complaint_id,
    status,
    needs_review,
    category,
    issue,
    confidence,
    summary,
    severity,
    priority,
    department,
    trace,
  } = result;

  const confidencePct = Math.round((confidence || 0) * 100);

  // Status banner rendering
  let bannerBg = 'bg-emerald-50 border-emerald-200 text-emerald-900';
  let bannerIcon = <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0 mt-0.5" />;
  let bannerTitle = 'Report received and routed';
  let bannerSubtitle = 'Your complaint was processed by the AI intake agent and routed to municipal authorities.';

  if (status === 'HUMAN_REVIEW') {
    bannerBg = 'bg-amber-50 border-amber-200 text-amber-900';
    bannerIcon = <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />;
    bannerTitle = 'Received, a person will review it';
    bannerSubtitle =
      trace?.find((t) => t.toLowerCase().includes('review') || t.toLowerCase().includes('confidence')) ||
      'This issue requires human triage before direct dispatch.';
  } else if (status === 'OUT_OF_SCOPE') {
    bannerBg = 'bg-slate-100 border-slate-200 text-slate-800';
    bannerIcon = <HelpCircle className="w-5 h-5 text-slate-600 shrink-0 mt-0.5" />;
    bannerTitle = "This doesn't look like a civic issue";
    bannerSubtitle =
      trace?.find((t) => t.toLowerCase().includes('civic') || t.toLowerCase().includes('relevance')) ||
      'The submitted issue does not match known municipal public works categories.';
  }

  return (
    <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 sm:p-8 space-y-6">
      {/* Banner */}
      <div className={`p-4 rounded-xl border flex items-start gap-3 ${bannerBg}`}>
        {bannerIcon}
        <div>
          <h2 className="text-base font-bold">{bannerTitle}</h2>
          <p className="text-xs mt-0.5 opacity-90">{bannerSubtitle}</p>
        </div>
      </div>

      {/* Header Info */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-5 border-b border-slate-100">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="font-mono text-xs font-bold text-slate-400">#{complaint_id}</span>
            <StatusBadge status={status} size="sm" />
            {needs_review && (
              <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-amber-800 bg-amber-100 px-2 py-0.5 rounded-full border border-amber-200">
                <AlertTriangle className="w-3 h-3" />
                Needs Review
              </span>
            )}
          </div>
          <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight capitalize">
            {(issue || '').replace(/_/g, ' ')}
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Category: <span className="font-semibold text-slate-700 capitalize">{(category || '').replace(/_/g, ' ')}</span>
          </p>
        </div>

        {/* Assigned department pill */}
        <div className="sm:text-right">
          <span className="text-[11px] text-slate-400 block mb-0.5">Assigned Department</span>
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg bg-brand-50 border border-brand-200 text-brand-800 text-xs font-semibold">
            <Shield className="w-3.5 h-3.5 text-brand-600" />
            {department?.name || department?.code || 'Triage'}
          </span>
        </div>
      </div>

      {/* Summary */}
      {summary && (
        <div className="p-4 rounded-xl bg-slate-50 border border-slate-100 text-xs text-slate-700 space-y-1">
          <span className="font-semibold text-slate-900 block text-[11px] uppercase tracking-wider">
            Report Summary
          </span>
          <p>{summary}</p>
        </div>
      )}

      {/* AI Confidence Bar */}
      <div className="space-y-1.5">
        <div className="flex items-center justify-between text-xs font-semibold">
          <span className="text-slate-700 flex items-center gap-1.5">
            <Sparkles className="w-3.5 h-3.5 text-brand-600" />
            AI Classification Confidence
          </span>
          <span className="font-mono text-slate-900">{confidencePct}%</span>
        </div>
        <div className="w-full h-2.5 rounded-full bg-slate-100 overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-700 ${
              confidencePct >= 85
                ? 'bg-emerald-500'
                : confidencePct >= 60
                ? 'bg-amber-500'
                : 'bg-rose-500'
            }`}
            style={{ width: `${Math.max(5, confidencePct)}%` }}
          />
        </div>
        {needs_review && (
          <p className="text-[11px] text-amber-700 flex items-center gap-1 mt-1">
            <Info className="w-3.5 h-3.5" />
            Flagged for municipal supervisor review due to confidence threshold or category policy.
          </p>
        )}
      </div>

      {/* Metrics Row: Severity & Priority */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Severity */}
        <div className="p-4 rounded-xl border border-slate-200 bg-white space-y-3 shadow-2xs">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-1.5">
              <Layers className="w-4 h-4 text-brand-600" />
              <h3 className="text-xs font-bold text-slate-900">Deterministic Severity</h3>
            </div>
            <SeverityBadge level={severity?.level} score={severity?.score} size="sm" />
          </div>

          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-slate-900 font-mono">
              {severity?.score ?? 0}
            </span>
            <span className="text-xs font-semibold text-slate-400">/ 10 points</span>
          </div>

          {/* Severity factor breakdown */}
          <div className="space-y-1.5 pt-1">
            <span className="text-[10px] uppercase tracking-wider font-semibold text-slate-400 block">
              Contributing Factors
            </span>
            {Array.isArray(severity?.factors) && severity.factors.length > 0 ? (
              severity.factors.map((f, i) => (
                <div
                  key={i}
                  className="flex items-center justify-between text-xs p-2 rounded-lg bg-slate-50 border border-slate-100"
                >
                  <span className="text-slate-600 capitalize">{f.factor || f.reason}</span>
                  <span className="font-mono font-semibold text-slate-800">
                    +{f.points ?? 0} pts
                  </span>
                </div>
              ))
            ) : (
              <p className="text-xs text-slate-400 italic">No extra severity factors applied.</p>
            )}
          </div>
        </div>

        {/* Priority & SLA */}
        <div className="p-4 rounded-xl border border-slate-200 bg-white space-y-3 shadow-2xs">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-1.5">
              <Clock className="w-4 h-4 text-brand-600" />
              <h3 className="text-xs font-bold text-slate-900">Dispatch Priority</h3>
            </div>
            <PriorityBadge priority={priority?.value} size="sm" />
          </div>

          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-extrabold text-slate-900 capitalize">
              {priority?.value || 'Normal'}
            </span>
          </div>

          {/* Priority factor breakdown */}
          <div className="space-y-1.5 pt-1">
            <span className="text-[10px] uppercase tracking-wider font-semibold text-slate-400 block">
              Active Modifiers
            </span>
            {typeof priority?.factors === 'object' && priority?.factors && Object.keys(priority.factors).length > 0 ? (
              Object.entries(priority.factors).map(([key, val]) => (
                <div
                  key={key}
                  className="flex items-center justify-between text-xs p-2 rounded-lg bg-slate-50 border border-slate-100"
                >
                  <span className="text-slate-600 capitalize">{key.replace(/_/g, ' ')}</span>
                  <span className="font-mono font-semibold text-brand-700">
                    {typeof val === 'boolean' ? (val ? 'Active' : 'No') : String(val)}
                  </span>
                </div>
              ))
            ) : (
              <p className="text-xs text-slate-400 italic">Standard municipal priority rules applied.</p>
            )}
          </div>
        </div>
      </div>

      {/* Decision Trace: How we decided */}
      <div className="p-4 rounded-xl border border-slate-200 bg-slate-50/70 space-y-2.5">
        <h3 className="text-xs font-bold text-slate-900 flex items-center gap-2">
          <Sparkles className="w-3.5 h-3.5 text-brand-600" />
          How we decided
        </h3>
        {Array.isArray(trace) && trace.length > 0 ? (
          <ul className="space-y-1.5 text-xs text-slate-700 list-disc list-inside">
            {trace.map((step, idx) => (
              <li key={idx} className="leading-relaxed">
                {step}
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-xs text-slate-400 italic">No decision steps recorded.</p>
        )}
      </div>

      {/* Action Buttons */}
      <div className="pt-4 border-t border-slate-100 flex flex-col sm:flex-row items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2 w-full sm:w-auto">
          <button
            type="button"
            onClick={onReset}
            className="flex-1 sm:flex-initial inline-flex items-center justify-center gap-1.5 px-4 py-2.5 rounded-xl border border-slate-300 hover:bg-slate-50 text-slate-700 text-xs font-semibold transition-colors cursor-pointer"
          >
            <PlusCircle className="w-4 h-4" />
            Report another issue
          </button>
          <Link
            to="/citizen"
            className="flex-1 sm:flex-initial inline-flex items-center justify-center gap-1.5 px-4 py-2.5 rounded-xl border border-slate-300 hover:bg-slate-50 text-slate-700 text-xs font-semibold transition-colors"
          >
            <ListFilter className="w-4 h-4" />
            My complaints
          </Link>
        </div>

        <Link
          to={`/citizen/complaints/${complaint_id}`}
          className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl bg-brand-600 hover:bg-brand-700 text-white text-xs font-semibold shadow-xs transition-colors"
        >
          Track this complaint
          <ArrowRight className="w-4 h-4" />
        </Link>
      </div>
    </div>
  );
}
