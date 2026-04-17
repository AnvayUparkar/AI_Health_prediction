import L from 'leaflet';
import 'leaflet-routing-machine';

let activeRoute: any = null;

/**
 * Draws a route on the map from user location to hospital location.
 * @param {L.Map} map - The Leaflet map instance
 * @param {number} userLat - User latitude
 * @param {number} userLng - User longitude
 * @param {number} hospitalLat - Hospital latitude
 * @param {number} hospitalLng - Hospital longitude
 */
export function drawRoute(map: L.Map, userLat: number, userLng: number, hospitalLat: number, hospitalLng: number) {
    if (!map) return;

    // Remove existing route if any
    if (activeRoute) {
        try {
            map.removeControl(activeRoute);
        } catch (e) {
            console.warn('Failed to remove active route control', e);
        }
    }

    // Create and add the new route control
    // @ts-ignore - L.Routing might not have proper type definitions available globally even with @types
    activeRoute = L.Routing.control(({
        waypoints: [
            L.latLng(userLat, userLng),
            L.latLng(hospitalLat, hospitalLng)
        ],
        lineOptions: {
            styles: [{ color: '#3b82f6', opacity: 0.8, weight: 6 }],
            extendToWaypoints: false,
            missingRouteTolerance: 10
        },

        routeWhileDragging: false,
        addWaypoints: false,
        fitSelectedRoutes: true,
        showAlternatives: false,
        createMarker: function() { return null; } // Don't create extra markers
    } as any)).addTo(map);

    // Minimize the routing instructions container for cleaner UI
    const container = activeRoute.getContainer();
    if (container) {
        container.style.display = 'none'; // Keep it hidden but functional
    }
}
