import React, { useState, useRef, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  Camera,
  Video,
  FileText,
  AlertCircle,
  ArrowLeft,
  Send,
  Trash2,
  CheckCircle2,
  Globe2,
} from 'lucide-react';
import { useAuth } from '../lib/auth';
import { createComplaint } from '../lib/api';
import LocationPicker from '../components/LocationPicker';
import VoiceRecorder from '../components/VoiceRecorder';
import SubmissionProgress from '../components/SubmissionProgress';
import ResultPanel from '../components/ResultPanel';

const MAX_IMAGE_BYTES = 10 * 1024 * 1024; // 10 MB
const MAX_VIDEO_BYTES = 15 * 1024 * 1024; // 15 MB
const MAX_DESCRIPTION_CHARS = 1000;

export default function ReportIssuePage() {
  const { session } = useAuth();

  // Form State
  const [citizenName, setCitizenName] = useState(session?.citizenName || 'Rahul Deshmukh');
  const [citizenContact, setCitizenContact] = useState(session?.citizenContact || '+91 9822012345');
  const [description, setDescription] = useState('');
  const [language, setLanguage] = useState('auto'); // 'auto' | 'en' | 'hi' | 'mr'
  const [photoFile, setPhotoFile] = useState(null);
  const [photoPreview, setPhotoPreview] = useState(null);
  const [audioFile, setAudioFile] = useState(null);
  const [videoFile, setVideoFile] = useState(null);
  const [latitude, setLatitude] = useState(16.705);
  const [longitude, setLongitude] = useState(74.2433);
  const [addressText, setAddressText] = useState('');

  // UI / Status State
  const [errors, setErrors] = useState({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState(null);
  const [result, setResult] = useState(null);

  // AbortController for cancel
  const abortControllerRef = useRef(null);

  // Section Refs for scroll-to-first-error
  const nameRef = useRef(null);
  const contactRef = useRef(null);
  const descRef = useRef(null);
  const photoRef = useRef(null);
  const videoRef = useRef(null);
  const locationRef = useRef(null);

  // Photo preview lifecycle
  useEffect(() => {
    if (!photoFile) {
      if (photoPreview) {
        URL.revokeObjectURL(photoPreview);
        setPhotoPreview(null);
      }
    } else {
      const url = URL.createObjectURL(photoFile);
      setPhotoPreview(url);
      return () => {
        URL.revokeObjectURL(url);
      };
    }
  }, [photoFile]);

  // Update prefilled values when session changes if fields are untouched
  useEffect(() => {
    if (session?.citizenName && !description && !photoFile && !audioFile && !videoFile) {
      setCitizenName(session.citizenName);
    }
    if (session?.citizenContact && !description && !photoFile && !audioFile && !videoFile) {
      setCitizenContact(session.citizenContact);
    }
  }, [session]);

  const handlePhotoSelect = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (file.size > MAX_IMAGE_BYTES) {
      const mb = (file.size / (1024 * 1024)).toFixed(1);
      setErrors((prev) => ({
        ...prev,
        photo: `Photo exceeds the 10 MB limit (${mb} MB). Please choose a smaller image.`,
      }));
      e.target.value = '';
      return;
    }

    setErrors((prev) => {
      const copy = { ...prev };
      delete copy.photo;
      delete copy.content;
      return copy;
    });
    setPhotoFile(file);
  };

  const handleRemovePhoto = () => {
    setPhotoFile(null);
    setErrors((prev) => {
      const copy = { ...prev };
      delete copy.photo;
      return copy;
    });
  };

  const handleVideoSelect = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (file.size > MAX_VIDEO_BYTES) {
      const mb = (file.size / (1024 * 1024)).toFixed(1);
      setErrors((prev) => ({
        ...prev,
        video: `Video exceeds the 15 MB limit (${mb} MB). Short clips under 15MB work best.`,
      }));
      e.target.value = '';
      return;
    }

    setErrors((prev) => {
      const copy = { ...prev };
      delete copy.video;
      delete copy.content;
      return copy;
    });
    setVideoFile(file);
  };

  const handleRemoveVideo = () => {
    setVideoFile(null);
    setErrors((prev) => {
      const copy = { ...prev };
      delete copy.video;
      return copy;
    });
  };

  const validateForm = () => {
    const newErrors = {};

    if (!citizenName.trim()) {
      newErrors.name = 'Full name is required.';
    }

    if (!citizenContact.trim()) {
      newErrors.contact = 'Contact phone number is required.';
    }

    if (latitude === null || latitude === undefined || longitude === null || longitude === undefined) {
      newErrors.location = 'Please select a location on the map.';
    }

    const hasText = description.trim().length > 0;
    const hasMedia = Boolean(photoFile || audioFile || videoFile);
    if (!hasText && !hasMedia) {
      newErrors.content = 'Please provide an issue description, photo, or audio voice note.';
    }

    setErrors(newErrors);

    // Scroll to the first error
    if (newErrors.name && nameRef.current) {
      nameRef.current.scrollIntoView({ behavior: 'smooth', block: 'center' });
    } else if (newErrors.contact && contactRef.current) {
      contactRef.current.scrollIntoView({ behavior: 'smooth', block: 'center' });
    } else if (newErrors.content && descRef.current) {
      descRef.current.scrollIntoView({ behavior: 'smooth', block: 'center' });
    } else if (newErrors.location && locationRef.current) {
      locationRef.current.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }

    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitError(null);

    if (!validateForm()) {
      return;
    }

    setIsSubmitting(true);
    const controller = new AbortController();
    abortControllerRef.current = controller;

    try {
      const formData = new FormData();
      formData.append('citizen_name', citizenName.trim());
      formData.append('citizen_contact', citizenContact.trim());
      formData.append('latitude', String(latitude));
      formData.append('longitude', String(longitude));

      if (description.trim()) {
        formData.append('text', description.trim());
      }

      // Omit language if Auto
      if (language && language !== 'auto') {
        formData.append('language', language);
      }

      // Omit empty address
      if (addressText.trim()) {
        formData.append('address_text', addressText.trim());
      }

      if (photoFile) {
        formData.append('image', photoFile);
      }

      if (audioFile) {
        formData.append('audio', audioFile);
      }

      if (videoFile) {
        formData.append('video', videoFile);
      }

      const response = await createComplaint(formData, { signal: controller.signal });
      setResult(response);
    } catch (err) {
      setSubmitError(err.message || 'Failed to submit complaint. Please try again.');
    } finally {
      setIsSubmitting(false);
      abortControllerRef.current = null;
    }
  };

  const handleCancelSubmission = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
  };

  const handleResetForm = () => {
    setResult(null);
    setDescription('');
    setLanguage('auto');
    setPhotoFile(null);
    setAudioFile(null);
    setVideoFile(null);
    setAddressText('');
    setLatitude(16.705);
    setLongitude(74.2433);
    setErrors({});
    setSubmitError(null);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  // If a result is available, render ResultPanel replacing the form
  if (result) {
    return (
      <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-4">
          <Link
            to="/citizen"
            className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-500 hover:text-slate-800 transition-colors"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            Back to complaints
          </Link>
        </div>
        <ResultPanel
          result={result}
          citizenName={citizenName}
          citizenContact={citizenContact}
          onReset={handleResetForm}
        />
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header */}
      <div className="mb-6">
        <Link
          to="/citizen"
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-500 hover:text-slate-800 transition-colors mb-3"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          Back to complaints
        </Link>
        <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
          Report a Civic Issue
        </h1>
        <p className="text-xs sm:text-sm text-slate-500 mt-1">
          Submit photos, voice notes, or text description. Our multimodal AI will classify, assess severity, and route it to the right department.
        </p>
      </div>

      {/* Submitting in progress screen */}
      {isSubmitting ? (
        <SubmissionProgress onCancel={handleCancelSubmission} />
      ) : (
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Submission error alert */}
          {submitError && (
            <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 flex items-start gap-3 text-rose-900 text-xs">
              <AlertCircle className="w-5 h-5 text-rose-600 shrink-0 mt-0.5" />
              <div className="flex-1">
                <span className="font-semibold block mb-0.5">Submission Error</span>
                <p>{submitError}</p>
              </div>
            </div>
          )}

          {/* Citizen Details Card */}
          <div className="bg-white rounded-2xl border border-slate-200 p-5 sm:p-6 shadow-2xs space-y-4">
            <h2 className="text-xs font-bold uppercase tracking-wider text-slate-400">
              Reporter Details
            </h2>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div ref={nameRef}>
                <label className="block text-xs font-semibold text-slate-800 mb-1">
                  Full Name <span className="text-rose-500">*</span>
                </label>
                <input
                  type="text"
                  required
                  disabled={isSubmitting}
                  value={citizenName}
                  onChange={(e) => {
                    setCitizenName(e.target.value);
                    if (errors.name) {
                      setErrors((p) => {
                        const copy = { ...p };
                        delete copy.name;
                        return copy;
                      });
                    }
                  }}
                  placeholder="e.g. Rahul Deshmukh"
                  className={`w-full px-3 py-2 text-xs rounded-lg border ${
                    errors.name ? 'border-rose-400 ring-1 ring-rose-200' : 'border-slate-300'
                  } focus:outline-none focus:ring-2 focus:ring-brand-500 bg-white`}
                />
                {errors.name && (
                  <p className="text-[11px] text-rose-600 mt-1">{errors.name}</p>
                )}
              </div>

              <div ref={contactRef}>
                <label className="block text-xs font-semibold text-slate-800 mb-1">
                  Contact Phone <span className="text-rose-500">*</span>
                </label>
                <input
                  type="text"
                  required
                  disabled={isSubmitting}
                  value={citizenContact}
                  onChange={(e) => {
                    setCitizenContact(e.target.value);
                    if (errors.contact) {
                      setErrors((p) => {
                        const copy = { ...p };
                        delete copy.contact;
                        return copy;
                      });
                    }
                  }}
                  placeholder="e.g. +91 9822012345"
                  className={`w-full px-3 py-2 text-xs rounded-lg border ${
                    errors.contact ? 'border-rose-400 ring-1 ring-rose-200' : 'border-slate-300'
                  } focus:outline-none focus:ring-2 focus:ring-brand-500 bg-white`}
                />
                {errors.contact && (
                  <p className="text-[11px] text-rose-600 mt-1">{errors.contact}</p>
                )}
              </div>
            </div>
          </div>

          {/* Issue Content Card */}
          <div className="bg-white rounded-2xl border border-slate-200 p-5 sm:p-6 shadow-2xs space-y-6">
            <h2 className="text-xs font-bold uppercase tracking-wider text-slate-400">
              Issue Evidence & Description
            </h2>

            {/* Description Textarea */}
            <div ref={descRef}>
              <div className="flex items-center justify-between mb-1.5">
                <label className="text-xs font-semibold text-slate-800 flex items-center gap-1.5">
                  <FileText className="w-4 h-4 text-brand-600" />
                  Description{' '}
                  <span className="text-slate-400 font-normal">
                    (optional if photo or audio is provided)
                  </span>
                </label>
                <span
                  className={`text-[11px] font-mono ${
                    description.length >= MAX_DESCRIPTION_CHARS
                      ? 'text-rose-600 font-bold'
                      : 'text-slate-400'
                  }`}
                >
                  {description.length}/{MAX_DESCRIPTION_CHARS}
                </span>
              </div>

              <textarea
                rows={4}
                disabled={isSubmitting}
                maxLength={MAX_DESCRIPTION_CHARS}
                value={description}
                onChange={(e) => {
                  setDescription(e.target.value);
                  if (errors.content) {
                    setErrors((p) => {
                      const copy = { ...p };
                      delete copy.content;
                      return copy;
                    });
                  }
                }}
                placeholder="e.g. Deep dangerous pothole on main Shivaji Road causing traffic slowdown / मुख्य रस्त्यावरील बस स्थानकाजवळ पाण्याची पाईपलाईन फुटून पाणी वाहत आहे..."
                className={`w-full px-3 py-2.5 text-xs rounded-xl border ${
                  errors.content ? 'border-rose-400 ring-1 ring-rose-200' : 'border-slate-300'
                } focus:outline-none focus:ring-2 focus:ring-brand-500 bg-white resize-none`}
              />

              {/* Language Selector */}
              <div className="flex items-center justify-between mt-2">
                <div className="flex items-center gap-2">
                  <Globe2 className="w-3.5 h-3.5 text-slate-400" />
                  <span className="text-xs text-slate-600 font-medium">Input Language:</span>
                  <select
                    disabled={isSubmitting}
                    value={language}
                    onChange={(e) => setLanguage(e.target.value)}
                    className="text-xs rounded-lg border border-slate-300 px-2 py-1 bg-white text-slate-700 focus:outline-none focus:ring-2 focus:ring-brand-500"
                  >
                    <option value="auto">Auto (Detect)</option>
                    <option value="en">English</option>
                    <option value="hi">Hindi (हिंदी)</option>
                    <option value="mr">Marathi (मराठी)</option>
                  </select>
                </div>
                <span className="text-[10px] text-slate-400">
                  Marathi & Hindi vernacular supported
                </span>
              </div>

              {errors.content && (
                <p className="text-xs text-rose-600 font-medium flex items-center gap-1 mt-2">
                  <AlertCircle className="w-3.5 h-3.5" />
                  {errors.content}
                </p>
              )}
            </div>

            {/* Photo Upload Section */}
            <div ref={photoRef} className="space-y-2">
              <label className="text-xs font-semibold text-slate-800 flex items-center gap-1.5">
                <Camera className="w-4 h-4 text-brand-600" />
                Photo Evidence <span className="text-slate-400 font-normal">(optional, max 10 MB)</span>
              </label>

              {!photoFile ? (
                <div>
                  <label className="border-2 border-dashed border-slate-200 hover:border-slate-300 rounded-xl p-5 flex flex-col items-center justify-center bg-slate-50 hover:bg-slate-100/60 transition-colors cursor-pointer">
                    <Camera className="w-6 h-6 text-slate-400 mb-1.5" />
                    <span className="text-xs font-semibold text-slate-700">
                      Take photo or select image
                    </span>
                    <span className="text-[11px] text-slate-400 mt-0.5">
                      Opens camera on phones &bull; JPG, PNG, WEBP up to 10 MB
                    </span>
                    <input
                      type="file"
                      accept="image/*"
                      capture="environment"
                      disabled={isSubmitting}
                      onChange={handlePhotoSelect}
                      className="hidden"
                    />
                  </label>
                </div>
              ) : (
                <div className="p-3 rounded-xl border border-slate-200 bg-slate-50 flex items-center gap-4">
                  {photoPreview && (
                    <img
                      src={photoPreview}
                      alt="Complaint preview"
                      className="w-16 h-16 object-cover rounded-lg border border-slate-200"
                    />
                  )}
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-semibold text-slate-800 truncate">
                      {photoFile.name}
                    </p>
                    <p className="text-[11px] text-slate-500">
                      {(photoFile.size / (1024 * 1024)).toFixed(2)} MB
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={handleRemovePhoto}
                    disabled={isSubmitting}
                    className="p-2 rounded-lg border border-rose-200 text-rose-600 hover:bg-rose-50 text-xs font-medium cursor-pointer"
                    title="Remove photo"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              )}

              {errors.photo && (
                <p className="text-xs text-rose-600 font-medium flex items-center gap-1">
                  <AlertCircle className="w-3.5 h-3.5" />
                  {errors.photo}
                </p>
              )}
            </div>

            {/* Voice Recorder Component */}
            <VoiceRecorder
              audioFile={audioFile}
              onAudioChange={(file) => {
                setAudioFile(file);
                if (file && errors.content) {
                  setErrors((p) => {
                    const copy = { ...p };
                    delete copy.content;
                    return copy;
                  });
                }
              }}
            />

            {/* Video Upload Section */}
            <div ref={videoRef} className="space-y-2">
              <label className="text-xs font-semibold text-slate-800 flex items-center gap-1.5">
                <Video className="w-4 h-4 text-brand-600" />
                Video Clip <span className="text-slate-400 font-normal">(optional, max 15 MB)</span>
              </label>

              {!videoFile ? (
                <div>
                  <label className="border-2 border-dashed border-slate-200 hover:border-slate-300 rounded-xl p-4 flex flex-col items-center justify-center bg-slate-50 hover:bg-slate-100/60 transition-colors cursor-pointer">
                    <Video className="w-6 h-6 text-slate-400 mb-1" />
                    <span className="text-xs font-semibold text-slate-700">
                      Upload short video clip
                    </span>
                    <span className="text-[11px] text-slate-400 mt-0.5">
                      MP4, MOV, WEBM &bull; Short 5–15 sec clips work best
                    </span>
                    <input
                      type="file"
                      accept=".mp4,.mov,.webm,video/*"
                      disabled={isSubmitting}
                      onChange={handleVideoSelect}
                      className="hidden"
                    />
                  </label>
                </div>
              ) : (
                <div className="p-3 rounded-xl border border-slate-200 bg-slate-50 flex items-center justify-between gap-3 text-xs">
                  <div className="flex items-center gap-2 truncate">
                    <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                    <span className="font-semibold text-slate-800 truncate">{videoFile.name}</span>
                    <span className="text-slate-400 shrink-0">
                      ({(videoFile.size / (1024 * 1024)).toFixed(2)} MB)
                    </span>
                  </div>
                  <button
                    type="button"
                    onClick={handleRemoveVideo}
                    disabled={isSubmitting}
                    className="p-1.5 rounded border border-rose-200 text-rose-600 hover:bg-rose-50 cursor-pointer"
                    title="Remove video"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              )}

              {errors.video && (
                <p className="text-xs text-rose-600 font-medium flex items-center gap-1">
                  <AlertCircle className="w-3.5 h-3.5" />
                  {errors.video}
                </p>
              )}
            </div>
          </div>

          {/* Location Card */}
          <div
            ref={locationRef}
            className="bg-white rounded-2xl border border-slate-200 p-5 sm:p-6 shadow-2xs"
          >
            <LocationPicker
              latitude={latitude}
              longitude={longitude}
              onLocationChange={(lat, lng) => {
                setLatitude(lat);
                setLongitude(lng);
                if (errors.location) {
                  setErrors((p) => {
                    const copy = { ...p };
                    delete copy.location;
                    return copy;
                  });
                }
              }}
              addressText={addressText}
              onAddressChange={setAddressText}
              error={errors.location}
            />
          </div>

          {/* Submit Action Card */}
          <div className="p-5 rounded-2xl bg-white border border-slate-200 shadow-sm flex flex-col sm:flex-row items-center justify-between gap-4">
            <div className="text-xs text-slate-500 text-center sm:text-left">
              <span>By submitting, your report will be triaged autonomously by ResolveIt.</span>
            </div>

            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-6 py-3 rounded-xl bg-brand-600 hover:bg-brand-700 text-white font-bold text-xs shadow-md hover:shadow-lg disabled:opacity-50 transition-all cursor-pointer"
            >
              <Send className="w-4 h-4" />
              Submit Complaint
            </button>
          </div>
        </form>
      )}
    </div>
  );
}
