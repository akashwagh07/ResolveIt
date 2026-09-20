import React from 'react';
import { Cpu, ShieldCheck, AlertCircle, CheckCircle2, XCircle, Clock, User, Check, Sparkles } from 'lucide-react';

export default function VerificationCard({ resolution }) {
  if (!resolution) return null;

  // Normalize ai_verdict
  let verdict = null;
  if (typeof resolution.ai_verdict === 'string') {
    try {
      verdict = JSON.parse(resolution.ai_verdict);
    } catch {
      verdict = { reasoning: resolution.ai_verdict };
    }
  } else if (typeof resolution.ai_verdict === 'object' && resolution.ai_verdict !== null) {
    verdict = resolution.ai_verdict;
  }

  const confidence =
    resolution.ai_confidence !== null && resolution.ai_confidence !== undefined
      ? `${(resolution.ai_confidence * 100).toFixed(0)}%`
      : verdict?.confidence !== null && verdict?.confidence !== undefined
      ? `${(verdict.confidence * 100).toFixed(0)}%`
      : 'Not assessed';

  const recommendation = verdict?.recommendation || 'Not assessed';
  const reasoning = verdict?.reasoning || verdict?.reason || 'Not assessed';

  // Three-step tracker status
  const isOfficerDone = Boolean(resolution.description);
  const adminDecision = resolution.admin_decision || 'PENDING';
  const citizenDecision = resolution.citizen_decision || 'PENDING';

  return (
    <div className="bg-white rounded-2xl border border-purple-200 p-6 shadow-xs space-y-5">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-purple-100 pb-3">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-purple-100 text-purple-700 flex items-center justify-center font-bold">
            <Cpu className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-slate-900 flex items-center gap-1.5">
              <span>Automated Verification & Decision Audit</span>
              <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded bg-purple-50 text-purple-700 border border-purple-200">
                Agent 3
              </span>
            </h3>
            <p className="text-[11px] text-slate-500">
              Multimodal before/after analysis & multi-party resolution review
            </p>
          </div>
        </div>

        <div className="text-left sm:text-right">
          <span className="text-[11px] text-slate-400 block">Submitted by</span>
          <span className="text-xs font-semibold text-slate-700">
            {resolution.officer_name || 'Field Officer'}
          </span>
        </div>
      </div>

      {/* Mandatory Human Agency Warning */}
      <div className="p-3 rounded-xl bg-purple-50/60 border border-purple-200 flex items-center gap-2.5 text-xs text-purple-900">
        <Sparkles className="w-4 h-4 text-purple-600 shrink-0" />
        <span className="font-semibold">
          Automated checks only assist. A human decides.
        </span>
      </div>

      {/* AI Assessment Metrics */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {/* Recommendation */}
        <div className="p-3 rounded-xl bg-slate-50 border border-slate-200 text-xs">
          <span className="text-slate-400 block font-medium mb-1">AI Recommendation</span>
          <span className="font-bold text-slate-800 text-sm">
            {recommendation}
          </span>
        </div>

        {/* Confidence */}
        <div className="p-3 rounded-xl bg-slate-50 border border-slate-200 text-xs">
          <span className="text-slate-400 block font-medium mb-1">Confidence Score</span>
          <span className="font-bold text-slate-800 text-sm font-mono">
            {confidence}
          </span>
        </div>

        {/* Reasoning */}
        <div className="p-3 rounded-xl bg-slate-50 border border-slate-200 text-xs sm:col-span-1">
          <span className="text-slate-400 block font-medium mb-1">AI Reasoning</span>
          <span className="text-slate-700 font-medium block truncate" title={reasoning}>
            {reasoning}
          </span>
        </div>
      </div>

      {/* Three-step decision tracker */}
      <div className="pt-2 border-t border-slate-100">
        <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider mb-3">
          Multi-Party Resolution Tracker
        </h4>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
          {/* Step 1: Officer Repair Note */}
          <div className="p-3.5 rounded-xl border border-slate-200 bg-slate-50 flex flex-col justify-between gap-2">
            <div>
              <div className="flex items-center justify-between gap-1 mb-1">
                <span className="font-bold text-slate-800 flex items-center gap-1.5">
                  <User className="w-3.5 h-3.5 text-blue-600" />
                  1. Field Officer
                </span>
                <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800">
                  SUBMITTED
                </span>
              </div>
              <p className="text-slate-600 text-[11px] leading-relaxed line-clamp-3">
                "{resolution.description}"
              </p>
            </div>
            <div className="text-[10px] text-slate-400 font-mono">
              {resolution.created_at ? new Date(resolution.created_at).toLocaleDateString('en-IN') : ''}
            </div>
          </div>

          {/* Step 2: Admin Decision */}
          <div className="p-3.5 rounded-xl border border-slate-200 bg-slate-50 flex flex-col justify-between gap-2">
            <div>
              <div className="flex items-center justify-between gap-1 mb-1">
                <span className="font-bold text-slate-800 flex items-center gap-1.5">
                  <ShieldCheck className="w-3.5 h-3.5 text-brand-600" />
                  2. Admin Review
                </span>
                <span
                  className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                    adminDecision === 'APPROVED'
                      ? 'bg-emerald-100 text-emerald-800'
                      : adminDecision === 'REJECTED'
                      ? 'bg-rose-100 text-rose-800'
                      : 'bg-amber-100 text-amber-800'
                  }`}
                >
                  {adminDecision}
                </span>
              </div>
              <p className="text-slate-500 text-[11px]">
                {adminDecision === 'APPROVED'
                  ? 'Resolution verified by municipal supervisor. Dispatched to citizen.'
                  : adminDecision === 'REJECTED'
                  ? 'Resolution rejected by admin; sent back to officer.'
                  : 'Awaiting administrative verification and sign-off.'}
              </p>
            </div>
          </div>

          {/* Step 3: Citizen Confirmation */}
          <div className="p-3.5 rounded-xl border border-slate-200 bg-slate-50 flex flex-col justify-between gap-2">
            <div>
              <div className="flex items-center justify-between gap-1 mb-1">
                <span className="font-bold text-slate-800 flex items-center gap-1.5">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                  3. Citizen Closure
                </span>
                <span
                  className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                    citizenDecision === 'CONFIRMED'
                      ? 'bg-emerald-100 text-emerald-800'
                      : citizenDecision === 'DISPUTED'
                      ? 'bg-rose-100 text-rose-800'
                      : 'bg-amber-100 text-amber-800'
                  }`}
                >
                  {citizenDecision}
                </span>
              </div>
              <p className="text-slate-500 text-[11px]">
                {citizenDecision === 'CONFIRMED'
                  ? 'Citizen confirmed fix. Closed-loop cycle resolved.'
                  : citizenDecision === 'DISPUTED'
                  ? 'Citizen disputed repair. Case reopened for follow-up.'
                  : 'Pending citizen neighborhood confirmation.'}
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
