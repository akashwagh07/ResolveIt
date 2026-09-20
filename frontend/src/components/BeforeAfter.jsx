import React, { useState } from 'react';
import { Layers, Maximize2, X, AlertCircle } from 'lucide-react';

export default function BeforeAfter({ beforeEvidence = [], afterEvidence = [] }) {
  const [activeModalImage, setActiveModalImage] = useState(null);

  if ((!beforeEvidence || beforeEvidence.length === 0) && (!afterEvidence || afterEvidence.length === 0)) {
    return null;
  }

  return (
    <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-xs space-y-4">
      <div className="flex items-center justify-between border-b border-slate-100 pb-3">
        <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
          <Layers className="w-4 h-4 text-brand-600" />
          Before & After Resolution Comparison
        </h3>
        <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
          Visual Evidence
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* BEFORE COLUMN */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-rose-500 inline-block" />
              Before Repair (Citizen Report)
            </span>
            <span className="text-[10px] text-slate-400 font-mono">
              {beforeEvidence.length} {beforeEvidence.length === 1 ? 'image' : 'images'}
            </span>
          </div>

          {beforeEvidence.length > 0 ? (
            <div className="space-y-2">
              {beforeEvidence.map((ev) => (
                <div
                  key={ev.id}
                  className="relative group rounded-xl overflow-hidden border border-slate-200 bg-slate-100"
                >
                  <img
                    src={ev.url || `/api/evidence/${ev.id}/file`}
                    alt="Original reported issue"
                    className="w-full h-48 object-cover cursor-pointer group-hover:scale-102 transition-transform duration-200"
                    onClick={() => setActiveModalImage(ev.url || `/api/evidence/${ev.id}/file`)}
                  />
                  <button
                    type="button"
                    onClick={() => setActiveModalImage(ev.url || `/api/evidence/${ev.id}/file`)}
                    className="absolute bottom-2 right-2 p-1.5 rounded-md bg-black/60 text-white opacity-0 group-hover:opacity-100 transition-opacity text-xs flex items-center gap-1 cursor-pointer"
                  >
                    <Maximize2 className="w-3.5 h-3.5" />
                    Enlarge
                  </button>
                  <div className="absolute top-2 left-2 px-2 py-0.5 rounded-md bg-black/60 text-white font-semibold text-[10px] uppercase">
                    Before
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="h-48 rounded-xl border border-dashed border-slate-200 bg-slate-50 flex items-center justify-center text-xs text-slate-400 italic">
              No before photo attached
            </div>
          )}
        </div>

        {/* AFTER COLUMN */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 inline-block" />
              After Repair (Officer Proof)
            </span>
            <span className="text-[10px] text-slate-400 font-mono">
              {afterEvidence.length} {afterEvidence.length === 1 ? 'image' : 'images'}
            </span>
          </div>

          {afterEvidence.length > 0 ? (
            <div className="space-y-2">
              {afterEvidence.map((ev) => (
                <div
                  key={ev.id}
                  className="relative group rounded-xl overflow-hidden border border-slate-200 bg-slate-100"
                >
                  <img
                    src={ev.url || `/api/evidence/${ev.id}/file`}
                    alt="Officer resolution proof"
                    className="w-full h-48 object-cover cursor-pointer group-hover:scale-102 transition-transform duration-200"
                    onClick={() => setActiveModalImage(ev.url || `/api/evidence/${ev.id}/file`)}
                  />
                  <button
                    type="button"
                    onClick={() => setActiveModalImage(ev.url || `/api/evidence/${ev.id}/file`)}
                    className="absolute bottom-2 right-2 p-1.5 rounded-md bg-black/60 text-white opacity-0 group-hover:opacity-100 transition-opacity text-xs flex items-center gap-1 cursor-pointer"
                  >
                    <Maximize2 className="w-3.5 h-3.5" />
                    Enlarge
                  </button>
                  <div className="absolute top-2 left-2 px-2 py-0.5 rounded-md bg-emerald-700 text-white font-semibold text-[10px] uppercase">
                    After
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="h-48 rounded-xl border border-dashed border-slate-200 bg-slate-50 flex items-center justify-center text-xs text-slate-400 italic">
              No after photo submitted yet
            </div>
          )}
        </div>
      </div>

      {/* Zoom Modal */}
      {activeModalImage && (
        <div
          className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-4 backdrop-blur-2xs"
          onClick={() => setActiveModalImage(null)}
        >
          <div
            className="relative max-w-4xl max-h-[90vh] bg-slate-950 rounded-2xl overflow-hidden shadow-2xl border border-slate-800"
            onClick={(e) => e.stopPropagation()}
          >
            <button
              type="button"
              onClick={() => setActiveModalImage(null)}
              className="absolute top-3 right-3 p-2 rounded-full bg-black/60 text-white hover:bg-black/80 transition-colors z-10 cursor-pointer"
              title="Close"
            >
              <X className="w-5 h-5" />
            </button>
            <img
              src={activeModalImage}
              alt="Enlarged evidence comparison"
              className="max-w-full max-h-[85vh] object-contain mx-auto"
            />
          </div>
        </div>
      )}
    </div>
  );
}
