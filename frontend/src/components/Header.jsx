import React from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { Shield, User, LogOut, Map, BarChart3, PlusCircle, Sliders } from 'lucide-react';
import { useAuth } from '../lib/auth';

export default function Header() {
  const { session, clearSession } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();

  const handleSwitchRole = () => {
    clearSession();
    navigate('/');
  };

  const isCitizen = session?.role === 'CITIZEN';
  const isAdminOrOfficer = session?.role === 'ADMIN' || session?.role === 'OFFICER';

  return (
    <header className="sticky top-0 z-40 bg-white border-b border-slate-200 shadow-2xs">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Brand */}
        <div className="flex items-center gap-6">
          <Link to="/" className="flex items-center gap-2 group">
            <div className="w-9 h-9 rounded-lg bg-brand-600 flex items-center justify-center text-white shadow-xs group-hover:bg-brand-700 transition-colors">
              <Shield className="w-5 h-5" />
            </div>
            <div>
              <span className="text-base font-bold text-slate-900 tracking-tight">ResolveIt</span>
              <span className="hidden sm:inline-block ml-2 text-[10px] font-semibold uppercase tracking-wider px-1.5 py-0.5 rounded bg-amber-100 text-amber-800 border border-amber-200">
                Demo Mode
              </span>
            </div>
          </Link>

          {/* Nav links */}
          {session && (
            <nav className="hidden md:flex items-center gap-1">
              {isCitizen && (
                <>
                  <Link
                    to="/citizen"
                    className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
                      location.pathname === '/citizen'
                        ? 'bg-slate-100 text-slate-900'
                        : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
                    }`}
                  >
                    My Complaints
                  </Link>
                  <Link
                    to="/citizen/report"
                    className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
                      location.pathname === '/citizen/report'
                        ? 'bg-brand-50 text-brand-700'
                        : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
                    }`}
                  >
                    <PlusCircle className="w-3.5 h-3.5" />
                    Report Issue
                  </Link>
                </>
              )}

              {isAdminOrOfficer && (
                <>
                  <Link
                    to="/admin"
                    className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
                      location.pathname === '/admin'
                        ? 'bg-slate-100 text-slate-900 font-semibold'
                        : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
                    }`}
                  >
                    <BarChart3 className="w-3.5 h-3.5" />
                    Work Queue
                  </Link>
                  <Link
                    to="/admin/map"
                    className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
                      location.pathname === '/admin/map'
                        ? 'bg-slate-100 text-slate-900 font-semibold'
                        : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
                    }`}
                  >
                    <Map className="w-3.5 h-3.5" />
                    Issue Map
                  </Link>
                  <Link
                    to="/demo"
                    className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
                      location.pathname === '/demo'
                        ? 'bg-slate-100 text-slate-900 font-semibold'
                        : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
                    }`}
                  >
                    <Sliders className="w-3.5 h-3.5" />
                    Control Panel
                  </Link>
                </>
              )}
            </nav>
          )}
        </div>

        {/* User Session / Switch role */}
        <div className="flex items-center gap-3">
          {session ? (
            <div className="flex items-center gap-2">
              <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-slate-100 border border-slate-200 text-xs text-slate-700">
                <User className="w-3.5 h-3.5 text-slate-500" />
                <span className="font-semibold">{session.role}</span>
                {session.citizenName && (
                  <span className="hidden sm:inline text-slate-400">({session.citizenName})</span>
                )}
              </div>

              <button
                type="button"
                onClick={handleSwitchRole}
                className="flex items-center gap-1 text-xs font-medium text-slate-500 hover:text-rose-600 px-2.5 py-1 rounded-md hover:bg-rose-50 transition-colors"
                title="Switch demo role"
              >
                <LogOut className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">Switch role</span>
              </button>
            </div>
          ) : (
            <span className="text-xs text-slate-400 italic">No role selected</span>
          )}
        </div>
      </div>
    </header>
  );
}
