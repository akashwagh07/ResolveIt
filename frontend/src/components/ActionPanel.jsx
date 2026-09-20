import React, { useState, useEffect, useRef } from 'react';
import {
  CheckCircle2,
  AlertTriangle,
  Clock,
  ArrowRight,
  UserCheck,
  RotateCcw,
  XCircle,
  ThumbsUp,
  ThumbsDown,
  Play,
  Check,
  X,
  Loader2,
  Info,
} from 'lucide-react';
import { getActions, runAction, getUsers } from '../lib/api';

const ACTION_ICONS = {
  accept: Check,
  confirm_classification: CheckCircle2,
  reject_out_of_scope: XCircle,
  assign: UserCheck,
  start_work: Play,
  approve_resolution: ThumbsUp,
  reject_resolution: ThumbsDown,
  confirm_resolution: CheckCircle2,
  dispute_resolution: RotateCcw,
  resume_work: Play,
  de_escalate: ArrowRight,
};

const ACTION_DESCRIPTIONS = {
  accept: 'Accept this complaint for formal review and allow department assignment.',
  confirm_classification: 'Confirm the category and priority so the complaint can be assigned to an officer.',
  reject_out_of_scope: 'Reject this complaint as non-civic or outside municipal jurisdiction.',
  assign: 'Assign this complaint to a field officer within the department.',
  start_work: 'Acknowledge assignment and mark this complaint as IN PROGRESS on site.',
  approve_resolution: 'Approve the resolution proof and ask the citizen to confirm the fix.',
  reject_resolution: 'Reject the resolution and send the complaint back to the officer to redo work.',
  confirm_resolution: 'Confirm that the issue was satisfactorily resolved in your neighborhood.',
  dispute_resolution: 'Dispute the repair if the issue remains unresolved or was fixed poorly.',
  resume_work: 'Resume work on this disputed complaint.',
  de_escalate: 'De-escalate this complaint back to its previous operational status.',
};

const ACTION_CONFIRMATIONS = {
  accept: 'Accept this complaint for formal municipal review?',
  confirm_classification: 'Confirm AI classification and mark ready for officer assignment?',
  start_work: 'Start active field repair work on this complaint?',
  approve_resolution: 'Approve the resolution and ask the citizen to confirm?',
  confirm_resolution: 'Confirm that this issue has been satisfactorily resolved in your neighborhood?',
  resume_work: 'Resume field work on this reopened complaint?',
  de_escalate: 'De-escalate this complaint back to its previous status?',
};

const STATUS_WAITING_EXPLANATIONS = {
  SUBMITTED: 'Analyzing report and determining civic relevance...',
  AI_ANALYZING: 'Multimodal AI is analyzing the complaint...',
  CLASSIFIED: 'Waiting for municipal supervisor to review and assign an officer.',
  UNDER_REVIEW: 'Under municipal review; waiting for officer assignment.',
  HUMAN_REVIEW: 'Low confidence or uncategorized issue; waiting for municipal supervisor to confirm classification or reject.',
  ASSIGNED: 'Waiting for the assigned officer to start work.',
  IN_PROGRESS: 'Officer is currently working on site. Waiting for resolution proof upload.',
  RESOLUTION_SUBMITTED: 'Resolution submitted; automated verification in progress.',
  AI_VERIFICATION: 'Verification in progress...',
  ADMIN_VERIFICATION: 'Work submitted; waiting for municipal supervisor to review before/after repair proof.',
  CITIZEN_CONFIRMATION: 'Waiting for the reporting citizen to confirm or dispute the resolution.',
  RESOLVED: 'Complaint has been successfully resolved and closed.',
  OUT_OF_SCOPE: 'Complaint was marked out of municipal scope.',
  REOPENED: 'Citizen disputed resolution; waiting for officer or admin to resume work.',
  ESCALATED: 'SLA breached; escalated to municipal leadership.',
};

export default function ActionPanel({ complaint, onActionSuccess, role }) {
  const [actions, setActions] = useState([]);
  const [loadingActions, setLoadingActions] = useState(true);
  const [runningAction, setRunningAction] = useState(null);
  const [actionError, setActionError] = useState('');
  const [actionSuccess, setActionSuccess] = useState('');

  // Modal State
  const [activeModalAction, setActiveModalAction] = useState(null);
  const [modalReason, setModalReason] = useState('');
  const [modalOfficerId, setModalOfficerId] = useState('');
  const [modalNote, setModalNote] = useState('');
  const [officers, setOfficers] = useState([]);
  const [loadingOfficers, setLoadingOfficers] = useState(false);

  const modalRef = useRef(null);

  const fetchAvailableActions = async () => {
    if (!complaint?.id) return;
    setLoadingActions(true);
    try {
      const data = await getActions(complaint.id);
      setActions(Array.isArray(data) ? data : []);
    } catch (err) {
      // Non-critical, could be 401 if unauthenticated
      setActions([]);
    } finally {
      setLoadingActions(false);
    }
  };

  useEffect(() => {
    fetchAvailableActions();
  }, [complaint?.id, complaint?.status, complaint?.assigned_officer_id]);

  // Load department officers if assign modal is opened
  useEffect(() => {
    if (activeModalAction?.action === 'assign') {
      setLoadingOfficers(true);
      getUsers('OFFICER')
        .then((users) => {
          const list = Array.isArray(users) ? users : [];
          // Filter to officers in complaint's department if complaint.department_id exists
          const deptOfficers = complaint?.department_id
            ? list.filter((u) => u.department_id === complaint.department_id)
            : list;

          setOfficers(deptOfficers.length > 0 ? deptOfficers : list);
          if (deptOfficers.length > 0) {
            setModalOfficerId(String(deptOfficers[0].id));
          } else if (list.length > 0) {
            setModalOfficerId(String(list[0].id));
          }
        })
        .catch(() => setOfficers([]))
        .finally(() => setLoadingOfficers(false));
    }
  }, [activeModalAction, complaint?.department_id]);

  // Handle ESC to close modal
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && activeModalAction && !runningAction) {
        closeModal();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [activeModalAction, runningAction]);

  const openModalForAction = (act) => {
    setActionError('');
    setActionSuccess('');
    setModalReason('');
    setModalNote('');
    setActiveModalAction(act);
  };

  const closeModal = () => {
    if (runningAction) return;
    setActiveModalAction(null);
    setModalReason('');
    setModalNote('');
  };

  const executeActionCall = async (actionName, params = {}) => {
    setRunningAction(actionName);
    setActionError('');
    setActionSuccess('');

    try {
      const result = await runAction(complaint.id, actionName, params);
      setActionSuccess(result.message || `Action ${actionName} executed successfully.`);
      closeModal();
      // Refetch parent complaint data and available actions
      if (onActionSuccess) {
        await onActionSuccess();
      }
      await fetchAvailableActions();
    } catch (err) {
      setActionError(err.message || `Failed to execute action ${actionName}`);
      // Refetch actions because state may have changed on 403 or 409
      await fetchAvailableActions();
      if (onActionSuccess) {
        onActionSuccess();
      }
    } finally {
      setRunningAction(null);
    }
  };

  const handleModalSubmit = (e) => {
    e.preventDefault();
    if (!activeModalAction) return;

    const act = activeModalAction.action;
    const params = {};

    if (act === 'assign') {
      const oid = parseInt(modalOfficerId, 10);
      if (!oid) {
        setActionError('Please select a valid field officer.');
        return;
      }
      params.officer_id = oid;
      if (modalNote.trim()) {
        params.note = modalNote.trim();
      }
    } else if (
      act === 'reject_resolution' ||
      act === 'dispute_resolution' ||
      act === 'reject_out_of_scope'
    ) {
      if (!modalReason.trim()) {
        setActionError('A reason is required to perform this action.');
        return;
      }
      params.reason = modalReason.trim();
    }

    executeActionCall(act, params);
  };

  const waitingMessage =
    STATUS_WAITING_EXPLANATIONS[complaint?.status] ||
    'No administrative actions currently available for your role.';

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs">
      <div className="flex items-center justify-between gap-3 mb-3">
        <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
          <span>Available Actions</span>
          {actions.length > 0 && (
            <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-brand-50 text-brand-700 border border-brand-200">
              {actions.length} ready
            </span>
          )}
        </h3>

        {runningAction && (
          <span className="inline-flex items-center gap-1.5 text-xs text-brand-600 font-medium">
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
            Executing...
          </span>
        )}
      </div>

      {actionSuccess && (
        <div className="mb-4 p-3 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
            <span>{actionSuccess}</span>
          </div>
          <button
            type="button"
            onClick={() => setActionSuccess('')}
            className="text-emerald-700 hover:text-emerald-900 font-bold ml-2 cursor-pointer"
          >
            &times;
          </button>
        </div>
      )}

      {actionError && (
        <div className="mb-4 p-3 rounded-lg bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0" />
            <span>{actionError}</span>
          </div>
          <button
            type="button"
            onClick={() => setActionError('')}
            className="text-rose-700 hover:text-rose-900 font-bold ml-2 cursor-pointer"
          >
            &times;
          </button>
        </div>
      )}

      {loadingActions ? (
        <div className="py-4 text-center text-xs text-slate-400 flex items-center justify-center gap-2">
          <Loader2 className="w-3.5 h-3.5 animate-spin" />
          Checking permitted actions...
        </div>
      ) : actions.length === 0 ? (
        <div className="p-3.5 rounded-lg bg-slate-50 border border-slate-100 flex items-start gap-2.5 text-xs text-slate-600">
          <Info className="w-4 h-4 text-slate-400 shrink-0 mt-0.5" />
          <div>
            <p className="font-medium text-slate-700">{waitingMessage}</p>
            <p className="text-[11px] text-slate-400 mt-0.5">
              Actions will update automatically when the complaint status changes.
            </p>
          </div>
        </div>
      ) : (
        <div className="flex flex-wrap gap-2.5">
          {actions.map((act) => {
            const Icon = ACTION_ICONS[act.action] || ArrowRight;
            const isDanger =
              act.action === 'reject_out_of_scope' ||
              act.action === 'reject_resolution' ||
              act.action === 'dispute_resolution';

            const buttonStyle = isDanger
              ? 'bg-rose-50 border-rose-200 text-rose-700 hover:bg-rose-100'
              : 'bg-brand-50 border-brand-200 text-brand-700 hover:bg-brand-100';

            return (
              <button
                key={act.action}
                type="button"
                disabled={Boolean(runningAction)}
                onClick={() => openModalForAction(act)}
                className={`inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg border text-xs font-semibold shadow-2xs transition-all disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer ${buttonStyle}`}
              >
                <Icon className="w-3.5 h-3.5 shrink-0" />
                <span>{act.label}</span>
              </button>
            );
          })}
        </div>
      )}

      {/* Accessible Action Modal */}
      {activeModalAction && (
        <div
          className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4 backdrop-blur-2xs"
          onClick={closeModal}
        >
          <div
            ref={modalRef}
            role="dialog"
            aria-modal="true"
            aria-labelledby="action-modal-title"
            className="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl border border-slate-200 text-left space-y-4 animate-in fade-in zoom-in-95 duration-150"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-start justify-between gap-3">
              <div>
                <h3 id="action-modal-title" className="text-base font-bold text-slate-900">
                  {activeModalAction.label}
                </h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  {ACTION_DESCRIPTIONS[activeModalAction.action] || 'Execute this action on the complaint.'}
                </p>
              </div>
              <button
                type="button"
                onClick={closeModal}
                disabled={Boolean(runningAction)}
                className="p-1 rounded-md text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleModalSubmit} className="space-y-4">
              {/* ASSIGN PARAMETERS */}
              {activeModalAction.action === 'assign' && (
                <div className="space-y-3 text-xs">
                  <div>
                    <label className="block font-semibold text-slate-700 mb-1">
                      Assign to Field Officer
                    </label>
                    {loadingOfficers ? (
                      <div className="p-2 text-slate-400 bg-slate-50 rounded border border-slate-200 animate-pulse">
                        Loading department officers...
                      </div>
                    ) : officers.length === 0 ? (
                      <p className="text-rose-600 font-medium">
                        No field officers found for this department.
                      </p>
                    ) : (
                      <select
                        value={modalOfficerId}
                        onChange={(e) => setModalOfficerId(e.target.value)}
                        required
                        className="w-full px-3 py-2 rounded-lg border border-slate-300 bg-white text-slate-800 focus:outline-none focus:ring-2 focus:ring-brand-500"
                      >
                        {officers.map((off) => (
                          <option key={off.id} value={off.id}>
                            {off.name} (Officer #{off.id})
                          </option>
                        ))}
                      </select>
                    )}
                  </div>

                  <div>
                    <label className="block font-semibold text-slate-700 mb-1">
                      Assignment Note (Optional)
                    </label>
                    <textarea
                      rows={2}
                      value={modalNote}
                      onChange={(e) => setModalNote(e.target.value)}
                      placeholder="e.g. Expedite due to school proximity"
                      className="w-full px-3 py-2 rounded-lg border border-slate-300 bg-white text-slate-800 focus:outline-none focus:ring-2 focus:ring-brand-500"
                    />
                  </div>
                </div>
              )}

              {/* REASON TEXTAREA (FOR REJECTIONS & DISPUTES) */}
              {(activeModalAction.action === 'reject_resolution' ||
                activeModalAction.action === 'dispute_resolution' ||
                activeModalAction.action === 'reject_out_of_scope') && (
                <div className="space-y-1.5 text-xs">
                  <label className="block font-semibold text-slate-700">
                    Reason for {activeModalAction.label} <span className="text-rose-600">*</span>
                  </label>
                  <textarea
                    rows={3}
                    required
                    value={modalReason}
                    onChange={(e) => setModalReason(e.target.value)}
                    placeholder={
                      activeModalAction.action === 'dispute_resolution'
                        ? 'Describe why the fix is unsatisfactory or what remains broken...'
                        : 'Provide specific reasons for this decision...'
                    }
                    className="w-full px-3 py-2 rounded-lg border border-slate-300 bg-white text-slate-800 focus:outline-none focus:ring-2 focus:ring-brand-500"
                  />
                  <p className="text-[11px] text-slate-400">
                    This reason will be recorded in the append-only audit log.
                  </p>
                </div>
              )}

              {/* SIMPLE CONFIRMATION PROMPT */}
              {activeModalAction.action !== 'assign' &&
                activeModalAction.action !== 'reject_resolution' &&
                activeModalAction.action !== 'dispute_resolution' &&
                activeModalAction.action !== 'reject_out_of_scope' && (
                  <div className="p-3 rounded-lg bg-slate-50 border border-slate-100 text-xs text-slate-700">
                    <p className="font-semibold text-slate-900 mb-0.5">Please confirm:</p>
                    <p>
                      {ACTION_CONFIRMATIONS[activeModalAction.action] ||
                        `Are you sure you want to ${activeModalAction.label.toLowerCase()}?`}
                    </p>
                  </div>
                )}

              <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-100">
                <button
                  type="button"
                  onClick={closeModal}
                  disabled={Boolean(runningAction)}
                  className="px-3.5 py-2 text-xs font-semibold rounded-lg text-slate-600 hover:bg-slate-100 transition-colors cursor-pointer"
                >
                  Cancel
                </button>

                <button
                  type="submit"
                  disabled={Boolean(runningAction)}
                  className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-semibold rounded-lg bg-brand-600 hover:bg-brand-700 text-white shadow-xs transition-colors cursor-pointer disabled:bg-slate-300"
                >
                  {runningAction ? (
                    <>
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      Executing...
                    </>
                  ) : (
                    <span>Confirm & Execute</span>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
