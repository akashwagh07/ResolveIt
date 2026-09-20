import React from 'react';

const PRIORITY_CONFIG = {
  NORMAL: { label: 'Normal', bg: 'bg-slate-100', text: 'text-slate-700', border: 'border-slate-200' },
  STANDARD: { label: 'Standard', bg: 'bg-blue-50', text: 'text-blue-700', border: 'border-blue-200' },
  HIGH: { label: 'High Priority', bg: 'bg-amber-50', text: 'text-amber-800', border: 'border-amber-300' },
  EMERGENCY: { label: 'Emergency', bg: 'bg-red-50', text: 'text-red-700', border: 'border-red-300', pulse: true },
};

export default function PriorityBadge({ priority, size = 'md' }) {
  const norm = (priority || '').toUpperCase();
  const conf = PRIORITY_CONFIG[norm] || {
    label: priority || 'Normal',
    bg: 'bg-slate-100',
    text: 'text-slate-700',
    border: 'border-slate-200',
  };

  const sizeClasses = size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-2.5 py-1 text-xs font-medium';

  return (
    <span
      className={`inline-flex items-center rounded-full border ${conf.bg} ${conf.text} ${conf.border} ${sizeClasses}`}
    >
      {conf.pulse && (
        <span className="relative flex h-2 w-2 mr-1.5">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
          <span className="relative inline-flex rounded-full h-2 w-2 bg-red-500"></span>
        </span>
      )}
      {conf.label}
    </span>
  );
}
