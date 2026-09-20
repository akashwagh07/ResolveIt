import React, { useEffect, useState } from 'react';
import { useParams, useLocation, Link } from 'react-router-dom';
import {
  ArrowLeft,
  MapPin,
  Calendar,
  Clock,
  Shield,
  User,
  Phone,
  FileText,
  Cpu,
  Layers,
  Image as ImageIcon,
  History,
  AlertTriangle,
  Maximize2,
  X,
  Volume2,
} from 'lucide-react';
import { getComplaint, getDepartments } from '../lib/api';
import StatusBadge from '../components/StatusBadge';
import SeverityBadge from '../components/SeverityBadge';
import PriorityBadge from '../components/PriorityBadge';
import StatusTimeline from '../components/StatusTimeline';
import AuditTimeline from '../components/AuditTimeline';
import LoadingState from '../components/LoadingState';
import ErrorState from '../components/ErrorState';

export default function ComplaintDetailPage() {
  const { id } = useParams();
  const location = useLocation();
  const [complaint, setComplaint] = useState(null);
  const [departments, setDepartments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [expandedImage, setExpandedImage] = useState(null);
  const [mediaErrors, setMediaErrors] = useState({});

  const isAdminView = location.pathname.startsWith('/admin');
  const backLink = isAdminView ? '/admin' : '/citizen';

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [compData, deptData] = await Promise.all([
        getComplaint(id),
        getDepartments().catch(() => []),
      ]);
      setComplaint(compData);
      setDepartments(deptData);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [id]);

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-12">
        <LoadingState message="Loading complaint dossier and audit events..." />
      </div>
    );
  }

  if (error || !complaint) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-12">
        <ErrorState message={error || 'Complaint not found'} onRetry={fetchData} />
      </div>
    );
  }

  const departmentObj = departments.find((d) => d.id === complaint.department_id);
  const deptName = departmentObj ? departmentObj.name : `Department #${complaint.department_id}`;

  const createdDate = new Date(complaint.created_at).toLocaleString('en-IN', {
    dateStyle: 'medium',
    timeStyle: 'short',
  });

  const slaDate = complaint.sla_deadline
    ? new Date(complaint.sla_deadline).toLocaleString('en-IN', {
        dateStyle: 'medium',
        timeStyle: 'short',
      })
    : null;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
      {/* Navigation & Header */}
      <div>
        <Link
          to={backLink}
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-500 hover:text-slate-900 transition-colors mb-4"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          Back to {isAdminView ? 'Work Queue' : 'My Complaints'}
        </Link>

        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white p-6 rounded-2xl border border-slate-200 shadow-xs">
          <div>
            <div className="flex flex-wrap items-center gap-2 mb-2">
              <span className="font-mono text-xs font-bold text-slate-400">
                #{complaint.id}
              </span>
              <span className="text-xs font-bold text-brand-700 bg-brand-50 px-2.5 py-0.5 rounded-full border border-brand-200">
                {complaint.category}
              </span>
              {complaint.needs_review && (
                <span className="inline-flex items-center gap-1 text-xs font-bold text-amber-800 bg-amber-100 px-2 py-0.5 rounded-full border border-amber-200">
                  <AlertTriangle className="w-3 h-3" />
                  Needs Review
                </span>
              )}
            </div>

            <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
              {complaint.issue.replace(/_/g, ' ')}
            </h1>

            <div className="flex flex-wrap items-center gap-4 text-xs text-slate-500 mt-2">
              <span className="flex items-center gap-1">
                <MapPin className="w-3.5 h-3.5 text-slate-400" />
                {complaint.address_text}
              </span>
              <span className="flex items-center gap-1">
                <Calendar className="w-3.5 h-3.5 text-slate-400" />
                Submitted {createdDate}
              </span>
            </div>
          </div>

          <div className="flex flex-wrap md:flex-col items-start md:items-end gap-2 shrink-0">
            <StatusBadge status={complaint.status} size="lg" />
            <div className="flex items-center gap-1.5">
              <SeverityBadge
                level={complaint.severity_level}
                score={complaint.severity_score}
              />
              <PriorityBadge priority={complaint.priority} />
            </div>
          </div>
        </div>
      </div>

      {/* Lifecycle progress bar */}
      <StatusTimeline
        currentStatus={complaint.status}
        previousStatus={complaint.previous_status}
      />

      {/* Main Details Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column (2 Cols) */}
        <div className="lg:col-span-2 space-y-6">
          {/* Complaint description */}
          <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-xs">
            <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2 mb-3">
              <FileText className="w-4 h-4 text-brand-600" />
              Citizen Report
            </h3>
            <p className="text-sm text-slate-700 leading-relaxed bg-slate-50 p-4 rounded-lg border border-slate-100 whitespace-pre-wrap">
              {complaint.raw_text}
            </p>

            {complaint.structured_summary && (
              <div className="mt-4 pt-4 border-t border-slate-100">
                <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">
                  Structured AI Summary
                </h4>
                <p className="text-xs text-slate-800 font-medium">
                  {complaint.structured_summary}
                </p>
              </div>
            )}
          </div>

          {/* Severity & Priority Engine breakdown */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            {/* Severity factors */}
            <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-bold text-slate-900 flex items-center gap-1.5">
                  <Layers className="w-4 h-4 text-brand-600" />
                  Severity Engine
                </h3>
                <span className="font-mono text-xs font-bold text-slate-800 bg-slate-100 px-2 py-0.5 rounded">
                  Score {complaint.severity_score}/10
                </span>
              </div>

              <div className="space-y-2">
                {Array.isArray(complaint.severity_factors) ? (
                  complaint.severity_factors.map((f, i) => (
                    <div
                      key={i}
                      className="flex items-center justify-between text-xs p-2 rounded bg-slate-50 border border-slate-100"
                    >
                      <span className="text-slate-600 capitalize">
                        {f.factor || f.reason || 'Factor'}
                      </span>
                      <span className="font-mono font-semibold text-slate-900">
                        +{f.points || 0} pts
                      </span>
                    </div>
                  ))
                ) : typeof complaint.severity_factors === 'object' && complaint.severity_factors ? (
                  Object.entries(complaint.severity_factors).map(([k, v]) => (
                    <div
                      key={k}
                      className="flex items-center justify-between text-xs p-2 rounded bg-slate-50 border border-slate-100"
                    >
                      <span className="text-slate-600 capitalize">{k.replace(/_/g, ' ')}</span>
                      <span className="font-mono font-semibold text-slate-900">
                        {typeof v === 'boolean' ? (v ? 'Yes' : 'No') : String(v)}
                      </span>
                    </div>
                  ))
                ) : (
                  <p className="text-xs text-slate-400 italic">No factor breakdown provided</p>
                )}
              </div>
            </div>

            {/* Priority factors */}
            <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-bold text-slate-900 flex items-center gap-1.5">
                  <Clock className="w-4 h-4 text-brand-600" />
                  Priority & SLA
                </h3>
                <PriorityBadge priority={complaint.priority} size="sm" />
              </div>

              <div className="space-y-2 text-xs">
                {typeof complaint.priority_factors === 'object' &&
                complaint.priority_factors &&
                Object.keys(complaint.priority_factors).length > 0 ? (
                  Object.entries(complaint.priority_factors).map(([k, v]) => (
                    <div
                      key={k}
                      className="flex items-center justify-between p-2 rounded bg-slate-50 border border-slate-100"
                    >
                      <span className="text-slate-600 capitalize">{k.replace(/_/g, ' ')}</span>
                      <span className="font-mono font-semibold text-brand-700">
                        {typeof v === 'boolean' ? (v ? 'Active' : 'No') : String(v)}
                      </span>
                    </div>
                  ))
                ) : (
                  <p className="text-xs text-slate-400 italic p-2">Standard priority modifiers applied</p>
                )}

                {slaDate && (
                  <div className="mt-3 pt-2 border-t border-slate-100 text-xs">
                    <span className="text-slate-500">Initial SLA Deadline:</span>
                    <p className="font-mono font-semibold text-slate-800 mt-0.5">{slaDate}</p>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* AI Reasoning (rendered readably) */}
          <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs">
            <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2 mb-3">
              <Cpu className="w-4 h-4 text-purple-600" />
              AI Understanding & Decision Reasoning
            </h3>

            {complaint.ai_reasoning && Object.keys(complaint.ai_reasoning).length > 0 ? (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {Object.entries(complaint.ai_reasoning).map(([key, val]) => (
                  <div key={key} className="p-3 rounded-lg bg-purple-50/50 border border-purple-100 text-xs">
                    <span className="font-semibold text-purple-900 capitalize block mb-1">
                      {key.replace(/_/g, ' ')}
                    </span>
                    <span className="text-slate-700">
                      {Array.isArray(val)
                        ? val.join(', ')
                        : typeof val === 'object'
                        ? JSON.stringify(val)
                        : String(val)}
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-slate-400 italic">No AI reasoning payload logged.</p>
            )}
          </div>

          {/* Evidence gallery */}
          <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs">
            <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2 mb-3">
              <ImageIcon className="w-4 h-4 text-brand-600" />
              Evidence & Verification Media
            </h3>

            {complaint.evidence && complaint.evidence.length > 0 ? (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {complaint.evidence.map((ev) => {
                  const evType = (ev.type || '').toUpperCase();
                  const hasError = mediaErrors[ev.id];

                  return (
                    <div
                      key={ev.id}
                      className="p-3 rounded-xl border border-slate-200 bg-slate-50 flex flex-col justify-between gap-2.5"
                    >
                      <div className="flex items-center justify-between gap-1">
                        <span className="font-semibold text-slate-800 uppercase text-[10px] tracking-wider px-2 py-0.5 rounded bg-slate-200">
                          {ev.role}
                        </span>
                        <span className="text-slate-500 text-[11px] font-medium">{ev.type}</span>
                      </div>

                      {/* Render Media View */}
                      {hasError ? (
                        <div className="p-4 rounded-lg bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-center gap-2">
                          <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0" />
                          <span>Unable to load {evType.toLowerCase()} file</span>
                        </div>
                      ) : evType === 'IMAGE' ? (
                        <div className="relative group overflow-hidden rounded-lg border border-slate-200 bg-slate-100">
                          <img
                            src={ev.url || `/api/evidence/${ev.id}/file`}
                            alt={ev.file_path}
                            className="w-full h-40 object-cover cursor-pointer group-hover:scale-105 transition-transform duration-200"
                            onClick={() => setExpandedImage(ev.url || `/api/evidence/${ev.id}/file`)}
                            onError={() => setMediaErrors((prev) => ({ ...prev, [ev.id]: true }))}
                          />
                          <button
                            type="button"
                            onClick={() => setExpandedImage(ev.url || `/api/evidence/${ev.id}/file`)}
                            className="absolute bottom-2 right-2 p-1.5 rounded-md bg-black/60 text-white opacity-0 group-hover:opacity-100 transition-opacity text-xs flex items-center gap-1 cursor-pointer"
                          >
                            <Maximize2 className="w-3.5 h-3.5" />
                            Expand
                          </button>
                        </div>
                      ) : evType === 'AUDIO' ? (
                        <div className="p-2 rounded-lg bg-white border border-slate-200">
                          <div className="flex items-center gap-1.5 text-xs text-slate-600 mb-1.5">
                            <Volume2 className="w-4 h-4 text-brand-600" />
                            <span className="font-medium">Audio Recording</span>
                          </div>
                          <audio
                            controls
                            src={ev.url || `/api/evidence/${ev.id}/file`}
                            className="w-full h-10"
                            onError={() => setMediaErrors((prev) => ({ ...prev, [ev.id]: true }))}
                          />
                        </div>
                      ) : evType === 'VIDEO' ? (
                        <div className="rounded-lg overflow-hidden border border-slate-200 bg-black">
                          <video
                            controls
                            src={ev.url || `/api/evidence/${ev.id}/file`}
                            className="w-full max-h-48"
                            onError={() => setMediaErrors((prev) => ({ ...prev, [ev.id]: true }))}
                          />
                        </div>
                      ) : (
                        <div className="p-3 bg-white rounded border border-slate-200 text-xs">
                          <p className="font-mono text-slate-700 truncate">{ev.file_path}</p>
                        </div>
                      )}

                      <div className="text-[11px] text-slate-500 pt-1 border-t border-slate-200/60">
                        <p className="font-mono truncate">{ev.file_path}</p>
                        {ev.phash && (
                          <p className="font-mono text-[10px] text-slate-400 mt-0.5">phash: {ev.phash}</p>
                        )}
                        <p className="text-[10px] text-slate-400 mt-0.5">Uploaded by {ev.uploaded_by}</p>
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <p className="text-xs text-slate-400 italic">No media attachments recorded for this complaint.</p>
            )}
          </div>
        </div>

        {/* Right Column: Meta info & Audit Timeline */}
        <div className="space-y-6">
          {/* Metadata Card */}
          <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs text-xs space-y-3">
            <h3 className="font-bold text-slate-900 text-sm pb-2 border-b border-slate-100">
              Administrative Dossier
            </h3>

            <div>
              <span className="text-slate-400 block mb-0.5">Assigned Department</span>
              <span className="font-semibold text-slate-800 flex items-center gap-1.5">
                <Shield className="w-3.5 h-3.5 text-brand-600" />
                {deptName}
              </span>
            </div>

            <div>
              <span className="text-slate-400 block mb-0.5">Citizen Identity</span>
              <span className="font-semibold text-slate-800 flex items-center gap-1.5">
                <User className="w-3.5 h-3.5 text-slate-400" />
                {complaint.citizen_name}
              </span>
              <span className="text-slate-500 font-mono mt-0.5 block">
                {complaint.citizen_contact}
              </span>
            </div>

            <div>
              <span className="text-slate-400 block mb-0.5">Escalation Stage</span>
              <span className="font-semibold text-slate-800">
                Level {complaint.escalation_level || 0}
              </span>
            </div>

            {complaint.duplicate_count > 0 && (
              <div>
                <span className="text-slate-400 block mb-0.5">Linked Duplicates</span>
                <span className="font-semibold text-slate-800">
                  {complaint.duplicate_count} reports merged
                </span>
              </div>
            )}
          </div>

          {/* Audit Trail Timeline */}
          <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs">
            <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2 mb-4">
              <History className="w-4 h-4 text-brand-600" />
              Audit Trail (Newest Last)
            </h3>

            <AuditTimeline events={complaint.events || []} />
          </div>
        </div>
      </div>

      {/* Expanded Image Modal */}
      {expandedImage && (
        <div
          className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-4 backdrop-blur-xs"
          onClick={() => setExpandedImage(null)}
        >
          <div
            className="relative max-w-4xl max-h-[90vh] bg-slate-950 rounded-2xl overflow-hidden shadow-2xl border border-slate-800"
            onClick={(e) => e.stopPropagation()}
          >
            <button
              type="button"
              onClick={() => setExpandedImage(null)}
              className="absolute top-3 right-3 p-2 rounded-full bg-black/60 text-white hover:bg-black/80 transition-colors z-10 cursor-pointer"
              title="Close preview"
            >
              <X className="w-5 h-5" />
            </button>
            <img
              src={expandedImage}
              alt="Enlarged evidence preview"
              className="max-w-full max-h-[85vh] object-contain mx-auto"
            />
          </div>
        </div>
      )}
    </div>
  );
}
