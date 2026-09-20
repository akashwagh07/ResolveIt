import React from 'react';
import { CheckCircle2, AlertTriangle, Clock, ArrowRight } from 'lucide-react';
import StatusBadge from './StatusBadge';

const MAIN_STEPS = [
  { key: 'SUBMITTED', label: 'Submitted' },
  { key: 'AI_ANALYZING', label: 'AI Intake' },
  { key: 'CLASSIFIED', label: 'Classified' },
  { key: 'UNDER_REVIEW', label: 'Review' },
  { key: 'ASSIGNED', label: 'Assigned' },
  { key: 'IN_PROGRESS', label: 'In Progress' },
  { key: 'RESOLUTION_SUBMITTED', label: 'Work Done' },
  { key: 'AI_VERIFICATION', label: 'AI Check' },
  { key: 'ADMIN_VERIFICATION', label: 'Admin Approval' },
  { key: 'CITIZEN_CONFIRMATION', label: 'Citizen Check' },
  { key: 'RESOLVED', label: 'Resolved' },
];

const EXCEPTION_STATES = new Set([
  'HUMAN_REVIEW',
  'OUT_OF_SCOPE',
  'MERGED',
  'ESCALATED',
  'REOPENED',
  'ERROR',
]);

export default function StatusTimeline({ currentStatus, previousStatus }) {
  const isException = EXCEPTION_STATES.has(currentStatus);
  const mainIndex = MAIN_STEPS.findIndex((s) => s.key === currentStatus);

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-slate-800 flex items-center gap-2">
          <Clock className="w-4 h-4 text-brand-600" />
          Lifecycle Progress
        </h3>
        <StatusBadge status={currentStatus} />
      </div>

      {isException && (
        <div className="mb-5 p-3.5 rounded-lg bg-amber-50 border border-amber-200 flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
          <div className="text-xs text-amber-900">
            <span className="font-semibold">Special State Active: </span>
            This complaint is currently in <span className="font-mono font-semibold">{currentStatus}</span>
            {previousStatus && (
              <span> (transitioned from <span className="font-mono font-semibold">{previousStatus}</span>)</span>
            )}.
          </div>
        </div>
      )}

      {/* Main flow steps horizontal/responsive */}
      <div className="overflow-x-auto pb-2">
        <div className="flex items-center min-w-[760px] justify-between">
          {MAIN_STEPS.map((step, idx) => {
            const isCurrent = step.key === currentStatus;
            const isCompleted = mainIndex !== -1 && idx < mainIndex;
            const isUpcoming = mainIndex === -1 ? true : idx > mainIndex;

            let circleClass = 'bg-slate-100 text-slate-400 border-slate-200';
            if (isCompleted) {
              circleClass = 'bg-emerald-500 text-white border-emerald-500';
            } else if (isCurrent) {
              circleClass = 'bg-brand-600 text-white border-brand-600 ring-4 ring-brand-100';
            }

            return (
              <div key={step.key} className="flex-1 flex flex-col items-center relative group">
                {idx > 0 && (
                  <div
                    className={`absolute top-3 right-[50%] left-[-50%] h-0.5 -translate-y-1/2 z-0 ${
                      isCompleted ? 'bg-emerald-500' : 'bg-slate-200'
                    }`}
                  />
                )}

                <div
                  className={`relative z-10 w-6 h-6 rounded-full border flex items-center justify-center text-[10px] font-semibold transition-all ${circleClass}`}
                >
                  {isCompleted ? <CheckCircle2 className="w-3.5 h-3.5" /> : idx + 1}
                </div>

                <span
                  className={`mt-2 text-[11px] text-center whitespace-nowrap font-medium ${
                    isCurrent
                      ? 'text-brand-700 font-bold'
                      : isCompleted
                      ? 'text-slate-700'
                      : 'text-slate-400'
                  }`}
                >
                  {step.label}
                </span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
