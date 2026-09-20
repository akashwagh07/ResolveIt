import React, { useEffect, useState } from 'react';
import { Sliders, FastForward, CloudRain, Database, UserCheck, AlertCircle, Shield, User, Phone, Building, Loader2 } from 'lucide-react';
import { whoami } from '../lib/api';
import { useAuth } from '../lib/auth';

export default function DemoControlPanel() {
  const { session } = useAuth();
  const [identity, setIdentity] = useState(null);
  const [loadingIdentity, setLoadingIdentity] = useState(true);
  const [identityError, setIdentityError] = useState('');

  useEffect(() => {
    setLoadingIdentity(true);
    whoami()
      .then((data) => setIdentity(data))
      .catch((err) => setIdentityError(err.message))
      .finally(() => setLoadingIdentity(false));
  }, []);

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

      {/* Resolved Caller Identity Card */}
      <div className="p-5 rounded-2xl bg-white border border-slate-200 shadow-xs space-y-3">
        <div className="flex items-center justify-between border-b border-slate-100 pb-2.5">
          <h2 className="text-sm font-bold text-slate-900 flex items-center gap-2">
            <Shield className="w-4 h-4 text-brand-600" />
            Active Session Identity (GET /api/auth/whoami)
          </h2>
          <span className="text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded bg-brand-50 text-brand-700 border border-brand-200">
            {session?.role || 'Unauthenticated'}
          </span>
        </div>

        {loadingIdentity ? (
          <div className="py-4 text-xs text-slate-400 flex items-center justify-center gap-2">
            <Loader2 className="w-4 h-4 animate-spin text-brand-600" />
            Resolving identity headers from backend...
          </div>
        ) : identityError ? (
          <div className="p-3 rounded-lg bg-rose-50 border border-rose-200 text-rose-800 text-xs">
            Failed to resolve identity: {identityError}
          </div>
        ) : identity ? (
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
            <div className="p-3 rounded-xl bg-slate-50 border border-slate-100">
              <span className="text-slate-400 block font-medium mb-0.5">Caller Name</span>
              <span className="font-bold text-slate-800 flex items-center gap-1.5">
                <User className="w-3.5 h-3.5 text-slate-400" />
                {identity.name}
              </span>
            </div>

            <div className="p-3 rounded-xl bg-slate-50 border border-slate-100">
              <span className="text-slate-400 block font-medium mb-0.5">Role & Contact</span>
              <span className="font-bold text-slate-800 block">
                {identity.role}
              </span>
              {identity.contact && (
                <span className="text-[11px] text-slate-500 font-mono mt-0.5 block">
                  {identity.contact}
                </span>
              )}
            </div>

            <div className="p-3 rounded-xl bg-slate-50 border border-slate-100">
              <span className="text-slate-400 block font-medium mb-0.5">Assigned Department</span>
              {identity.department ? (
                <div>
                  <span className="font-bold text-slate-800 block">
                    {identity.department.name}
                  </span>
                  <span className="text-[10px] font-mono text-slate-400 uppercase">
                    Code: {identity.department.code} (ID: #{identity.department.id})
                  </span>
                </div>
              ) : (
                <span className="text-slate-400 italic">None (Citizen or unassigned)</span>
              )}
            </div>
          </div>
        ) : null}
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
