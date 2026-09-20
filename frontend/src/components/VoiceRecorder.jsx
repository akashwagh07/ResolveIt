import React, { useState, useRef, useEffect } from 'react';
import { Mic, Square, RotateCcw, Upload, Volume2, AlertCircle, Trash2, CheckCircle2 } from 'lucide-react';
import { convertBlobToWav } from '../lib/wav';

const MAX_AUDIO_BYTES = 15 * 1024 * 1024; // 15 MB

export default function VoiceRecorder({ audioFile, onAudioChange }) {
  const [mode, setMode] = useState('record'); // 'record' | 'upload'
  const [isRecording, setIsRecording] = useState(false);
  const [timerSeconds, setTimerSeconds] = useState(0);
  const [converting, setConverting] = useState(false);
  const [audioUrl, setAudioUrl] = useState(null);
  const [micError, setMicError] = useState(null);
  const [uploadError, setUploadError] = useState(null);

  const mediaRecorderRef = useRef(null);
  const timerIntervalRef = useRef(null);
  const audioChunksRef = useRef([]);
  const streamRef = useRef(null);
  const fileInputRef = useRef(null);

  // Synchronize audio preview URL with external audioFile prop
  useEffect(() => {
    if (!audioFile) {
      if (audioUrl) {
        URL.revokeObjectURL(audioUrl);
        setAudioUrl(null);
      }
    } else {
      const url = URL.createObjectURL(audioFile);
      setAudioUrl(url);
      return () => {
        URL.revokeObjectURL(url);
      };
    }
  }, [audioFile]);

  // Clean up media streams and intervals on unmount
  useEffect(() => {
    return () => {
      if (timerIntervalRef.current) clearInterval(timerIntervalRef.current);
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((t) => t.stop());
      }
    };
  }, []);

  const formatTimer = (secs) => {
    const m = Math.floor(secs / 60);
    const s = secs % 60;
    return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
  };

  const startRecording = async () => {
    setMicError(null);
    setUploadError(null);

    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      setMicError(
        'Microphone recording is not supported in this browser or requires a secure origin (localhost or HTTPS).'
      );
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = async () => {
        setIsRecording(false);
        if (timerIntervalRef.current) {
          clearInterval(timerIntervalRef.current);
          timerIntervalRef.current = null;
        }

        // Release microphone stream
        if (streamRef.current) {
          streamRef.current.getTracks().forEach((t) => t.stop());
          streamRef.current = null;
        }

        const rawBlob = new Blob(audioChunksRef.current, {
          type: mediaRecorder.mimeType || 'audio/webm',
        });

        if (rawBlob.size === 0) {
          setMicError('No audio recorded. Please try again.');
          return;
        }

        try {
          setConverting(true);
          const wavFile = await convertBlobToWav(rawBlob);
          setConverting(false);
          onAudioChange(wavFile);
        } catch (err) {
          setConverting(false);
          setMicError(`Audio processing error: ${err.message}. You can still upload a sound file.`);
        }
      };

      mediaRecorder.start(250); // Collect data chunks every 250ms
      setIsRecording(true);
      setTimerSeconds(0);

      timerIntervalRef.current = setInterval(() => {
        setTimerSeconds((prev) => {
          if (prev >= 59) {
            // Cap at 60 seconds
            if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
              mediaRecorderRef.current.stop();
            }
            return 60;
          }
          return prev + 1;
        });
      }, 1000);
    } catch (err) {
      if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
        setMicError('Microphone permission was denied. Please allow microphone access or upload an audio file.');
      } else {
        setMicError(`Could not access microphone (${err.message}). You can upload an audio file instead.`);
      }
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
      mediaRecorderRef.current.stop();
    }
  };

  const handleFileUpload = (e) => {
    setUploadError(null);
    const file = e.target.files?.[0];
    if (!file) return;

    if (file.size > MAX_AUDIO_BYTES) {
      const mb = (file.size / (1024 * 1024)).toFixed(1);
      setUploadError(`Audio file exceeds the 15 MB limit (file size: ${mb} MB).`);
      e.target.value = '';
      return;
    }

    // Setting an uploaded file clears any recorded voice note
    onAudioChange(file);
  };

  const handleRemove = () => {
    if (isRecording) {
      stopRecording();
    }
    setTimerSeconds(0);
    setMicError(null);
    setUploadError(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
    onAudioChange(null);
  };

  return (
    <div className="space-y-3">
      {/* Mode toggle */}
      <div className="flex items-center justify-between">
        <label className="text-xs font-semibold text-slate-800 flex items-center gap-1.5">
          <Volume2 className="w-4 h-4 text-brand-600" />
          Voice Note (Audio) <span className="text-slate-400 font-normal">(optional)</span>
        </label>

        <div className="inline-flex rounded-lg border border-slate-200 p-0.5 bg-slate-50 text-xs">
          <button
            type="button"
            onClick={() => {
              setMode('record');
              setUploadError(null);
            }}
            className={`px-2.5 py-1 rounded-md font-medium transition-colors cursor-pointer ${
              mode === 'record' ? 'bg-white text-slate-900 shadow-2xs' : 'text-slate-500 hover:text-slate-800'
            }`}
          >
            Record Voice
          </button>
          <button
            type="button"
            onClick={() => {
              setMode('upload');
              setMicError(null);
            }}
            className={`px-2.5 py-1 rounded-md font-medium transition-colors cursor-pointer ${
              mode === 'upload' ? 'bg-white text-slate-900 shadow-2xs' : 'text-slate-500 hover:text-slate-800'
            }`}
          >
            Upload File
          </button>
        </div>
      </div>

      {/* Main interaction panel */}
      <div className="p-4 rounded-xl border border-slate-200 bg-white shadow-2xs">
        {mode === 'record' ? (
          <div className="space-y-3">
            {/* Record / Stop / Timer controls */}
            {!audioFile && !converting ? (
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div className="flex items-center gap-3">
                  {!isRecording ? (
                    <button
                      type="button"
                      onClick={startRecording}
                      className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-rose-600 hover:bg-rose-700 text-white text-xs font-semibold shadow-xs transition-colors cursor-pointer"
                    >
                      <Mic className="w-4 h-4" />
                      Start Recording
                    </button>
                  ) : (
                    <button
                      type="button"
                      onClick={stopRecording}
                      className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-slate-900 hover:bg-slate-800 text-white text-xs font-semibold shadow-xs transition-colors cursor-pointer animate-pulse"
                    >
                      <Square className="w-4 h-4 fill-white" />
                      Stop Recording
                    </button>
                  )}

                  {isRecording && (
                    <div className="flex items-center gap-2">
                      <span className="w-2.5 h-2.5 rounded-full bg-rose-600 animate-ping" />
                      <span className="font-mono text-xs font-bold text-rose-600">
                        {formatTimer(timerSeconds)} / 01:00
                      </span>
                    </div>
                  )}
                </div>

                <span className="text-[11px] text-slate-400">
                  Speak in Marathi, Hindi, or English (max 60 seconds).
                </span>
              </div>
            ) : null}

            {/* Converting indicator */}
            {converting && (
              <div className="p-3 rounded-lg bg-brand-50 border border-brand-100 flex items-center gap-2 text-xs text-brand-800">
                <div className="w-3.5 h-3.5 border-2 border-brand-600 border-t-transparent rounded-full animate-spin" />
                <span>Optimizing voice note to 16 kHz 16-bit WAV for AI analysis...</span>
              </div>
            )}

            {/* Recorded audio player & re-record button */}
            {audioFile && !converting && (
              <div className="space-y-2">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-semibold text-emerald-700 flex items-center gap-1">
                    <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                    Voice note ready ({audioFile.name})
                  </span>
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={startRecording}
                      className="inline-flex items-center gap-1 px-2.5 py-1 rounded border border-slate-200 hover:bg-slate-50 text-slate-700 text-xs font-medium cursor-pointer"
                    >
                      <RotateCcw className="w-3.5 h-3.5" />
                      Re-record
                    </button>
                    <button
                      type="button"
                      onClick={handleRemove}
                      className="inline-flex items-center gap-1 px-2.5 py-1 rounded border border-rose-200 text-rose-600 hover:bg-rose-50 text-xs font-medium cursor-pointer"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                      Remove
                    </button>
                  </div>
                </div>

                {audioUrl && (
                  <audio
                    src={audioUrl}
                    controls
                    className="w-full h-10 rounded-lg border border-slate-200 bg-slate-50"
                  />
                )}
              </div>
            )}

            {/* Friendly Microphone error */}
            {micError && (
              <div className="p-3 rounded-lg bg-amber-50 border border-amber-200 flex items-start gap-2.5 text-xs text-amber-900">
                <AlertCircle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
                <div className="flex-1">
                  <p>{micError}</p>
                  <button
                    type="button"
                    onClick={() => setMode('upload')}
                    className="mt-1 font-semibold text-brand-700 hover:underline cursor-pointer"
                  >
                    Switch to upload audio file &rarr;
                  </button>
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="space-y-3">
            {/* Audio file upload input */}
            {!audioFile ? (
              <div>
                <label className="border-2 border-dashed border-slate-200 hover:border-slate-300 rounded-xl p-5 flex flex-col items-center justify-center bg-slate-50 hover:bg-slate-100/60 transition-colors cursor-pointer">
                  <Upload className="w-6 h-6 text-slate-400 mb-1.5" />
                  <span className="text-xs font-semibold text-slate-700">
                    Choose an audio file from your device
                  </span>
                  <span className="text-[11px] text-slate-400 mt-0.5">
                    .mp3, .wav, .ogg, .m4a, .aac, .flac (up to 15 MB)
                  </span>
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".mp3,.wav,.ogg,.m4a,.aac,.flac,audio/*"
                    onChange={handleFileUpload}
                    className="hidden"
                  />
                </label>
              </div>
            ) : (
              <div className="space-y-2">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-semibold text-slate-800 truncate max-w-[200px] sm:max-w-md">
                    {audioFile.name} ({(audioFile.size / (1024 * 1024)).toFixed(2)} MB)
                  </span>
                  <button
                    type="button"
                    onClick={handleRemove}
                    className="inline-flex items-center gap-1 px-2.5 py-1 rounded border border-rose-200 text-rose-600 hover:bg-rose-50 text-xs font-medium cursor-pointer"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                    Remove
                  </button>
                </div>

                {audioUrl && (
                  <audio
                    src={audioUrl}
                    controls
                    className="w-full h-10 rounded-lg border border-slate-200 bg-slate-50"
                  />
                )}
              </div>
            )}

            {uploadError && (
              <p className="text-xs text-rose-600 font-medium flex items-center gap-1">
                <AlertCircle className="w-3.5 h-3.5" />
                {uploadError}
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
