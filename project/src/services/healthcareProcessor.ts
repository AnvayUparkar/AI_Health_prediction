/**
 * Healthcare Data Processor
 * Normalizes, cross-calculates distances, and sorts results.
 */
import { calculateDistance } from './geoService';

export interface HealthcareFacility {
  id: string | number;
  name: string;
  type: 'doctor' | 'clinic' | 'hospital' | 'other';
  lat: number;
  lon: number;
  distance: number;
  address?: string;
  isGlobal?: boolean;
}


export const processFacilities = (
  rawJson: any,
  userLat: number,
  userLon: number
): HealthcareFacility[] => {
  if (!rawJson || !rawJson.elements) return [];

  const facilities: HealthcareFacility[] = rawJson.elements.map((el: any) => {
    const lat = el.lat || (el.center ? el.center.lat : 0);
    const lon = el.lon || (el.center ? el.center.lon : 0);
    const amenity = el.tags.amenity;
    
    // Normalize type
    let type: HealthcareFacility['type'] = 'other';
    if (amenity === 'doctors') type = 'doctor';
    else if (amenity === 'clinic') type = 'clinic';
    else if (amenity === 'hospital') type = 'hospital';

    const distance = calculateDistance(userLat, userLon, lat, lon);

    return {
      id: el.id,
      name: el.tags.name || `Unnamed ${type.charAt(0).toUpperCase() + type.slice(1)}`,
      type,
      lat,
      lon,
      distance,
      address: el.tags['addr:street'] || el.tags['addr:city'] || ''
    };
  });

  // Sort: Nearest first
  return facilities.sort((a, b) => a.distance - b.distance);
};
