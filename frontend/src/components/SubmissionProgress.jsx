import React, { useState, useEffect } from 'react';
import { Loader2, XCircle, Sparkles } from 'lucide-react';

const PROGRESS_STEPS = [
  'Reading your report',
  'Checking the photo',
  'Assessing severity',
  'Choosing the right department',
];

export default function SubmissionProgress({ onCancel }) {
  const [currentStepIndex, setCurrentStepIndex] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentStepIndex((prev) => (prev + 1) % PROGRESS_STEPS.length);
    }, 2800);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="w-full bg-white border border-slate-200 rounded-2xl p-6 sm:p-8 shadow-md text-center space-y-5">
      <div className="inline-flex items-center justify-center w-14 h-14 rounded-full bg-brand-50 border border-brand-200 text-brand-600 mb-1">
        <Loader2 className="w-7 h-7 animate-spin text-brand-600" />
      </div>

      <div>
        <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-brand-50 text-brand-700 text-xs font-semibold mb-2">
          <Sparkles className="w-3.5 h-3.5" />
          Autonomous Civic Pipeline
        </div>
        <h2 className="text-xl font-bold text-slate-900 transition-all duration-300">
          {PROGRESS_STEPS[currentStepIndex]}...
        </h2>
        <p className="text-xs text-slate-500 mt-1 max-w-md mx-auto">
          Our multimodal AI agent is reviewing your submission, verifying media evidence, and calculating deterministic routing factors.
        </p>
      </div>

      {/* Honest step indicator dots */}
      <div className="flex items-center justify-center gap-2 pt-2">
        {PROGRESS_STEPS.map((step, idx) => (
          <div
            key={step}
            className={`h-1.5 rounded-full transition-all duration-500 ${
              idx === currentStepIndex
                ? 'w-8 bg-brand-600'
                : idx < currentStepIndex
                ? 'w-3 bg-brand-300'
                : 'w-3 bg-slate-200'
            }`}
          />
        ))}
      </div>

      <div className="pt-4 border-t border-slate-100 flex flex-col sm:flex-row items-center justify-center gap-3">
        <span className="text-[11px] text-slate-400">
          Takes about 10–20 seconds for multimodal verification.
        </span>
        <button
          type="button"
          onClick={onCancel}
          className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg border border-slate-300 hover:bg-slate-50 text-slate-700 text-xs font-semibold transition-colors cursor-pointer"
        >
          <XCircle className="w-3.5 h-3.5 text-slate-400" />
          Cancel Submission
        </button>
      </div>
    </div>
  );
}
