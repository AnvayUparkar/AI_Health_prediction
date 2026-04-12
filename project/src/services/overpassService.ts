/**
 * Overpass API Service
 * Fetches medical facilities from OpenStreetMap.
 */

export const fetchNearbyHealthcare = async (lat: number, lon: number, radius: number = 5000): Promise<any> => {
  const endpoint = 'https://overpass-api.de/api/interpreter';
  
  // Single optimized query for node + way + relation for doctors, clinics, and hospitals
  const query = `
    [out:json][timeout:25];
    (
      node["amenity"~"doctors|clinic|hospital"](around:${radius},${lat},${lon});
      way["amenity"~"doctors|clinic|hospital"](around:${radius},${lat},${lon});
      relation["amenity"~"doctors|clinic|hospital"](around:${radius},${lat},${lon});
    );
    out center;
  `;

  const response = await fetch(endpoint, {
    method: 'POST',
    body: query,
  });

  if (!response.ok) {
    throw new Error(`Overpass API Error: ${response.statusText}`);
  }

  return await response.json();
};
