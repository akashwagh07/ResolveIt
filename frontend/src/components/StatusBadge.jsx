import React from 'react';

const STATUS_CONFIG = {
  SUBMITTED: { label: 'Submitted', bg: 'bg-slate-100', text: 'text-slate-700', border: 'border-slate-200' },
  AI_ANALYZING: { label: 'AI Analyzing', bg: 'bg-cyan-50', text: 'text-cyan-700', border: 'border-cyan-200' },
  CLASSIFIED: { label: 'Classified', bg: 'bg-blue-50', text: 'text-blue-700', border: 'border-blue-200' },
  UNDER_REVIEW: { label: 'Under Review', bg: 'bg-indigo-50', text: 'text-indigo-700', border: 'border-indigo-200' },
  ASSIGNED: { label: 'Assigned', bg: 'bg-sky-50', text: 'text-sky-700', border: 'border-sky-200' },
  IN_PROGRESS: { label: 'In Progress', bg: 'bg-blue-50', text: 'text-blue-700', border: 'border-blue-300' },
  RESOLUTION_SUBMITTED: { label: 'Resolution Submitted', bg: 'bg-violet-50', text: 'text-violet-700', border: 'border-violet-200' },
  AI_VERIFICATION: { label: 'AI Verification', bg: 'bg-purple-50', text: 'text-purple-700', border: 'border-purple-200' },
  ADMIN_VERIFICATION: { label: 'Admin Verification', bg: 'bg-purple-100', text: 'text-purple-800', border: 'border-purple-300' },
  CITIZEN_CONFIRMATION: { label: 'Citizen Confirmation', bg: 'bg-amber-50', text: 'text-amber-800', border: 'border-amber-300' },
  RESOLVED: { label: 'Resolved', bg: 'bg-emerald-50', text: 'text-emerald-700', border: 'border-emerald-200' },
  HUMAN_REVIEW: { label: 'Human Review', bg: 'bg-amber-100', text: 'text-amber-900', border: 'border-amber-300' },
  OUT_OF_SCOPE: { label: 'Out of Scope', bg: 'bg-zinc-100', text: 'text-zinc-700', border: 'border-zinc-300' },
  MERGED: { label: 'Merged', bg: 'bg-stone-100', text: 'text-stone-700', border: 'border-stone-300' },
  ESCALATED: { label: 'Escalated', bg: 'bg-rose-100', text: 'text-rose-800', border: 'border-rose-300' },
  REOPENED: { label: 'Reopened', bg: 'bg-orange-100', text: 'text-orange-800', border: 'border-orange-300' },
  ERROR: { label: 'Error', bg: 'bg-red-100', text: 'text-red-800', border: 'border-red-300' },
};

export default function StatusBadge({ status, size = 'md' }) {
  const conf = STATUS_CONFIG[status] || {
    label: status || 'Unknown',
    bg: 'bg-gray-100',
    text: 'text-gray-700',
    border: 'border-gray-200',
  };

  const sizeClasses = size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-2.5 py-1 text-xs font-medium';

  return (
    <span
      className={`inline-flex items-center rounded-full border ${conf.bg} ${conf.text} ${conf.border} ${sizeClasses}`}
    >
      <span className="w-1.5 h-1.5 rounded-full mr-1.5 bg-current opacity-75"></span>
      {conf.label}
    </span>
  );
}
