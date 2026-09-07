import { useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import MapView from "../components/MapView";
import api from "../api/axios";
import { useAuth } from "../context/AuthContext";

const active = (status) => status === "In Progress";

export default function GPSTracking() {
  const [searchParams] = useSearchParams();
  const { user } = useAuth();
  const isDriver = user?.role === "Driver";
  const [locations, setLocations] = useState([]); const [vehicles, setVehicles] = useState([]); const [drivers, setDrivers] = useState([]); const [trips, setTrips] = useState([]); const [vehicleToTrack, setVehicleToTrack] = useState(() => searchParams.get("vehicle_id") || ""); const [filterVehicleId, setFilterVehicleId] = useState(() => searchParams.get("vehicle_id") || ""); const [selectedVehicle, setSelectedVehicle] = useState(null); const [tripRoute, setTripRoute] = useState(null); const [error, setError] = useState("");
  const reconnectTimer = useRef(null);
  const locationWatch = useRef(null);
  const gpsSocket = useRef(null);
  const lastLocationSentAt = useRef(0);
  const load = async () => { try { const [gps, vehicleData, driverData, tripData] = await Promise.all([api.get("/gps/"), api.get("/vehicles/"), api.get("/drivers/"), api.get("/trips/")]); setLocations(gps.data); setVehicles(vehicleData.data); setDrivers(driverData.data); setTrips(tripData.data); } catch (requestError) { setError(requestError.response?.data?.detail || "Unable to load GPS locations."); } };
  useEffect(() => { const timer = setTimeout(() => { void load(); }, 0); const interval = window.setInterval(() => void load(), 10000); return () => { clearTimeout(timer); window.clearInterval(interval); }; }, []);
  useEffect(() => { const timer = window.setTimeout(() => { const vehicleId = searchParams.get("vehicle_id") || ""; const tripId = searchParams.get("trip_id") || ""; setVehicleToTrack(vehicleId); setFilterVehicleId(vehicleId); setSelectedVehicle(null); setTripRoute(null); if (!vehicleId) return; void api.get("/trips/").then((response) => setTrips(Array.isArray(response.data) ? response.data : [])).catch((requestError) => setError(requestError.response?.data?.detail || "Unable to load trip details.")); if (tripId) { void api.get(`/trips/${tripId}/route`).then((response) => setTripRoute(response.data)).catch((requestError) => setError(requestError.response?.data?.detail || "Unable to load this trip route.")); } void api.get(`/gps/${vehicleId}`).then((response) => { setLocations((current) => [response.data, ...current.filter((item) => item.vehicle_id !== response.data.vehicle_id)]); }).catch((requestError) => { if (requestError.response?.status === 404) setError("The route is shown below. This vehicle has not sent a live GPS location yet."); else setError(requestError.response?.data?.detail || "Unable to load this trip vehicle's GPS location."); }); }, 0); return () => window.clearTimeout(timer); }, [searchParams]);
  useEffect(() => {
    const token = sessionStorage.getItem("token");
    if (!token) return undefined;
    let socket; let closed = false;
    const connect = () => {
      const protocol = window.location.protocol === "https:" ? "wss" : "ws";
      socket = new WebSocket(`${protocol}://${window.location.host}/api/gps/ws?token=${encodeURIComponent(token)}`);
      gpsSocket.current = socket;
      socket.onmessage = (event) => {
        const message = JSON.parse(event.data);
        if (message.type === "server_ping") { socket.send(JSON.stringify({ type: "ping" })); return; }
        if (message.type !== "gps_location") return;
        const location = message.location;
        setLocations((current) => [location, ...current.filter((item) => item.vehicle_id !== location.vehicle_id)]);
      };
      socket.onclose = () => {
        if (gpsSocket.current === socket) gpsSocket.current = null;
        if (!closed) reconnectTimer.current = window.setTimeout(connect, 2000);
      };
    };
    connect();
    return () => { closed = true; window.clearTimeout(reconnectTimer.current); if (gpsSocket.current === socket) gpsSocket.current = null; socket?.close(); };
  }, []);
  useEffect(() => () => { if (locationWatch.current != null) navigator.geolocation?.clearWatch(locationWatch.current); }, []);
  const activeTrips = useMemo(() => trips.filter((trip) => active(trip.status)), [trips]);
  const selectedTrip = useMemo(() => trips.find((trip) => trip.trip_id === searchParams.get("trip_id")) || activeTrips.find((trip) => trip.vehicle_id === filterVehicleId) || null, [trips, activeTrips, searchParams, filterVehicleId]);
  const vehicleName = (id) => vehicles.find((vehicle) => vehicle.vehicle_id === id)?.registration_number || "Unknown vehicle";
  const driverName = (id) => drivers.find((driver) => driver.driver_id === id)?.name || "Unassigned";
  const allMapVehicles = locations.filter((location) => activeTrips.some((trip) => trip.vehicle_id === location.vehicle_id)).map((location) => { const trip = activeTrips.find((item) => item.vehicle_id === location.vehicle_id); return { ...location, vehicle: vehicleName(location.vehicle_id), driver: driverName(trip?.driver_id), location: `${Number(location.latitude).toFixed(6)}, ${Number(location.longitude).toFixed(6)}`, status: Number(location.speed) > 0 ? "Online" : "Offline", updated: new Date(location.timestamp).toLocaleString() }; });
  // Start with the complete active fleet. Previously this returned an empty
  // list until a user chose a vehicle, which made the tracking view appear
  // limited to whichever vehicle/location had been opened most recently.
  const mapVehicles = filterVehicleId
    ? allMapVehicles.filter((item) => item.vehicle_id === filterVehicleId)
    : allMapVehicles;
  const trackVehicle = async (event) => {
    event.preventDefault();
    setError("");
    try {
      const [tripResponse, response] = await Promise.all([api.get("/trips/"), api.get(`/gps/${vehicleToTrack}`)]);
      setTrips(Array.isArray(tripResponse.data) ? tripResponse.data : []);
      setLocations((current) => [response.data, ...current.filter((item) => item.vehicle_id !== response.data.vehicle_id)]);
      setFilterVehicleId(vehicleToTrack);
      setSelectedVehicle(vehicleName(vehicleToTrack));
    } catch (requestError) {
      setFilterVehicleId(vehicleToTrack);
      setSelectedVehicle(null);
      setError(requestError.response?.status === 404 ? "This vehicle has not sent a GPS location yet." : requestError.response?.data?.detail || "Unable to load this vehicle's GPS location.");
    }
  };
  const shareDriverLocation = () => {
    if (!vehicleToTrack) { setError("Select an active-trip vehicle first."); return; }
    if (!navigator.geolocation) { setError("This browser does not support location services."); return; }
    setError("");
    if (locationWatch.current != null) navigator.geolocation.clearWatch(locationWatch.current);
    locationWatch.current = navigator.geolocation.watchPosition(async (position) => {
      if (Date.now() - lastLocationSentAt.current < 5000) return;
      lastLocationSentAt.current = Date.now();
      const payload = { vehicle_id: vehicleToTrack, latitude: position.coords.latitude, longitude: position.coords.longitude, speed: position.coords.speed == null ? null : Math.max(0, position.coords.speed * 3.6) };
      try {
        if (gpsSocket.current?.readyState === WebSocket.OPEN) {
          gpsSocket.current.send(JSON.stringify(payload));
        } else {
          const response = await api.post("/gps/", payload);
          setLocations((current) => [response.data, ...current.filter((item) => item.vehicle_id !== response.data.vehicle_id)]);
        }
        setFilterVehicleId(vehicleToTrack);
        setSelectedVehicle(vehicleName(vehicleToTrack));
      } catch (requestError) { setError(requestError.response?.data?.detail || "Unable to share your location for this vehicle."); }
    }, () => setError("Location permission was denied. Allow location access in the browser, then try again."), { enableHighAccuracy: true, timeout: 15000, maximumAge: 5000 });
  };
  const stopSharingLocation = () => { if (locationWatch.current != null) navigator.geolocation.clearWatch(locationWatch.current); locationWatch.current = null; };
  return <div className="min-h-screen bg-gray-100 p-8"><h1 className="text-4xl font-bold">GPS Tracking</h1><p className="mb-5 text-gray-600">Active vehicles with GPS positions: <b>{allMapVehicles.length}</b></p>{error && <div className="mb-4 rounded bg-red-50 p-3 text-red-700">{error}</div>}
    <form onSubmit={trackVehicle} className="mb-5 rounded-xl bg-white p-5 shadow"><label className="mb-2 block font-semibold">Track in-progress vehicle number</label><div className="flex flex-col gap-3 sm:flex-row"><select required value={vehicleToTrack} onChange={(event) => setVehicleToTrack(event.target.value)} className="rounded border p-3 sm:flex-1"><option value="">Select in-progress vehicle number</option>{activeTrips.map((trip) => <option key={trip.trip_id} value={trip.vehicle_id}>{vehicleName(trip.vehicle_id)}</option>)}</select><button className="rounded bg-blue-600 px-6 py-3 font-medium text-white">Track Vehicle</button>{isDriver && <button type="button" onClick={shareDriverLocation} className="rounded bg-emerald-600 px-6 py-3 font-medium text-white">Start Live Location</button>}{isDriver && <button type="button" onClick={stopSharingLocation} className="rounded bg-slate-600 px-6 py-3 font-medium text-white">Stop Sharing</button>}</div><p className="mt-2 text-sm text-gray-500">Only vehicles on In Progress trips can be live tracked.{isDriver ? " Start Live Location from the driver's device to send accurate WebSocket GPS pings." : " Live positions are supplied by the assigned driver's device."}</p></form>
    <div className="mt-6 rounded-xl bg-white p-5 shadow">{selectedTrip && <div className="mb-4 rounded-lg border border-blue-200 bg-blue-50 p-4"><h2 className="font-semibold text-slate-900">Live route: {selectedTrip.start_location} to {selectedTrip.end_location}</h2><p className="mt-1 text-sm text-slate-700">{tripRoute ? `${tripRoute.distance_km} km · ${tripRoute.duration_display || `${tripRoute.duration_minutes} min`} · ETA ${new Date(tripRoute.eta).toLocaleString()}` : "Loading the route…"}</p>{tripRoute?.fallback && <p className="mt-1 text-sm text-amber-700">The routing service is unavailable, so this is a straight-line estimate.</p>}</div>}<MapView vehicles={mapVehicles} selectedVehicle={selectedVehicle} onSelectVehicle={setSelectedVehicle} routeGeometry={tripRoute?.geometry} startLocation={selectedTrip?.start_location} endLocation={selectedTrip?.end_location}/>{!filterVehicleId && <p className="mt-3 text-center text-sm text-gray-500">Showing all in-progress vehicles. Select one above to focus its live location.</p>}</div><div className="mt-6 rounded-xl bg-white p-6 shadow"><table className="w-full"><thead className="bg-gray-100"><tr><th className="p-3 text-left">Vehicle</th><th>Driver</th><th>Coordinates</th><th>Speed</th><th>Updated</th></tr></thead><tbody>{mapVehicles.map((item) => <tr key={item.tracking_id} className="border-b text-center"><td className="p-3 text-left">{item.vehicle}</td><td>{item.driver}</td><td>{item.location}</td><td>{item.speed ?? 0} km/h</td><td>{item.updated}</td></tr>)}{!mapVehicles.length && <tr><td colSpan="5" className="p-6 text-center text-gray-500">{filterVehicleId ? "No live GPS location is available for this vehicle." : "No in-progress vehicles have sent a GPS location yet."}</td></tr>}</tbody></table></div></div>;
}
