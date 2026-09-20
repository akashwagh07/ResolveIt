import React from 'react';
import { Sliders, FastForward, CloudRain, Database, UserCheck, AlertCircle } from 'lucide-react';

export default function DemoControlPanel() {
  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
          <Sliders className="w-6 h-6 text-brand-600" />
          Demo Control Panel
        </h1>
        <p className="text-xs text-slate-500 mt-1">
          Simulation controller for virtual time travel, dynamic weather modifiers, and seeded officer actions.
        </p>
      </div>

      <div className="p-4 rounded-xl bg-blue-50 border border-blue-200 flex items-start gap-3">
        <AlertCircle className="w-5 h-5 text-blue-600 shrink-0 mt-0.5" />
        <div className="text-xs text-blue-900">
          <span className="font-semibold">Demo Control Simulator Placeholder: </span>
          The simulation controls below will allow fast-forwarding the virtual clock (`clock.py`), toggling Open-Meteo rain forecasts to trigger priority modifiers, and simulating officer before/after proof submission during live judge walkthroughs.
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-5 opacity-75">
        {/* Virtual Clock Controls */}
        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs">
          <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2 mb-2">
            <FastForward className="w-4 h-4 text-brand-600" />
            Virtual Clock Time Travel
          </h3>
          <p className="text-xs text-slate-500 mb-4">
            Advance the server-side virtual clock by 6h, 24h, or 72h to trigger deterministic SLA breach escalation.
          </p>
          <div className="flex gap-2">
            <button disabled className="flex-1 py-2 text-xs font-semibold rounded-lg bg-slate-100 text-slate-400 cursor-not-allowed border border-slate-200">
              +6 Hours
            </button>
            <button disabled className="flex-1 py-2 text-xs font-semibold rounded-lg bg-slate-100 text-slate-400 cursor-not-allowed border border-slate-200">
              +24 Hours (SLA breach)
            </button>
            <button disabled className="flex-1 py-2 text-xs font-semibold rounded-lg bg-slate-100 text-slate-400 cursor-not-allowed border border-slate-200">
              Reset Clock
            </button>
          </div>
        </div>

        {/* Dynamic Priority Weather Modifier */}
        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs">
          <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2 mb-2">
            <CloudRain className="w-4 h-4 text-sky-600" />
            Weather Modifier Simulation
          </h3>
          <p className="text-xs text-slate-500 mb-4">
            Toggle 48-hour rain forecast alerts to observe real-time priority elevation on drainage & road issues.
          </p>
          <div className="flex gap-2">
            <button disabled className="flex-1 py-2 text-xs font-semibold rounded-lg bg-slate-100 text-slate-400 cursor-not-allowed border border-slate-200">
              Simulate Heavy Rain
            </button>
            <button disabled className="flex-1 py-2 text-xs font-semibold rounded-lg bg-slate-100 text-slate-400 cursor-not-allowed border border-slate-200">
              Clear Weather
            </button>
          </div>
        </div>

        {/* Officer Simulation */}
        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs">
          <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2 mb-2">
            <UserCheck className="w-4 h-4 text-emerald-600" />
            Field Officer Simulator
          </h3>
          <p className="text-xs text-slate-500 mb-4">
            Simulate a department worker dispatching to the site and uploading before/after repair proof.
          </p>
          <button disabled className="w-full py-2 text-xs font-semibold rounded-lg bg-slate-100 text-slate-400 cursor-not-allowed border border-slate-200">
            Submit Simulated Proof of Fix
          </button>
        </div>

        {/* Database Reseeder */}
        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs">
          <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2 mb-2">
            <Database className="w-4 h-4 text-indigo-600" />
            Baseline Kolhapur Complaints
          </h3>
          <p className="text-xs text-slate-500 mb-4">
            Reset complaints across Kolhapur locations (Tarabai Park, Rankala Lake, Shahupuri, Laxmipuri).
          </p>
          <button disabled className="w-full py-2 text-xs font-semibold rounded-lg bg-slate-100 text-slate-400 cursor-not-allowed border border-slate-200">
            Re-run Baseline Seeder
          </button>
        </div>
      </div>
    </div>
  );
}
