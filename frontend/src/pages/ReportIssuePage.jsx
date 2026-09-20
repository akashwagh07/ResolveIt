import React from 'react';
import { Camera, Mic, MapPin, AlertCircle, ArrowLeft } from 'lucide-react';
import { Link } from 'react-router-dom';

export default function ReportIssuePage() {
  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-6">
        <Link
          to="/citizen"
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-500 hover:text-slate-800 transition-colors mb-3"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          Back to complaints
        </Link>
        <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Report an Issue</h1>
        <p className="text-xs text-slate-500 mt-1">
          Submit photos, voice notes or text of civic problems for AI categorization and resolution.
        </p>
      </div>

      {/* Notice Banner */}
      <div className="mb-6 p-4 rounded-xl bg-amber-50 border border-amber-200 flex items-start gap-3">
        <AlertCircle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
        <div className="text-xs text-amber-900">
          <span className="font-semibold">Prototype Intake Form: </span>
          Submission is disabled in this frontend view. Live multimodal intake and AI processing pipeline is currently wired through backend agent commands.
        </div>
      </div>

      {/* Disabled Form Skeleton */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 sm:p-8 shadow-xs space-y-6 opacity-75">
        {/* Description */}
        <div>
          <label className="block text-xs font-semibold text-slate-700 mb-1.5">
            Issue Description
          </label>
          <textarea
            disabled
            rows={4}
            placeholder="Describe the problem, location landmarks, or severity (e.g. large pothole causing traffic jam)..."
            className="w-full px-3 py-2 text-xs rounded-lg border border-slate-200 bg-slate-50 text-slate-400 cursor-not-allowed resize-none"
          />
        </div>

        {/* Media uploads row */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {/* Photo upload */}
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1.5">
              Photo / Video Proof
            </label>
            <div className="border-2 border-dashed border-slate-200 rounded-xl p-6 text-center bg-slate-50 cursor-not-allowed">
              <Camera className="w-6 h-6 text-slate-300 mx-auto mb-2" />
              <p className="text-xs font-medium text-slate-400">Click or drag images</p>
              <p className="text-[10px] text-slate-400 mt-0.5">JPEG, PNG, MP4 up to 25MB</p>
            </div>
          </div>

          {/* Audio recording */}
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1.5">
              Voice Note (Audio)
            </label>
            <div className="border-2 border-dashed border-slate-200 rounded-xl p-6 text-center bg-slate-50 cursor-not-allowed">
              <Mic className="w-6 h-6 text-slate-300 mx-auto mb-2" />
              <p className="text-xs font-medium text-slate-400">Record Marathi / Hindi / English voice</p>
              <p className="text-[10px] text-slate-400 mt-0.5">Microphone intake disabled</p>
            </div>
          </div>
        </div>

        {/* Location coordinates */}
        <div>
          <label className="block text-xs font-semibold text-slate-700 mb-1.5">
            Location Landmark & GPS
          </label>
          <div className="flex items-center gap-2">
            <div className="relative flex-1">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <MapPin className="w-4 h-4 text-slate-300" />
              </div>
              <input
                type="text"
                disabled
                placeholder="GPS detected: 16.7112, 74.2405 (Kolhapur)"
                className="w-full pl-9 pr-3 py-2 text-xs rounded-lg border border-slate-200 bg-slate-50 text-slate-400 cursor-not-allowed"
              />
            </div>
            <button
              type="button"
              disabled
              className="px-3 py-2 text-xs font-medium rounded-lg bg-slate-100 text-slate-400 border border-slate-200 cursor-not-allowed"
            >
              Detect Location
            </button>
          </div>
        </div>

        {/* Action button */}
        <div className="pt-4 border-t border-slate-100 flex justify-end">
          <button
            type="button"
            disabled
            className="px-5 py-2.5 rounded-lg bg-slate-300 text-slate-500 font-semibold text-xs cursor-not-allowed"
          >
            Submit Complaint (Disabled)
          </button>
        </div>
      </div>
    </div>
  );
}
