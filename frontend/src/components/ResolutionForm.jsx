import React, { useState, useRef } from 'react';
import { Camera, Upload, X, CheckCircle2, AlertTriangle, Loader2, Image as ImageIcon } from 'lucide-react';
import { submitResolution } from '../lib/api';

const MAX_FILES = 4;
const MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024; // 10 MB

export default function ResolutionForm({ complaint, onResolutionSuccess }) {
  const [description, setDescription] = useState('');
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [previews, setPreviews] = useState([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const fileInputRef = useRef(null);

  // Original before evidence from complaint
  const beforeEvidence = (complaint?.evidence || []).filter(
    (ev) => ev.role === 'COMPLAINT' && ev.type === 'IMAGE'
  );

  const handleFileChange = (e) => {
    setError('');
    const files = Array.from(e.target.files || []);
    if (!files.length) return;

    if (selectedFiles.length + files.length > MAX_FILES) {
      setError(`You can attach a maximum of ${MAX_FILES} resolution photos.`);
      return;
    }

    const validNewFiles = [];
    const newPreviews = [];

    for (const file of files) {
      if (!file.type.startsWith('image/')) {
        setError(`File "${file.name}" is not a supported image.`);
        return;
      }
      if (file.size > MAX_FILE_SIZE_BYTES) {
        setError(`File "${file.name}" exceeds the 10 MB limit (${(file.size / (1024 * 1024)).toFixed(1)} MB).`);
        return;
      }
      validNewFiles.push(file);
      newPreviews.push(URL.createObjectURL(file));
    }

    setSelectedFiles((prev) => [...prev, ...validNewFiles]);
    setPreviews((prev) => [...prev, ...newPreviews]);

    // Reset input so re-selecting same file triggers change
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const removeFile = (index) => {
    // Revoke object URL
    URL.revokeObjectURL(previews[index]);
    setSelectedFiles((prev) => prev.filter((_, i) => i !== index));
    setPreviews((prev) => prev.filter((_, i) => i !== index));
    setError('');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    const trimmedDesc = description.trim();
    if (trimmedDesc.length < 10) {
      setError('Description must be at least 10 characters detailing the work completed.');
      return;
    }
    if (trimmedDesc.length > 1000) {
      setError('Description cannot exceed 1000 characters.');
      return;
    }

    if (selectedFiles.length < 1) {
      setError('At least 1 photo proving site repair is required.');
      return;
    }
    if (selectedFiles.length > MAX_FILES) {
      setError(`At most ${MAX_FILES} photos can be submitted.`);
      return;
    }

    setIsSubmitting(true);
    try {
      const formData = new FormData();
      formData.append('description', trimmedDesc);
      for (const file of selectedFiles) {
        formData.append('after_images', file);
      }

      await submitResolution(complaint.id, formData);
      setSuccess('Resolution submitted for verification! Work has transitioned to review.');
      setSelectedFiles([]);
      setPreviews([]);
      setDescription('');

      if (onResolutionSuccess) {
        await onResolutionSuccess();
      }
    } catch (err) {
      setError(err.message || 'Failed to submit resolution evidence.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="bg-white rounded-2xl border border-brand-200 p-6 shadow-sm space-y-6">
      <div className="flex items-center justify-between border-b border-slate-100 pb-3">
        <div>
          <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
            <Camera className="w-5 h-5 text-brand-600" />
            Field Resolution Proof & Work Completion
          </h3>
          <p className="text-xs text-slate-500 mt-0.5">
            Submit photographic evidence of completed repair work for AI and administrative verification.
          </p>
        </div>
        <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-blue-50 text-blue-700 border border-blue-200">
          Status: IN PROGRESS
        </span>
      </div>

      {success && (
        <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs flex items-center gap-2.5">
          <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
          <span className="font-semibold">{success}</span>
        </div>
      )}

      {error && (
        <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-center gap-2.5">
          <AlertTriangle className="w-5 h-5 text-rose-600 shrink-0" />
          <span className="font-medium">{error}</span>
        </div>
      )}

      {/* Two column layout: Original reference on left/top, upload form on right */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Reference Column: Original Complaint Photo */}
        <div className="lg:col-span-1 bg-slate-50 rounded-xl p-4 border border-slate-200 space-y-3">
          <div className="flex items-center gap-1.5 text-xs font-bold text-slate-700">
            <ImageIcon className="w-4 h-4 text-slate-500" />
            Original Before Evidence (Reference)
          </div>

          {beforeEvidence.length > 0 ? (
            <div className="space-y-2">
              {beforeEvidence.map((ev) => (
                <div key={ev.id} className="overflow-hidden rounded-lg border border-slate-200 bg-white">
                  <img
                    src={ev.url || `/api/evidence/${ev.id}/file`}
                    alt="Original issue reference"
                    className="w-full h-36 object-cover"
                  />
                  <div className="p-1.5 text-[10px] text-slate-500 font-mono text-center">
                    Original Citizen Upload
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-xs text-slate-400 italic">
              No before images were submitted with the original report.
            </p>
          )}

          <div className="text-[11px] text-slate-500 leading-relaxed pt-2 border-t border-slate-200">
            <span className="font-semibold text-slate-700">Tip for Officers:</span> Ensure your repair photos capture the exact same angle and landmark location for smooth verification.
          </div>
        </div>

        {/* Upload Form Column */}
        <form onSubmit={handleSubmit} className="lg:col-span-2 space-y-4 text-xs">
          {/* Work Description */}
          <div>
            <div className="flex items-center justify-between mb-1">
              <label className="font-semibold text-slate-700">
                Resolution Work Summary <span className="text-rose-600">*</span>
              </label>
              <span className={`text-[11px] font-mono ${description.length < 10 || description.length > 1000 ? 'text-amber-600 font-bold' : 'text-slate-400'}`}>
                {description.length} / 1000 chars (min 10)
              </span>
            </div>
            <textarea
              rows={3}
              required
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Detail the repair actions taken (e.g., Pothole filled with hot asphalt mix, compacted with roller, and barricades removed)..."
              className="w-full p-3 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-brand-500 bg-white text-slate-800"
            />
          </div>

          {/* After Photos Upload */}
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="font-semibold text-slate-700">
                After-Repair Proof Photos <span className="text-rose-600">*</span> (1 to 4 photos, up to 10 MB each)
              </label>
              <span className="text-[11px] text-slate-400 font-mono">
                {selectedFiles.length} / {MAX_FILES} attached
              </span>
            </div>

            {/* Photo Previews Grid */}
            {previews.length > 0 && (
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-3">
                {previews.map((src, index) => (
                  <div key={index} className="relative group rounded-lg overflow-hidden border border-slate-200 bg-slate-100">
                    <img src={src} alt={`After repair ${index + 1}`} className="w-full h-24 object-cover" />
                    <button
                      type="button"
                      onClick={() => removeFile(index)}
                      className="absolute top-1.5 right-1.5 p-1 rounded-full bg-black/70 text-white hover:bg-rose-600 transition-colors cursor-pointer"
                      title="Remove image"
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                    <div className="absolute bottom-0 inset-x-0 bg-black/60 px-1 py-0.5 text-[9px] text-white font-mono text-center truncate">
                      {selectedFiles[index]?.name}
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* File Input Area */}
            {selectedFiles.length < MAX_FILES && (
              <div
                onClick={() => fileInputRef.current?.click()}
                className="border-2 border-dashed border-slate-300 hover:border-brand-500 rounded-xl p-4 text-center bg-slate-50/50 hover:bg-brand-50/30 transition-colors cursor-pointer"
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/*"
                  capture="environment"
                  multiple
                  onChange={handleFileChange}
                  className="hidden"
                />
                <Camera className="w-6 h-6 text-slate-400 mx-auto mb-1" />
                <p className="font-semibold text-slate-700">Take photo or upload repair proof</p>
                <p className="text-[11px] text-slate-400 mt-0.5">JPEG, PNG, WebP up to 10 MB each</p>
              </div>
            )}
          </div>

          <div className="pt-2 flex items-center justify-end">
            <button
              type="submit"
              disabled={isSubmitting || selectedFiles.length === 0 || description.trim().length < 10}
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-brand-600 hover:bg-brand-700 disabled:bg-slate-300 text-white font-semibold text-xs shadow-sm transition-all cursor-pointer"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Uploading proof & running checks...
                </>
              ) : (
                <>
                  <Upload className="w-4 h-4" />
                  Submit for Verification
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
