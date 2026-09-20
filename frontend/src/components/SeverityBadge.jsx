import React from 'react';

const SEVERITY_CONFIG = {
  LOW: { label: 'Low', bg: 'bg-emerald-50', text: 'text-emerald-700', border: 'border-emerald-200' },
  MEDIUM: { label: 'Medium', bg: 'bg-amber-50', text: 'text-amber-700', border: 'border-amber-200' },
  HIGH: { label: 'High', bg: 'bg-orange-50', text: 'text-orange-700', border: 'border-orange-200' },
  CRITICAL: { label: 'Critical', bg: 'bg-rose-50', text: 'text-rose-700', border: 'border-rose-200' },
};

export default function SeverityBadge({ level, score, size = 'md' }) {
  const norm = (level || '').toUpperCase();
  const conf = SEVERITY_CONFIG[norm] || {
    label: level || 'N/A',
    bg: 'bg-slate-100',
    text: 'text-slate-700',
    border: 'border-slate-200',
  };

  const sizeClasses = size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-2.5 py-1 text-xs font-medium';

  return (
    <span
      className={`inline-flex items-center rounded-full border ${conf.bg} ${conf.text} ${conf.border} ${sizeClasses}`}
    >
      <span>{conf.label}</span>
      {score !== undefined && score !== null && (
        <span className="ml-1.5 px-1 py-0.2 rounded bg-black/5 font-mono text-[10px]">
          {score}/10
        </span>
      )}
    </span>
  );
}
