/**
 * Geospatial Service
 * Handles user geolocation fetching and distance calculations.
 */

export interface UserLocation {
  latitude: number;
  longitude: number;
}

export const getIPLocation = async (): Promise<UserLocation> => {
  try {
    const response = await fetch('https://ipapi.co/json/');
    const data = await response.json();
    if (data.latitude && data.longitude) {
      return {
        latitude: data.latitude,
        longitude: data.longitude,
      };
    }
    throw new Error('IP Location data incomplete');
  } catch (error) {
    console.warn('IP Geolocation fallback failed:', error);
    // Generic fallback to Mumbai center if all else fails
    return { latitude: 19.0760, longitude: 72.8777 };
  }
};

export const getUserLocation = (timeout: number = 10000): Promise<UserLocation> => {
  return new Promise((resolve) => {
    if (!navigator.geolocation) {
      getIPLocation().then(resolve);
      return;
    }

    navigator.geolocation.getCurrentPosition(
      (position) => {
        resolve({
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
        });
      },
      async (error) => {
        console.warn('HTML5 Geolocation failed, using IP fallback:', error.message);
        const loc = await getIPLocation();
        resolve(loc);
      },
      {
        enableHighAccuracy: true,
        timeout: timeout,
        maximumAge: 0,
      }
    );
  });
};

/**
 * Calculates the distance between two points using the Haversine formula.
 */
export const calculateDistance = (
  lat1: number,
  lon1: number,
  lat2: number,
  lon2: number
): number => {
  const R = 6371; // Earth's radius in km
  const dLat = (lat2 - lat1) * (Math.PI / 180);
  const dLon = (lon2 - lon1) * (Math.PI / 180);
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos(lat1 * (Math.PI / 180)) *
      Math.cos(lat2 * (Math.PI / 180)) *
      Math.sin(dLon / 2) *
      Math.sin(dLon / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return R * c;
};
