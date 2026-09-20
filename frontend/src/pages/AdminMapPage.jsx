import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { MapContainer, TileLayer, CircleMarker, Popup } from 'react-leaflet';
import { ExternalLink, RefreshCw, AlertCircle } from 'lucide-react';
import { getComplaints } from '../lib/api';
import StatusBadge from '../components/StatusBadge';
import SeverityBadge from '../components/SeverityBadge';
import LoadingState from '../components/LoadingState';
import ErrorState from '../components/ErrorState';

const SEVERITY_MARKER_COLORS = {
  LOW: '#10b981',      // Green
  MEDIUM: '#eab308',   // Yellow
  HIGH: '#f97316',     // Orange
  CRITICAL: '#ef4444', // Red
};

export default function AdminMapPage() {
  const [complaints, setComplaints] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchMapData = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getComplaints({ limit: 200 });
      setComplaints(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMapData();
  }, []);

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-12">
        <LoadingState message="Loading geospatial complaints onto map..." />
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-12">
        <ErrorState message={error} onRetry={fetchMapData} />
      </div>
    );
  }

  const validComplaints = complaints.filter(
    (c) => typeof c.latitude === 'number' && typeof c.longitude === 'number'
  );

  const avgLat = validComplaints.length
    ? validComplaints.reduce((sum, c) => sum + c.latitude, 0) / validComplaints.length
    : 16.705;

  const avgLng = validComplaints.length
    ? validComplaints.reduce((sum, c) => sum + c.longitude, 0) / validComplaints.length
    : 74.24;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Geospatial Issue Map</h1>
          <p className="text-xs text-slate-500 mt-1">
            Displaying active complaints in Kolhapur colored by deterministic severity score.
          </p>
        </div>

        <div className="flex items-center gap-4">
          {/* Legend */}
          <div className="hidden sm:flex items-center gap-3 bg-white px-3 py-1.5 rounded-lg border border-slate-200 text-xs text-slate-600 shadow-2xs">
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
              Low
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-yellow-500" />
              Medium
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-orange-500" />
              High
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-rose-500" />
              Critical
            </span>
          </div>

          <button
            type="button"
            onClick={fetchMapData}
            className="p-2 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-600 shadow-2xs transition-colors"
            title="Refresh map points"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Map Container */}
      <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-sm h-[640px] relative">
        <MapContainer
          center={[avgLat, avgLng]}
          zoom={13}
          scrollWheelZoom={true}
          className="w-full h-full"
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />

          {validComplaints.map((c) => {
            const markerColor =
              SEVERITY_MARKER_COLORS[(c.severity_level || '').toUpperCase()] || '#3b82f6';

            return (
              <CircleMarker
                key={c.id}
                center={[c.latitude, c.longitude]}
                radius={10}
                pathOptions={{
                  color: '#ffffff',
                  weight: 2,
                  fillColor: markerColor,
                  fillOpacity: 0.9,
                }}
              >
                <Popup>
                  <div className="p-1 min-w-[200px] text-xs">
                    <div className="flex items-center justify-between gap-2 mb-1.5">
                      <span className="font-bold text-slate-900 truncate">
                        {c.issue.replace(/_/g, ' ')}
                      </span>
                      <StatusBadge status={c.status} size="sm" />
                    </div>

                    <p className="text-slate-600 text-[11px] mb-2 line-clamp-2">
                      {c.address_text}
                    </p>

                    <div className="flex items-center justify-between pt-2 border-t border-slate-100">
                      <SeverityBadge level={c.severity_level} score={c.severity_score} size="sm" />
                      <Link
                        to={`/admin/complaints/${c.id}`}
                        className="inline-flex items-center gap-1 text-[11px] font-bold text-brand-600 hover:text-brand-800"
                      >
                        Inspect
                        <ExternalLink className="w-3 h-3" />
                      </Link>
                    </div>
                  </div>
                </Popup>
              </CircleMarker>
            );
          })}
        </MapContainer>
      </div>
    </div>
  );
}
