import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Shield, User, Briefcase, ShieldAlert, ArrowRight, Sparkles, CheckCircle2, PlusCircle, AlertCircle, KeyRound, Building2 } from 'lucide-react';
import { useAuth } from '../lib/auth';
import { getUsers, getDepartments, whoami } from '../lib/api';

const PRESET_CITIZENS = [
  { name: 'Rahul Deshmukh', contact: '+91 9822012345', label: 'Tarabai Park (Rahul)' },
  { name: 'Priya Patil', contact: '+91 9822054321', label: 'Rankala Lake (Priya)' },
  { name: 'Amit Shinde', contact: '+91 9823099887', label: 'Shahupuri (Amit)' },
];

export default function LandingPage() {
  const { session, setSession, authNotice, clearAuthNotice } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [selectedRole, setSelectedRole] = useState(session?.role || 'CITIZEN');
  const [citizenName, setCitizenName] = useState(session?.name || 'Rahul Deshmukh');
  const [citizenContact, setCitizenContact] = useState(session?.citizenContact || '+91 9822012345');

  // Officer / Admin state
  const [demoUsers, setDemoUsers] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [selectedUserId, setSelectedUserId] = useState('');
  const [passcode, setPasscode] = useState('');
  const [loadingUsers, setLoadingUsers] = useState(false);
  const [loginError, setLoginError] = useState('');
  const [isValidating, setIsValidating] = useState(false);
  const passcodeHint = (import.meta.env.VITE_DEMO_PASSCODE_HINT || '').trim();

  // Load departments once
  useEffect(() => {
    getDepartments()
      .then((depts) => setDepartments(Array.isArray(depts) ? depts : []))
      .catch(() => setDepartments([]));
  }, []);

  // Fetch users when switching to OFFICER or ADMIN
  useEffect(() => {
    if (selectedRole === 'OFFICER' || selectedRole === 'ADMIN') {
      setLoadingUsers(true);
      setLoginError('');
      getUsers(selectedRole)
        .then((users) => {
          const list = Array.isArray(users) ? users : [];
          setDemoUsers(list);
          if (list.length > 0) {
            setSelectedUserId(String(list[0].id));
          } else {
            setSelectedUserId('');
          }
        })
        .catch((err) => {
          setLoginError(`Failed to load ${selectedRole.toLowerCase()} accounts: ${err.message}`);
        })
        .finally(() => setLoadingUsers(false));
    }
  }, [selectedRole]);

  // Combined notice from auth context or router navigation state
  const displayNotice = location.state?.message || authNotice;

  const handleApplyRole = async (e) => {
    e.preventDefault();
    setLoginError('');

    if (selectedRole === 'CITIZEN') {
      if (!citizenContact.trim()) {
        setLoginError('Citizen contact phone number is required.');
        return;
      }
      setSession({
        role: 'CITIZEN',
        name: citizenName.trim() || 'Citizen',
        citizenContact: citizenContact.trim(),
      });
      clearAuthNotice();
      navigate('/citizen');
      return;
    }

    // OFFICER or ADMIN validation
    const uid = parseInt(selectedUserId, 10);
    if (!uid) {
      setLoginError(`Please select a demo ${selectedRole.toLowerCase()} account.`);
      return;
    }

    if (!passcode) {
      setLoginError('Passcode is required for municipal staff login.');
      return;
    }

    setIsValidating(true);
    try {
      const headers = {
        'X-Demo-Role': selectedRole,
        'X-Demo-User-Id': String(uid),
        'X-Demo-Passcode': passcode,
      };

      const identity = await whoami(headers);
      const userObj = demoUsers.find((u) => u.id === uid);
      const deptObj = departments.find((d) => d.id === userObj?.department_id);

      setSession(
        {
          role: selectedRole,
          userId: uid,
          name: identity.name || userObj?.name || `${selectedRole} User`,
          departmentId: userObj?.department_id || null,
          departmentName: identity.department?.name || deptObj?.name || '',
          citizenContact: '',
        },
        passcode
      );

      clearAuthNotice();
      if (selectedRole === 'OFFICER') {
        navigate('/officer');
      } else {
        navigate('/admin');
      }
    } catch (err) {
      if (
        err.status === 401 ||
        err.message?.includes('401') ||
        err.message?.includes('Wrong passcode') ||
        err.message === 'Invalid passcode' ||
        err.message?.toLowerCase().includes('passcode')
      ) {
        setLoginError('Wrong passcode. Ask the team for the demo passcode.');
      } else {
        setLoginError(err.message || 'Invalid passcode or credentials. Access denied.');
      }
    } finally {
      setIsValidating(false);
    }
  };

  return (
    <div className="min-h-[calc(100vh-4rem)] flex flex-col justify-center items-center px-4 py-12 bg-linear-to-b from-slate-50 via-white to-slate-100">
      <div className="max-w-3xl w-full text-center mb-8">
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

        <div className="inline-block mt-3 px-3 py-1 rounded-full bg-amber-50 border border-amber-200 text-amber-900 text-xs font-medium">
          <span className="font-bold uppercase tracking-wider text-amber-700 mr-1.5">Demo mode:</span>
          Simulated demo identity for judging and walkthroughs. Not real authentication.
        </div>
      </div>

      {/* Redirect / Auth Notice Banner */}
      {displayNotice && (
        <div className="max-w-xl w-full mb-6 p-4 rounded-xl bg-amber-50 border border-amber-200 flex items-start gap-3 shadow-xs">
          <AlertCircle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
          <div className="text-xs text-amber-900 flex-1">
            <span className="font-bold">Notice: </span>
            {displayNotice}
          </div>
          <button
            type="button"
            onClick={() => clearAuthNotice()}
            className="text-xs font-semibold text-amber-700 hover:text-amber-900 cursor-pointer"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Role Picker Card */}
      <div className="max-w-xl w-full bg-white rounded-2xl border border-slate-200 shadow-xl p-6 sm:p-8">
        <div className="mb-6 text-left">
          <h2 className="text-base font-bold text-slate-900">Select Demo Persona</h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Choose a role to explore the perspective of citizens, field officers, or municipal supervisors.
          </p>
        </div>

        {loginError && (
          <div className="mb-5 p-3.5 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-start gap-2.5">
            <AlertCircle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
            <div className="flex-1 font-medium">{loginError}</div>
          </div>
        )}

        <form onSubmit={handleApplyRole} className="space-y-5">
          {/* Roles radio group */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            {/* Citizen */}
            <button
              type="button"
              onClick={() => {
                setSelectedRole('CITIZEN');
                setLoginError('');
              }}
              className={`flex flex-col items-center justify-center p-4 rounded-xl border text-center transition-all cursor-pointer ${
                selectedRole === 'CITIZEN'
                  ? 'border-brand-600 bg-brand-50/50 text-brand-900 ring-2 ring-brand-500/20 shadow-xs'
                  : 'border-slate-200 hover:border-slate-300 text-slate-700 hover:bg-slate-50'
              }`}
            >
              <User className={`w-6 h-6 mb-2 ${selectedRole === 'CITIZEN' ? 'text-brand-600' : 'text-slate-400'}`} />
              <span className="text-sm font-semibold">Citizen</span>
              <span className="text-[11px] text-slate-500 mt-0.5">Report & track</span>
            </button>

            {/* Officer */}
            <button
              type="button"
              onClick={() => {
                setSelectedRole('OFFICER');
                setLoginError('');
              }}
              className={`flex flex-col items-center justify-center p-4 rounded-xl border text-center transition-all cursor-pointer ${
                selectedRole === 'OFFICER'
                  ? 'border-brand-600 bg-brand-50/50 text-brand-900 ring-2 ring-brand-500/20 shadow-xs'
                  : 'border-slate-200 hover:border-slate-300 text-slate-700 hover:bg-slate-50'
              }`}
            >
              <Briefcase className={`w-6 h-6 mb-2 ${selectedRole === 'OFFICER' ? 'text-brand-600' : 'text-slate-400'}`} />
              <span className="text-sm font-semibold">Officer</span>
              <span className="text-[11px] text-slate-500 mt-0.5">My work queue</span>
            </button>

            {/* Admin */}
            <button
              type="button"
              onClick={() => {
                setSelectedRole('ADMIN');
                setLoginError('');
              }}
              className={`flex flex-col items-center justify-center p-4 rounded-xl border text-center transition-all cursor-pointer ${
                selectedRole === 'ADMIN'
                  ? 'border-brand-600 bg-brand-50/50 text-brand-900 ring-2 ring-brand-500/20 shadow-xs'
                  : 'border-slate-200 hover:border-slate-300 text-slate-700 hover:bg-slate-50'
              }`}
            >
              <ShieldAlert className={`w-6 h-6 mb-2 ${selectedRole === 'ADMIN' ? 'text-brand-600' : 'text-slate-400'}`} />
              <span className="text-sm font-semibold">Admin</span>
              <span className="text-[11px] text-slate-500 mt-0.5">Municipal command</span>
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
                    setSession({
                      role: 'CITIZEN',
                      name: citizenName.trim(),
                      citizenContact: citizenContact.trim(),
                    });
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

          {/* Officer or Admin parameters */}
          {(selectedRole === 'OFFICER' || selectedRole === 'ADMIN') && (
            <div className="pt-3 border-t border-slate-100 space-y-3.5 text-left">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Select {selectedRole === 'OFFICER' ? 'Field Officer' : 'Admin / Supervisor'} Account
                </label>
                {loadingUsers ? (
                  <div className="p-2.5 text-xs text-slate-500 bg-slate-50 border border-slate-200 rounded-lg animate-pulse">
                    Loading demo accounts...
                  </div>
                ) : (
                  <select
                    value={selectedUserId}
                    onChange={(e) => setSelectedUserId(e.target.value)}
                    className="w-full px-3 py-2 text-xs rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500 bg-white"
                  >
                    {demoUsers.map((user) => {
                      const dept = departments.find((d) => d.id === user.department_id);
                      const deptLabel = dept ? ` — ${dept.name}` : (user.department_id ? ` — Dept #${user.department_id}` : '');
                      return (
                        <option key={user.id} value={user.id}>
                          {user.name}{deptLabel}
                        </option>
                      );
                    })}
                  </select>
                )}
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1 flex items-center justify-between">
                  <span className="flex items-center gap-1">
                    <KeyRound className="w-3.5 h-3.5 text-slate-400" />
                    Demo Passcode
                  </span>
                  {passcodeHint ? (
                    <span className="text-[10px] text-slate-400 font-normal">
                      (Hint: <code className="bg-slate-100 px-1 py-0.5 rounded font-mono">{passcodeHint}</code>)
                    </span>
                  ) : null}
                </label>
                <input
                  type="password"
                  required
                  value={passcode}
                  onChange={(e) => setPasscode(e.target.value)}
                  placeholder="Enter demo passcode"
                  className="w-full px-3 py-2 text-xs rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500 bg-white"
                />
              </div>

              <div className="text-[11px] text-slate-400">
                Credentials are validated against the backend <code className="text-slate-600 font-mono">GET /api/auth/whoami</code> before creating your session.
              </div>
            </div>
          )}

          <button
            type="submit"
            disabled={isValidating}
            className="w-full flex items-center justify-center gap-2 py-2.5 px-4 rounded-xl bg-brand-600 hover:bg-brand-700 disabled:bg-slate-300 text-white font-semibold text-sm shadow-md hover:shadow-lg transition-all cursor-pointer"
          >
            {isValidating ? (
              <span>Validating identity...</span>
            ) : (
              <>
                <span>Enter as {selectedRole}</span>
                <ArrowRight className="w-4 h-4" />
              </>
            )}
          </button>
        </form>

        <p className="mt-4 text-[11px] text-slate-400 text-center">
          Demo session is stored in localStorage; passcode is kept in sessionStorage only.
        </p>
      </div>
    </div>
  );
}
