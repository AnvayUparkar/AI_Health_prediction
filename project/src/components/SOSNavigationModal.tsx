import React, { useState, useEffect, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Navigation, AlertTriangle, Clock, MapPin, ExternalLink, Loader2 } from 'lucide-react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { getNearestHospital } from '../services/api';

// ── Marker Icons ─────────────────────────────────────────────────────────────

import shadowUrl from 'leaflet/dist/images/marker-shadow.png';

const UserPulseIcon = L.divIcon({
  className: '',
  html: `
    <div style="position:relative;width:24px;height:24px;">
      <div style="position:absolute;inset:0;background:#3b82f6;border-radius:50%;opacity:0.3;animation:sosPulse 1.5s ease-out infinite;"></div>
      <div style="position:absolute;top:4px;left:4px;width:16px;height:16px;background:#3b82f6;border-radius:50%;border:3px solid white;box-shadow:0 2px 8px rgba(59,130,246,0.5);"></div>
    </div>
    <style>@keyframes sosPulse{0%{transform:scale(1);opacity:0.4}100%{transform:scale(2.5);opacity:0}}</style>
  `,
  iconSize: [24, 24],
  iconAnchor: [12, 12],
});

const HospitalMarkerIcon = L.icon({
  iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-red.png',
  shadowUrl,
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
});

// ── Types ────────────────────────────────────────────────────────────────────

interface HospitalData {
  hospital_id: string;
  name: string;
  latitude: number;
  longitude: number;
  distance: number;
}

interface RouteInfo {
  distance: number; // km
  duration: number; // minutes
  coordinates: [number, number][];
}

// ── Component ────────────────────────────────────────────────────────────────

const SOSNavigationModal: React.FC = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [userCoords, setUserCoords] = useState<{ lat: number; lng: number } | null>(null);
  const [hospital, setHospital] = useState<HospitalData | null>(null);
  const [route, setRoute] = useState<RouteInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<L.Map | null>(null);
  const routeLayerRef = useRef<L.LayerGroup | null>(null);

  // ── Listen for SOS trigger event ───────────────────────────────────────────
  useEffect(() => {
    const handler = (e: CustomEvent<{ lat: number; lng: number }>) => {
      console.log('[SOSNav] Received sos-navigate event:', e.detail);
      setUserCoords({ lat: e.detail.lat, lng: e.detail.lng });
      setIsOpen(true);
      setLoading(true);
      setError(null);
      setHospital(null);
      setRoute(null);
    };

    window.addEventListener('sos-navigate', handler as EventListener);
    return () => window.removeEventListener('sos-navigate', handler as EventListener);
  }, []);

  // ── Fetch nearest hospital when modal opens ────────────────────────────────
  useEffect(() => {
    if (!isOpen || !userCoords) return;

    const fetchHospital = async () => {
      try {
        setLoading(true);
        const data = await getNearestHospital(userCoords.lat, userCoords.lng);
        setHospital(data);
        console.log('[SOSNav] Nearest hospital:', data);
      } catch (err: any) {
        console.error('[SOSNav] Failed to fetch hospital:', err);
        setError('Could not find nearest hospital. Please call emergency services.');
      } finally {
        setLoading(false);
      }
    };

    fetchHospital();
  }, [isOpen, userCoords]);

  // ── Fetch OSRM route ──────────────────────────────────────────────────────
  const fetchRoute = useCallback(async (
    fromLat: number, fromLng: number,
    toLat: number, toLng: number
  ): Promise<RouteInfo | null> => {
    try {
      const url = `https://router.project-osrm.org/route/v1/driving/${fromLng},${fromLat};${toLng},${toLat}?overview=full&geometries=geojson`;
      const res = await fetch(url);
      const data = await res.json();

      if (data.code === 'Ok' && data.routes?.[0]) {
        const r = data.routes[0];
        return {
          distance: Math.round((r.distance / 1000) * 10) / 10,
          duration: Math.round(r.duration / 60),
          coordinates: r.geometry.coordinates.map(
            (c: [number, number]) => [c[1], c[0]] as [number, number]
          ),
        };
      }
    } catch (err) {
      console.warn('[SOSNav] OSRM route failed, showing straight line:', err);
    }
    return null;
  }, []);

  // ── Initialize / update map ────────────────────────────────────────────────
  useEffect(() => {
    if (!isOpen || !userCoords || !hospital) return;

    // Small delay to ensure the DOM container is fully visible after animation
    const timer = setTimeout(async () => {
      if (!mapContainerRef.current) return;

      // Destroy previous map instance
      if (mapRef.current) {
        mapRef.current.remove();
        mapRef.current = null;
      }

      // Create map
      const map = L.map(mapContainerRef.current, {
        zoomControl: true,
        attributionControl: false,
      }).setView([userCoords.lat, userCoords.lng], 14);

      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19,
      }).addTo(map);

      // Force Leaflet to recalculate container size after modal animation
      setTimeout(() => map.invalidateSize(), 100);
      setTimeout(() => map.invalidateSize(), 300);
      setTimeout(() => map.invalidateSize(), 600);

      mapRef.current = map;
      routeLayerRef.current = L.layerGroup().addTo(map);

      // User marker
      L.marker([userCoords.lat, userCoords.lng], {
        icon: UserPulseIcon,
        zIndexOffset: 1000,
      })
        .bindPopup('<b style="color:#3b82f6;">📍 Your Location</b>')
        .addTo(map);

      // Hospital marker
      L.marker([hospital.latitude, hospital.longitude], {
        icon: HospitalMarkerIcon,
      })
        .bindPopup(`<b style="color:#dc2626;">🏥 ${hospital.name}</b><br/><span style="color:#6b7280;">${hospital.distance} km away</span>`)
        .addTo(map)
        .openPopup();

      // Fetch and draw route
      const routeData = await fetchRoute(
        userCoords.lat, userCoords.lng,
        hospital.latitude, hospital.longitude
      );

      if (routeData && routeData.coordinates.length > 0) {
        setRoute(routeData);
        const polyline = L.polyline(routeData.coordinates, {
          color: '#dc2626',
          weight: 5,
          opacity: 0.8,
          dashArray: '10 6',
          lineCap: 'round',
        }).addTo(routeLayerRef.current!);
        map.fitBounds(polyline.getBounds().pad(0.15));
      } else {
        // Fallback: fit bounds to both markers
        setRoute({
          distance: hospital.distance,
          duration: Math.round(hospital.distance * 2.5), // rough estimate
          coordinates: [],
        });
        const bounds = L.latLngBounds(
          [userCoords.lat, userCoords.lng],
          [hospital.latitude, hospital.longitude]
        );
        map.fitBounds(bounds.pad(0.3));
      }

      // Final invalidateSize after everything is drawn
      setTimeout(() => map.invalidateSize(), 200);
    }, 400);

    return () => clearTimeout(timer);
  }, [isOpen, userCoords, hospital, fetchRoute]);

  // ── Cleanup map on close ───────────────────────────────────────────────────
  const handleClose = () => {
    setIsOpen(false);
    if (mapRef.current) {
      mapRef.current.remove();
      mapRef.current = null;
    }
  };

  // ── Google Maps navigation link ────────────────────────────────────────────
  const googleMapsUrl = userCoords && hospital
    ? `https://www.google.com/maps/dir/?api=1&origin=${userCoords.lat},${userCoords.lng}&destination=${encodeURIComponent(hospital.name)}&travelmode=driving`
    : '#';

  // ── Render ─────────────────────────────────────────────────────────────────
  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          key="sos-nav-overlay"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.3 }}
          className="fixed inset-0 z-[9999] bg-black/60 backdrop-blur-sm flex items-end sm:items-center justify-center p-0 sm:p-4"
          onClick={(e) => { if (e.target === e.currentTarget) handleClose(); }}
        >
          <motion.div
            initial={{ y: '100%', opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            exit={{ y: '100%', opacity: 0 }}
            transition={{ type: 'spring', damping: 30, stiffness: 300 }}
            className="relative w-full sm:max-w-2xl bg-white rounded-t-3xl sm:rounded-3xl shadow-2xl overflow-hidden max-h-[95vh] sm:max-h-[90vh] flex flex-col"
          >
            {/* ── Emergency Banner ── */}
            <div className="bg-gradient-to-r from-red-600 via-red-500 to-orange-500 px-6 py-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-white/20 rounded-xl animate-pulse">
                    <AlertTriangle className="h-6 w-6 text-white" />
                  </div>
                  <div>
                    <h2 className="text-white font-black text-lg tracking-wide">
                      🚨 EMERGENCY NAVIGATION
                    </h2>
                    <p className="text-red-100 text-xs font-medium">
                      Route to nearest hospital
                    </p>
                  </div>
                </div>
                <button
                  onClick={handleClose}
                  className="p-2 hover:bg-white/20 rounded-xl transition-colors"
                >
                  <X className="h-5 w-5 text-white" />
                </button>
              </div>
            </div>

            {/* ── Hospital Info Bar ── */}
            {hospital && (
              <div className="px-6 py-3 bg-gray-50 border-b border-gray-100 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-red-100 rounded-lg">
                    <MapPin className="h-4 w-4 text-red-600" />
                  </div>
                  <div>
                    <p className="text-sm font-bold text-gray-800">{hospital.name}</p>
                    <p className="text-xs text-gray-500">{hospital.distance} km away</p>
                  </div>
                </div>
                {route && (
                  <div className="flex items-center gap-4 text-xs">
                    <div className="flex items-center gap-1 text-gray-600">
                      <Navigation className="h-3.5 w-3.5" />
                      <span className="font-bold">{route.distance} km</span>
                    </div>
                    <div className="flex items-center gap-1 text-gray-600">
                      <Clock className="h-3.5 w-3.5" />
                      <span className="font-bold">~{route.duration} min</span>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* ── Map Container ── */}
            <div className="relative flex-1 min-h-[350px] sm:min-h-[400px]">
              {loading && (
                <div className="absolute inset-0 z-10 bg-white/80 flex flex-col items-center justify-center gap-3">
                  <Loader2 className="h-10 w-10 text-red-500 animate-spin" />
                  <p className="text-sm font-bold text-gray-600">Locating nearest hospital...</p>
                </div>
              )}
              {error && (
                <div className="absolute inset-0 z-10 bg-white flex flex-col items-center justify-center gap-3 p-8">
                  <AlertTriangle className="h-12 w-12 text-amber-500" />
                  <p className="text-sm font-bold text-gray-700 text-center">{error}</p>
                  <p className="text-xs text-gray-500 text-center">Call your local emergency number immediately.</p>
                </div>
              )}
              <div ref={mapContainerRef} style={{ height: '400px', width: '100%' }} />
            </div>

            {/* ── Action Bar ── */}
            {hospital && (
              <div className="px-6 py-4 bg-white border-t border-gray-100 flex gap-3">
                <a
                  href={googleMapsUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex-1 flex items-center justify-center gap-2 bg-gradient-to-r from-blue-600 to-blue-500 text-white font-bold py-3 px-4 rounded-xl shadow-lg hover:shadow-xl transition-all text-sm"
                >
                  <ExternalLink className="h-4 w-4" />
                  Navigate in Google Maps
                </a>
                <button
                  onClick={handleClose}
                  className="px-4 py-3 bg-gray-100 hover:bg-gray-200 text-gray-700 font-bold rounded-xl transition-colors text-sm"
                >
                  Close
                </button>
              </div>
            )}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};

export default SOSNavigationModal;
