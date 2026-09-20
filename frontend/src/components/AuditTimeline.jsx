import React, { useState } from 'react';
import { ShieldCheck, User, Bot, Server, ChevronDown, ChevronRight, Terminal } from 'lucide-react';

function getActorBadge(actor) {
  const norm = (actor || '').toUpperCase();
  if (norm.startsWith('AGENT')) {
    return { label: actor, icon: Bot, bg: 'bg-purple-100 text-purple-700' };
  }
  if (norm === 'SYSTEM' || norm === 'SCHEDULER') {
    return { label: actor, icon: Server, bg: 'bg-slate-100 text-slate-700' };
  }
  if (norm === 'ADMIN') {
    return { label: actor, icon: ShieldCheck, bg: 'bg-indigo-100 text-indigo-700' };
  }
  return { label: actor, icon: User, bg: 'bg-blue-100 text-blue-700' };
}

export default function AuditTimeline({ events = [] }) {
  const [expandedId, setExpandedId] = useState(null);

  // Sorted newest last (chronological)
  const sortedEvents = [...events].sort(
    (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
  );

  if (!sortedEvents.length) {
    return (
      <div className="py-8 text-center text-sm text-slate-400 bg-slate-50 rounded-xl border border-slate-200">
        No audit events recorded yet.
      </div>
    );
  }

  return (
    <div className="relative pl-6 space-y-6 before:absolute before:left-2.5 before:top-2 before:bottom-2 before:w-0.5 before:bg-slate-200">
      {sortedEvents.map((evt) => {
        const actorInfo = getActorBadge(evt.actor);
        const Icon = actorInfo.icon;
        const isExpanded = expandedId === evt.id;
        const hasDetail = evt.detail && Object.keys(evt.detail).length > 0;
        const dateStr = new Date(evt.timestamp).toLocaleString('en-IN', {
          dateStyle: 'medium',
          timeStyle: 'short',
        });

        return (
          <div key={evt.id} className="relative group">
            {/* Timeline bullet */}
            <div className="absolute -left-[27px] top-1 w-3 h-3 rounded-full bg-white border-2 border-brand-600 shadow-sm" />

            <div className="bg-white rounded-lg border border-slate-200 p-3.5 shadow-xs hover:border-slate-300 transition-colors">
              <div className="flex flex-wrap items-center justify-between gap-2 mb-1">
                <div className="flex items-center gap-2">
                  <span
                    className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-semibold ${actorInfo.bg}`}
                  >
                    <Icon className="w-3 h-3" />
                    {actorInfo.label}
                  </span>
                  <span className="font-mono text-xs font-semibold text-slate-800">
                    {evt.action}
                  </span>
                </div>
                <time className="text-[11px] text-slate-400">{dateStr}</time>
              </div>

              {evt.reasoning && (
                <p className="text-xs text-slate-600 mt-1 italic bg-slate-50 p-2 rounded border border-slate-100">
                  "{evt.reasoning}"
                </p>
              )}

              {evt.confidence !== null && evt.confidence !== undefined && (
                <div className="mt-1 text-[11px] text-slate-500 font-medium">
                  Confidence: <span className="font-mono text-brand-700 font-semibold">{(evt.confidence * 100).toFixed(0)}%</span>
                </div>
              )}

              {hasDetail && (
                <div className="mt-2 pt-2 border-t border-slate-100">
                  <button
                    type="button"
                    onClick={() => setExpandedId(isExpanded ? null : evt.id)}
                    className="flex items-center gap-1 text-[11px] text-slate-500 hover:text-slate-800 font-medium cursor-pointer"
                  >
                    {isExpanded ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
                    <Terminal className="w-3 h-3 text-slate-400" />
                    {isExpanded ? 'Hide Payload' : 'View Payload Details'}
                  </button>

                  {isExpanded && (
                    <pre className="mt-2 p-2.5 rounded bg-slate-900 text-slate-200 text-[11px] font-mono overflow-x-auto max-h-48 border border-slate-800">
                      {JSON.stringify(evt.detail, null, 2)}
                    </pre>
                  )}
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
