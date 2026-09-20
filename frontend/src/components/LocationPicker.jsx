import React, { useState, useEffect } from 'react';
import { MapContainer, TileLayer, Marker, useMap, useMapEvents } from 'react-leaflet';
import L from 'leaflet';
import { MapPin, Navigation, AlertCircle } from 'lucide-react';

const KOLHAPUR_COORDS = [16.705, 74.2433];

// Custom marker pin avoiding missing PNG icons
const pinIcon = L.divIcon({
  className: 'resolveit-pin-icon',
  html: `<div style="background-color: #2563eb; width: 28px; height: 28px; border-radius: 50%; border: 3px solid #ffffff; box-shadow: 0 4px 10px rgba(0,0,0,0.35); display: flex; align-items: center; justify-content: center;">
           <div style="background-color: #ffffff; width: 8px; height: 8px; border-radius: 50%;"></div>
         </div>`,
  iconSize: [28, 28],
  iconAnchor: [14, 14],
});

function MapClickHandler({ onSelectLocation }) {
  useMapEvents({
    click(e) {
      const lat = Number(e.latlng.lat.toFixed(5));
      const lng = Number(e.latlng.lng.toFixed(5));
      onSelectLocation(lat, lng);
    },
  });
  return null;
}

function FlyToUpdater({ center }) {
  const map = useMap();
  useEffect(() => {
    if (center && center[0] && center[1]) {
      map.flyTo(center, Math.max(map.getZoom(), 14), { duration: 1 });
    }
  }, [center, map]);
  return null;
}

export default function LocationPicker({
  latitude,
  longitude,
  onLocationChange,
  addressText,
  onAddressChange,
  error,
}) {
  const [geoError, setGeoError] = useState(null);
  const [locating, setLocating] = useState(false);

  const currentCenter =
    latitude && longitude ? [latitude, longitude] : KOLHAPUR_COORDS;

  const handleUseCurrentLocation = () => {
    setGeoError(null);
    if (!navigator.geolocation) {
      setGeoError('Geolocation is not supported by your browser.');
      return;
    }

    setLocating(true);
    navigator.geolocation.getCurrentPosition(
      (position) => {
        setLocating(false);
        const lat = Number(position.coords.latitude.toFixed(5));
        const lng = Number(position.coords.longitude.toFixed(5));
        onLocationChange(lat, lng);
      },
      (err) => {
        setLocating(false);
        switch (err.code) {
          case err.PERMISSION_DENIED:
            setGeoError('Location permission denied. Please tap or click on the map to set your location.');
            break;
          case err.POSITION_UNAVAILABLE:
            setGeoError('Location information is unavailable. Please select on the map.');
            break;
          case err.TIMEOUT:
            setGeoError('Location request timed out. Please tap or click on the map.');
            break;
          default:
            setGeoError('Could not retrieve location. Please select on the map.');
        }
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
    );
  };

  const handleMarkerDragEnd = (e) => {
    const latlng = e.target.getLatLng();
    const lat = Number(latlng.lat.toFixed(5));
    const lng = Number(latlng.lng.toFixed(5));
    onLocationChange(lat, lng);
  };

  return (
    <div className="space-y-3">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        <label className="text-xs font-semibold text-slate-800 flex items-center gap-1.5">
          <MapPin className="w-4 h-4 text-brand-600" />
          Location <span className="text-rose-500">*</span>
        </label>

        <button
          type="button"
          onClick={handleUseCurrentLocation}
          disabled={locating}
          className="inline-flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-lg border border-brand-200 bg-brand-50 hover:bg-brand-100 text-brand-700 text-xs font-semibold transition-colors disabled:opacity-60 cursor-pointer"
        >
          <Navigation className={`w-3.5 h-3.5 ${locating ? 'animate-spin' : ''}`} />
          {locating ? 'Locating...' : 'Use my current location'}
        </button>
      </div>

      <p className="text-[11px] text-slate-500">
        Tap or click the map to place a pin, or drag the marker to adjust the exact spot.
      </p>

      {/* Map container */}
      <div className={`relative h-64 sm:h-72 w-full rounded-xl overflow-hidden border ${
        error ? 'border-rose-400 ring-1 ring-rose-200' : 'border-slate-200'
      } shadow-2xs`}>
        <MapContainer
          center={currentCenter}
          zoom={13}
          scrollWheelZoom={false}
          className="h-full w-full"
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          <MapClickHandler onSelectLocation={onLocationChange} />
          {latitude && longitude && (
            <>
              <Marker
                position={[latitude, longitude]}
                icon={pinIcon}
                draggable={true}
                eventHandlers={{ dragend: handleMarkerDragEnd }}
              />
              <FlyToUpdater center={[latitude, longitude]} />
            </>
          )}
        </MapContainer>
      </div>

      {/* Coordinates readout and status */}
      <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
        <div className="flex items-center gap-2">
          <span className="text-slate-500">Coordinates:</span>
          {latitude && longitude ? (
            <span className="font-mono font-semibold text-slate-800 bg-slate-100 px-2 py-0.5 rounded">
              {latitude.toFixed(5)}, {longitude.toFixed(5)}
            </span>
          ) : (
            <span className="text-amber-600 font-medium italic">No location selected yet</span>
          )}
        </div>
      </div>

      {/* Geolocation feedback error */}
      {geoError && (
        <div className="flex items-start gap-2 p-2.5 rounded-lg bg-amber-50 border border-amber-200 text-amber-900 text-xs">
          <AlertCircle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
          <span>{geoError}</span>
        </div>
      )}

      {/* Validation error */}
      {error && (
        <p className="text-xs text-rose-600 font-medium flex items-center gap-1">
          <AlertCircle className="w-3.5 h-3.5" />
          {error}
        </p>
      )}

      {/* Optional Address / Landmark input */}
      <div>
        <label className="block text-xs font-medium text-slate-600 mb-1">
          Address / Landmark <span className="text-slate-400 font-normal">(optional)</span>
        </label>
        <input
          type="text"
          value={addressText}
          onChange={(e) => onAddressChange(e.target.value)}
          placeholder="e.g. Near Rankala Lake Chowk, Shivaji Road"
          className="w-full px-3 py-2 text-xs rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500 bg-white"
        />
        <p className="text-[10px] text-slate-400 mt-1">
          Provide landmark or street details to help the field team locate the problem.
        </p>
      </div>
    </div>
  );
}
