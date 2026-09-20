import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { PlusCircle, RefreshCw, Phone } from 'lucide-react';
import { useAuth } from '../lib/auth';
import { getComplaints } from '../lib/api';
import ComplaintCard from '../components/ComplaintCard';
import LoadingState from '../components/LoadingState';
import ErrorState from '../components/ErrorState';
import EmptyState from '../components/EmptyState';

export default function CitizenDashboard() {
  const { session } = useAuth();
  const [complaints, setComplaints] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchCitizenComplaints = async () => {
    setLoading(true);
    setError(null);
    try {
      const contact = session?.citizenContact ? session.citizenContact.trim() : '';
      const filters = contact ? { citizen_contact: contact } : {};
      const data = await getComplaints(filters);
      if (!Array.isArray(data)) {
        throw new Error('Invalid data format received from server.');
      }
      setComplaints(data);
    } catch (err) {
      setError(err.message || 'Failed to fetch complaints');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCitizenComplaints();
  }, [session?.citizenContact]);

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Prominent CTA Hero Banner */}
      <div className="bg-gradient-to-r from-brand-600 to-indigo-700 rounded-2xl p-6 mb-8 text-white shadow-md flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="space-y-1">
          <h2 className="text-lg sm:text-xl font-bold tracking-tight">
            See a civic problem in your neighborhood?
          </h2>
          <p className="text-xs text-brand-100 max-w-xl">
            Report potholes, broken streetlights, water leaks, or overflowing garbage. Our multimodal AI will classify and route it to the right department.
          </p>
        </div>
        <Link
          to="/citizen/report"
          className="inline-flex items-center justify-center gap-2 px-5 py-3 rounded-xl bg-white text-brand-700 hover:bg-brand-50 text-xs font-bold shadow-sm transition-all shrink-0"
        >
          <PlusCircle className="w-4 h-4 text-brand-600" />
          Report an Issue
        </Link>
      </div>

      {/* Header section */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">My Complaints</h1>
          <p className="text-xs text-slate-500 mt-1 flex items-center gap-1.5">
            <Phone className="w-3.5 h-3.5 text-slate-400" />
            Filtered for contact: <span className="font-mono font-semibold text-slate-700">{session?.citizenContact || 'None set'}</span>
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={fetchCitizenComplaints}
            className="p-2 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-600 shadow-2xs transition-colors cursor-pointer"
            title="Refresh list"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>

          <Link
            to="/citizen/report"
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-brand-600 hover:bg-brand-700 text-white text-xs font-semibold shadow-xs transition-colors"
          >
            <PlusCircle className="w-4 h-4" />
            Report an Issue
          </Link>
        </div>
      </div>

      {/* Content */}
      {loading ? (
        <LoadingState message="Fetching your submitted civic complaints..." />
      ) : error ? (
        <ErrorState message={error} onRetry={fetchCitizenComplaints} />
      ) : complaints.length === 0 ? (
        <EmptyState
          title="No complaints registered"
          description={`No complaints found under contact number ${session?.citizenContact || ''}.`}
          action={
            <Link
              to="/citizen/report"
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-brand-600 hover:bg-brand-700 text-white text-xs font-semibold transition-colors mt-2"
            >
              <PlusCircle className="w-4 h-4" />
              Report New Issue
            </Link>
          }
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {complaints.map((c) => (
            <ComplaintCard key={c.id} complaint={c} linkPrefix="/citizen/complaints" />
          ))}
        </div>
      )}
    </div>
  );
}
