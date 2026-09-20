import React from 'react';
import { Link } from 'react-router-dom';
import { MapPin, Calendar, ArrowUpRight, AlertCircle } from 'lucide-react';
import StatusBadge from './StatusBadge';
import SeverityBadge from './SeverityBadge';
import PriorityBadge from './PriorityBadge';

export default function ComplaintCard({ complaint, linkPrefix = '/citizen/complaints' }) {
  const formattedDate = new Date(complaint.created_at).toLocaleDateString('en-IN', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  });

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs hover:shadow-md transition-all flex flex-col justify-between">
      <div>
        <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
          <div className="flex items-center gap-2">
            <span className="text-xs font-bold text-brand-700 bg-brand-50 px-2 py-0.5 rounded border border-brand-200">
              {complaint.category}
            </span>
            <span className="text-xs text-slate-500 font-mono">#{complaint.id.slice(0, 8)}</span>
          </div>
          <StatusBadge status={complaint.status} size="sm" />
        </div>

        <h4 className="text-base font-semibold text-slate-900 mb-1 line-clamp-1">
          {complaint.issue.replace(/_/g, ' ')}
        </h4>

        <p className="text-xs text-slate-600 line-clamp-2 mb-3">
          {complaint.raw_text}
        </p>

        <div className="space-y-1.5 text-xs text-slate-500 mb-4">
          <div className="flex items-center gap-1.5 truncate">
            <MapPin className="w-3.5 h-3.5 text-slate-400 shrink-0" />
            <span className="truncate">{complaint.address_text}</span>
          </div>
          <div className="flex items-center gap-1.5">
            <Calendar className="w-3.5 h-3.5 text-slate-400 shrink-0" />
            <span>{formattedDate}</span>
          </div>
        </div>
      </div>

      <div className="pt-3 border-t border-slate-100 flex items-center justify-between">
        <div className="flex items-center gap-1.5 flex-wrap">
          <SeverityBadge level={complaint.severity_level} score={complaint.severity_score} size="sm" />
          <PriorityBadge priority={complaint.priority} size="sm" />
        </div>

        <Link
          to={`${linkPrefix}/${complaint.id}`}
          className="inline-flex items-center gap-1 text-xs font-semibold text-brand-600 hover:text-brand-800 transition-colors"
        >
          Details
          <ArrowUpRight className="w-3.5 h-3.5" />
        </Link>
      </div>
    </div>
  );
}
