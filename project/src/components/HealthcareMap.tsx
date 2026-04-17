import React, { useEffect, useRef } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { HealthcareFacility } from '../services/healthcareProcessor';
import { UserLocation } from '../services/geoService';

// Fix for default Leaflet marker icon issues in Vite/Webpack
import iconUrl from 'leaflet/dist/images/marker-icon.png';
import iconRetinaUrl from 'leaflet/dist/images/marker-icon-2x.png';
import shadowUrl from 'leaflet/dist/images/marker-shadow.png';

const DefaultIcon = L.icon({
  iconUrl,
  iconRetinaUrl,
  shadowUrl,
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41]
});

// Distinct icons for User, Doctor, and Hospital
const UserIcon = L.divIcon({
  className: 'user-location-marker',
  html: '<div style="background-color: #3b82f6; width: 15px; height: 15px; border-radius: 50%; border: 3px solid white; box-shadow: 0 0 10px rgba(0,0,0,0.3);"></div>',
  iconSize: [20, 20],
});

const DoctorIcon = L.icon({
  iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-green.png',
  shadowUrl,
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41]
});

const HospitalIcon = L.icon({
  iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-red.png',
  shadowUrl,
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41]
});

L.Marker.prototype.options.icon = DefaultIcon;

interface HealthcareMapProps {
  facilities: HealthcareFacility[];
  userLocation: UserLocation | null;
  selectedFacilityId?: string | number;
  onLocationChange?: (location: UserLocation) => void;
}

const HealthcareMap: React.FC<HealthcareMapProps> = ({ 
  facilities, 
  userLocation,
  selectedFacilityId,
  onLocationChange
}) => {
  const mapContainer = useRef<HTMLDivElement>(null);
  const mapInstance = useRef<L.Map | null>(null);
  const markersLayer = useRef<L.LayerGroup | null>(null);

  useEffect(() => {
    if (!mapContainer.current || mapInstance.current) return;

    // Initialize map
    mapInstance.current = L.map(mapContainer.current).setView([19.0760, 72.8777], 13);
    
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '© OpenStreetMap contributors'
    }).addTo(mapInstance.current);

    markersLayer.current = L.layerGroup().addTo(mapInstance.current);

    return () => {
      mapInstance.current?.remove();
      mapInstance.current = null;
    };
  }, []);

  useEffect(() => {
    if (!mapInstance.current || !markersLayer.current) return;

    markersLayer.current.clearLayers();

    const layer = markersLayer.current; // Local reference for TS inference
    const markers: L.Marker[] = [];

    // Add User Location
    if (userLocation) {
      const userMarker = L.marker([userLocation.latitude, userLocation.longitude], { 
        icon: UserIcon,
        zIndexOffset: 1000,
        draggable: true
      })
        .bindPopup('<b>Your Location</b><br/><span style="font-size: 0.7rem; color: #6b7280;">Drag to correct position</span>')
        .addTo(layer);
      
      userMarker.on('dragend', (event) => {
        const marker = event.target;
        const position = marker.getLatLng();
        if (onLocationChange) {
          onLocationChange({
            latitude: position.lat,
            longitude: position.lng
          });
        }
      });

      markers.push(userMarker);
    }

    // Add Facility Markers
    facilities.forEach((facility) => {
      const icon = facility.type === 'hospital' ? HospitalIcon : DoctorIcon;
      const marker = L.marker([facility.lat, facility.lon], { icon })
        .bindPopup(`
          <div style="font-family: inherit;">
            <b style="color: #1e3a8a;">${facility.name}</b><br/>
            <span style="color: #6b7280; font-size: 0.8rem; text-transform: capitalize;">${facility.type}</span><br/>
            <span style="color: #3b82f6; font-weight: bold;">${facility.distance.toFixed(2)} km away</span>
          </div>
        `)
        .addTo(layer);
      
      markers.push(marker);

      if (selectedFacilityId && facility.id === selectedFacilityId) {
        marker.openPopup();
        mapInstance.current?.setView([facility.lat, facility.lon], 15);
      }
    });

    // Auto-zoom to fit all markers if no specific facility is selected
    if (markers.length > 0 && !selectedFacilityId) {
      try {
        const group = L.featureGroup(markers);
        mapInstance.current.fitBounds(group.getBounds().pad(0.1));
      } catch (e) {
        console.warn('Map fitBounds failed', e);
      }
    }
  }, [facilities, userLocation, selectedFacilityId]);

  return (
    <div className="mt-8 rounded-3xl overflow-hidden shadow-2xl border border-white/40 h-[400px] z-0">
      <div ref={mapContainer} className="h-full w-full" />
    </div>
  );
};

export default HealthcareMap;
