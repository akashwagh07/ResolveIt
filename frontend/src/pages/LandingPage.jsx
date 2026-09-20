import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Shield, User, Briefcase, ShieldAlert, ArrowRight, Sparkles, CheckCircle2, PlusCircle } from 'lucide-react';
import { useAuth } from '../lib/auth';

const PRESET_CITIZENS = [
  { name: 'Rahul Deshmukh', contact: '+91 9822012345', label: 'Tarabai Park (Rahul)' },
  { name: 'Priya Patil', contact: '+91 9822054321', label: 'Rankala Lake (Priya)' },
  { name: 'Amit Shinde', contact: '+91 9823099887', label: 'Shahupuri (Amit)' },
];

export default function LandingPage() {
  const { session, setSession } = useAuth();
  const navigate = useNavigate();

  const [selectedRole, setSelectedRole] = useState(session?.role || 'CITIZEN');
  const [citizenName, setCitizenName] = useState(session?.citizenName || 'Rahul Deshmukh');
  const [citizenContact, setCitizenContact] = useState(session?.citizenContact || '+91 9822012345');

  const handleApplyRole = (e) => {
    e.preventDefault();
    if (selectedRole === 'CITIZEN') {
      setSession('CITIZEN', citizenName, citizenContact);
      navigate('/citizen');
    } else if (selectedRole === 'OFFICER') {
      setSession('OFFICER', 'Department Officer', '');
      navigate('/admin');
    } else {
      setSession('ADMIN', 'Municipal Supervisor', '');
      navigate('/admin');
    }
  };

  return (
    <div className="min-h-[calc(100vh-4rem)] flex flex-col justify-center items-center px-4 py-12 bg-linear-to-b from-slate-50 via-white to-slate-100">
      <div className="max-w-3xl w-full text-center mb-10">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-brand-50 border border-brand-200 text-brand-700 text-xs font-semibold uppercase tracking-wider mb-4">
          <Sparkles className="w-3.5 h-3.5" />
          Autonomous Closed-Loop Civic Tech
        </div>

        <h1 className="text-4xl sm:text-5xl font-extrabold text-slate-900 tracking-tight mb-3">
          Resolve<span className="text-brand-600">It</span>
        </h1>
        <p className="text-lg sm:text-xl text-slate-600 max-w-xl mx-auto font-normal">
          AI-powered closed-loop civic issue resolution platform
        </p>
      </div>

      {/* Role Picker Card */}
      <div className="max-w-xl w-full bg-white rounded-2xl border border-slate-200 shadow-xl p-6 sm:p-8">
        <div className="mb-6 text-left">
          <h2 className="text-base font-bold text-slate-900">Select Demo Persona</h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Choose a role to explore the perspective of citizens or municipal authorities.
          </p>
        </div>

        <form onSubmit={handleApplyRole} className="space-y-5">
          {/* Roles radio group */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            {/* Citizen */}
            <button
              type="button"
              onClick={() => setSelectedRole('CITIZEN')}
              className={`flex flex-col items-center justify-center p-4 rounded-xl border text-center transition-all cursor-pointer ${
                selectedRole === 'CITIZEN'
                  ? 'border-brand-600 bg-brand-50/50 text-brand-900 ring-2 ring-brand-500/20 shadow-xs'
                  : 'border-slate-200 hover:border-slate-300 text-slate-700 hover:bg-slate-50'
              }`}
            >
              <User className={`w-6 h-6 mb-2 ${selectedRole === 'CITIZEN' ? 'text-brand-600' : 'text-slate-400'}`} />
              <span className="text-sm font-semibold">Citizen</span>
              <span className="text-[11px] text-slate-500 mt-0.5">Track my issues</span>
            </button>

            {/* Officer */}
            <button
              type="button"
              onClick={() => setSelectedRole('OFFICER')}
              className={`flex flex-col items-center justify-center p-4 rounded-xl border text-center transition-all cursor-pointer ${
                selectedRole === 'OFFICER'
                  ? 'border-brand-600 bg-brand-50/50 text-brand-900 ring-2 ring-brand-500/20 shadow-xs'
                  : 'border-slate-200 hover:border-slate-300 text-slate-700 hover:bg-slate-50'
              }`}
            >
              <Briefcase className={`w-6 h-6 mb-2 ${selectedRole === 'OFFICER' ? 'text-brand-600' : 'text-slate-400'}`} />
              <span className="text-sm font-semibold">Officer</span>
              <span className="text-[11px] text-slate-500 mt-0.5">Department queue</span>
            </button>

            {/* Admin */}
            <button
              type="button"
              onClick={() => setSelectedRole('ADMIN')}
              className={`flex flex-col items-center justify-center p-4 rounded-xl border text-center transition-all cursor-pointer ${
                selectedRole === 'ADMIN'
                  ? 'border-brand-600 bg-brand-50/50 text-brand-900 ring-2 ring-brand-500/20 shadow-xs'
                  : 'border-slate-200 hover:border-slate-300 text-slate-700 hover:bg-slate-50'
              }`}
            >
              <ShieldAlert className={`w-6 h-6 mb-2 ${selectedRole === 'ADMIN' ? 'text-brand-600' : 'text-slate-400'}`} />
              <span className="text-sm font-semibold">Admin</span>
              <span className="text-[11px] text-slate-500 mt-0.5">Full municipal view</span>
            </button>
          </div>

          {/* Citizen parameters */}
          {selectedRole === 'CITIZEN' && (
            <div className="pt-3 border-t border-slate-100 space-y-3.5 text-left">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Citizen Name
                </label>
                <input
                  type="text"
                  required
                  value={citizenName}
                  onChange={(e) => setCitizenName(e.target.value)}
                  placeholder="e.g. Rahul Deshmukh"
                  className="w-full px-3 py-2 text-xs rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500 bg-white"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Contact Phone Number
                </label>
                <input
                  type="text"
                  required
                  value={citizenContact}
                  onChange={(e) => setCitizenContact(e.target.value)}
                  placeholder="e.g. +91 9822012345"
                  className="w-full px-3 py-2 text-xs rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500 bg-white"
                />
              </div>

              {/* Quick-fill sample citizens */}
              <div className="pt-1">
                <p className="text-[11px] text-slate-400 font-medium mb-1.5">Quick fill sample citizen:</p>
                <div className="flex flex-wrap gap-1.5">
                  {PRESET_CITIZENS.map((preset) => (
                    <button
                      key={preset.contact}
                      type="button"
                      onClick={() => {
                        setCitizenName(preset.name);
                        setCitizenContact(preset.contact);
                      }}
                      className="text-[11px] px-2.5 py-1 rounded-md bg-slate-100 hover:bg-slate-200 text-slate-700 transition-colors cursor-pointer"
                    >
                      {preset.label}
                    </button>
                  ))}
                </div>
              </div>

              <div className="pt-2 text-center">
                <button
                  type="button"
                  onClick={() => {
                    setSession('CITIZEN', citizenName, citizenContact);
                    navigate('/citizen/report');
                  }}
                  className="inline-flex items-center gap-1.5 text-xs font-semibold text-brand-600 hover:text-brand-700 hover:underline cursor-pointer"
                >
                  <PlusCircle className="w-3.5 h-3.5" />
                  Or jump directly to Report an Issue &rarr;
                </button>
              </div>
            </div>
          )}

          <button
            type="submit"
            className="w-full flex items-center justify-center gap-2 py-2.5 px-4 rounded-xl bg-brand-600 hover:bg-brand-700 text-white font-semibold text-sm shadow-md hover:shadow-lg transition-all cursor-pointer"
          >
            Enter as {selectedRole}
            <ArrowRight className="w-4 h-4" />
          </button>
        </form>

        <p className="mt-4 text-[11px] text-slate-400 text-center">
          Demo session is persisted in browser local storage. No actual authentication is performed.
        </p>
      </div>
    </div>
  );
}
