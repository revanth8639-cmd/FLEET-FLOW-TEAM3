import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api/axios";
import MapView from "../components/MapView";
import { useAuth } from "../context/AuthContext";

const emptyForm = { vehicle_id: "", driver_id: "", shipment_id: "", start_location: "", end_location: "", status: "Scheduled" };
const activeTrip = (trip) => ["Scheduled", "In Progress"].includes(trip.status);
const routeModes = ["Fastest Route", "Shortest Route", "Traffic Avoidance", "Fuel-Efficient Route"];
const formatDuration = (minutes) => {
  const totalMinutes = Math.max(0, Math.round(Number(minutes) || 0));
  const hours = Math.floor(totalMinutes / 60);
  const remainingMinutes = totalMinutes % 60;
  return hours ? `${hours} hour${hours === 1 ? "" : "s"} ${remainingMinutes} min` : `${remainingMinutes} min`;
};

export default function Trips() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const canManage = ["Admin", "FleetManager", "Dispatcher"].includes(user?.role);
  const canOperateTrip = ["Admin", "FleetManager", "Driver"].includes(user?.role);
  const canDelete = user?.role === "Admin";
  const [trips, setTrips] = useState([]); const [vehicles, setVehicles] = useState([]); const [drivers, setDrivers] = useState([]); const [shipments, setShipments] = useState([]);
  const [form, setForm] = useState(emptyForm); const [editingId, setEditingId] = useState(null); const [route, setRoute] = useState(null); const [routeType, setRouteType] = useState(routeModes[0]); const [search, setSearch] = useState(""); const [statusFilter, setStatusFilter] = useState("All"); const [busyId, setBusyId] = useState(null); const [error, setError] = useState("");

  async function load() {
    try {
      const [tripResponse, vehicleResponse, driverResponse, shipmentResponse] = await Promise.all([api.get("/trips/"), api.get("/vehicles/"), api.get("/drivers/"), api.get("/shipments/")]);
      setTrips(tripResponse.data); setVehicles(vehicleResponse.data); setDrivers(driverResponse.data); setShipments(shipmentResponse.data); setError("");
    } catch (requestError) { setError(requestError.response?.data?.detail || "Unable to load trip records."); }
  }

  useEffect(() => { const timer = window.setTimeout(() => void load(), 0); return () => window.clearTimeout(timer); }, []);
  const label = (items, id, key, field) => items.find((item) => item[`${key}_id`] === id)?.[field] || "Unknown";
  const shipmentLabel = (id) => { const shipment = shipments.find((item) => item.shipment_id === id); return shipment ? `${shipment.tracking_number} (${shipment.status})` : "Unknown"; };
  const selectedShipment = useMemo(() => shipments.find((shipment) => shipment.shipment_id === form.shipment_id) || null, [shipments, form.shipment_id]);
  const availableVehicles = useMemo(() => vehicles.filter((vehicle) => vehicle.vehicle_id === form.vehicle_id || (vehicle.status === "Available" && !trips.some((trip) => trip.vehicle_id === vehicle.vehicle_id && activeTrip(trip) && trip.trip_id !== editingId))), [vehicles, trips, form.vehicle_id, editingId]);
  const availableDrivers = useMemo(() => drivers.filter((driver) => driver.driver_id === form.driver_id || (driver.status === "Available" && !trips.some((trip) => trip.driver_id === driver.driver_id && activeTrip(trip) && trip.trip_id !== editingId))), [drivers, trips, form.driver_id, editingId]);
  const visibleTrips = useMemo(() => { const query = search.trim().toLowerCase(); return trips.filter((trip) => (statusFilter === "All" || (statusFilter === "Active" ? activeTrip(trip) : trip.status === "Completed")) && (!query || [label(vehicles, trip.vehicle_id, "vehicle", "registration_number"), label(drivers, trip.driver_id, "driver", "name"), trip.start_location, trip.end_location, trip.status].join(" ").toLowerCase().includes(query))).sort((a, b) => Number(activeTrip(b)) - Number(activeTrip(a))); }, [trips, vehicles, drivers, search, statusFilter]);

  const save = async (event) => { event.preventDefault(); setError(""); try { const payload = { ...form, start_time: null, end_time: null }; if (editingId) await api.put(`/trips/${editingId}`, payload); else await api.post("/trips/", payload); setForm(emptyForm); setEditingId(null); await load(); } catch (requestError) { setError(requestError.response?.data?.detail || "Unable to save trip."); } };
  const lifecycle = async (trip, action) => { try { setBusyId(trip.trip_id); setError(""); await api.post(`/trips/${trip.trip_id}/${action}`); await load(); } catch (requestError) { setError(requestError.response?.data?.detail || `Unable to ${action} trip.`); } finally { setBusyId(null); } };
  const remove = async (trip) => { if (!window.confirm(`Delete trip from ${trip.start_location} to ${trip.end_location}?`)) return; try { setBusyId(trip.trip_id); await api.delete(`/trips/${trip.trip_id}`); await load(); } catch (requestError) { setError(requestError.response?.data?.detail || "Unable to delete trip."); } finally { setBusyId(null); } };
  const trackTrip = (trip) => navigate(`/gps?vehicle_id=${encodeURIComponent(trip.vehicle_id)}&trip_id=${encodeURIComponent(trip.trip_id)}`);

  return <div className="min-h-screen bg-gray-100 p-8">
    <h1 className="text-4xl font-bold">Trip Management</h1>
    <p className="mb-5 text-gray-600">Total trips: <b>{trips.length}</b> | Active or assigned: <b>{trips.filter(activeTrip).length}</b> | Completed: <b>{trips.filter((trip) => trip.status === "Completed").length}</b></p>
    {error && <div className="mb-4 rounded bg-red-50 p-3 text-red-700">{error}</div>}
    {canManage && <form onSubmit={save} className="grid grid-cols-1 gap-4 rounded-xl bg-white p-6 shadow md:grid-cols-2">
      <select required value={form.vehicle_id} onChange={(event) => setForm({ ...form, vehicle_id: event.target.value })} className="rounded border p-3"><option value="">Select available vehicle</option>{availableVehicles.map((vehicle) => <option key={vehicle.vehicle_id} value={vehicle.vehicle_id}>{vehicle.registration_number}</option>)}</select>
      <select required value={form.driver_id} onChange={(event) => setForm({ ...form, driver_id: event.target.value })} className="rounded border p-3"><option value="">Select available driver</option>{availableDrivers.map((driver) => <option key={driver.driver_id} value={driver.driver_id}>{driver.name}</option>)}</select>
      <select required value={form.shipment_id} onChange={(event) => { const shipment = shipments.find((item) => item.shipment_id === event.target.value); setForm({ ...form, shipment_id: event.target.value, start_location: shipment?.source || "", end_location: shipment?.destination || "" }); }} className="rounded border p-3"><option value="">Select shipment by tracking ID</option>{shipments.filter((shipment) => shipment.shipment_id === form.shipment_id || !["Delivered", "Cancelled"].includes(shipment.status)).map((shipment) => <option key={shipment.shipment_id} value={shipment.shipment_id}>{shipment.tracking_number}</option>)}</select>
      <select value={form.status} onChange={(event) => setForm({ ...form, status: event.target.value })} className="rounded border p-3"><option>Scheduled</option></select>
      <input required readOnly placeholder="Start location" value={form.start_location} className="rounded border bg-gray-50 p-3" />
      <input required readOnly placeholder="End location" value={form.end_location} className="rounded border bg-gray-50 p-3" />
      {selectedShipment && <div className="col-span-full rounded-lg border border-blue-200 bg-blue-50 p-4 text-sm text-slate-800">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2"><h2 className="text-base font-semibold">Selected shipment details</h2><span className="rounded-full bg-blue-600 px-3 py-1 font-medium text-white">Tracking ID: {selectedShipment.tracking_number}</span></div>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          <p><span className="font-medium">Shipment status:</span> {selectedShipment.status}</p>
          <p><span className="font-medium">Source:</span> {selectedShipment.source}</p>
          <p><span className="font-medium">Destination:</span> {selectedShipment.destination}</p>
          <p><span className="font-medium">Expected delivery:</span> {selectedShipment.expected_delivery_at ? new Date(selectedShipment.expected_delivery_at).toLocaleString() : selectedShipment.eta || "Not provided"}</p>
        </div>
      </div>}
      <div className="flex gap-2"><button className="rounded bg-blue-600 px-4 py-3 text-white">{editingId ? "Update Trip" : "Assign Trip"}</button>{editingId && <button type="button" onClick={() => { setForm(emptyForm); setEditingId(null); }} className="rounded bg-gray-200 px-4">Cancel</button>}</div>
    </form>}
    <section className="mt-6 rounded-xl bg-white p-6 shadow"><div className="mb-4 flex flex-col gap-3 md:flex-row md:items-center"><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search trips, drivers, vehicles, or locations" className="rounded border p-2 md:flex-1" /><select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)} className="rounded border p-2"><option value="All">All trips</option><option value="Active">Active trips</option><option value="Completed">Completed trips</option></select><label className="font-semibold">Route mode</label><select value={routeType} onChange={(event) => setRouteType(event.target.value)} className="rounded border p-2">{routeModes.map((mode) => <option key={mode}>{mode}</option>)}</select></div>
      <div className="overflow-x-auto"><table className="w-full"><thead className="bg-gray-100"><tr><th className="p-3">S.No</th><th className="text-left">Vehicle</th><th>Driver</th><th>Shipment details</th><th>Route</th><th>Status</th><th>Actions</th></tr></thead><tbody>{visibleTrips.map((trip, index) => <tr className="border-b text-center" key={trip.trip_id}><td className="p-3 font-semibold text-gray-500">{index + 1}</td><td className="p-3 text-left">{label(vehicles, trip.vehicle_id, "vehicle", "registration_number")}</td><td>{label(drivers, trip.driver_id, "driver", "name")}</td><td className="p-3 text-left"><p className="font-medium">{shipmentLabel(trip.shipment_id)}</p></td><td>{trip.start_location} to {trip.end_location}</td><td>{trip.status}</td><td className="p-2">{trip.status === "In Progress" && <button onClick={() => trackTrip(trip)} className="mr-2 rounded bg-blue-600 px-3 py-1 text-white">Live Tracking</button>}{canOperateTrip && trip.status === "Scheduled" && <button onClick={() => void lifecycle(trip, "start")} disabled={busyId === trip.trip_id} className="mr-2 rounded bg-green-600 px-3 py-1 text-white">Start</button>}{canOperateTrip && trip.status === "In Progress" && <button onClick={() => void lifecycle(trip, "end")} disabled={busyId === trip.trip_id} className="mr-2 rounded bg-purple-600 px-3 py-1 text-white">Complete</button>}{canManage && trip.status === "Scheduled" && <button onClick={() => { setEditingId(trip.trip_id); setForm({ vehicle_id: trip.vehicle_id, driver_id: trip.driver_id, shipment_id: trip.shipment_id, start_location: trip.start_location, end_location: trip.end_location, status: "Scheduled" }); }} className="mr-2 rounded bg-amber-500 px-3 py-1 text-white">Edit</button>}{canDelete && <button onClick={() => void remove(trip)} disabled={busyId === trip.trip_id} className="rounded bg-red-600 px-3 py-1 text-white">Delete</button>}</td></tr>)}{!visibleTrips.length && <tr><td colSpan="7" className="p-6 text-center text-gray-500">No trips found.</td></tr>}</tbody></table></div>
    </section>
    {route && <section className="mt-6 rounded-xl bg-white p-6 shadow"><div className="mb-4 flex justify-between gap-4"><div><h2 className="text-xl font-bold">{route.trip.start_location} to {route.trip.end_location}</h2><p className="text-gray-600">{route.route_type}: {route.distance_km} km - {route.duration_display || formatDuration(route.duration_minutes)} - ETA {new Date(route.eta).toLocaleString()}</p>{route.route_mode_note && <p className="mt-1 text-sm text-amber-700">{route.route_mode_note}</p>}{route.fallback && <p className="mt-1 text-sm text-amber-700">Showing an estimated route because the routing service was unavailable.</p>}</div><button onClick={() => setRoute(null)} className="h-fit text-gray-600">Close</button></div><div className="mb-4 flex gap-4 text-sm"><span className="flex items-center gap-2"><span className="flex h-6 w-6 items-center justify-center rounded-full bg-green-600 font-bold text-white">S</span> Start</span><span className="flex items-center gap-2"><span className="flex h-6 w-6 items-center justify-center rounded-full bg-red-600 font-bold text-white">E</span> Destination</span></div>{route.alternatives?.length > 0 && <div className="mb-4"><p className="mb-2 font-semibold">Available route options</p><div className="grid gap-3 md:grid-cols-3">{route.alternatives.map((option) => <div key={option.id} className={`rounded-lg border p-3 ${option.id === route.selected_alternative ? "border-blue-600 bg-blue-50" : "border-gray-200"}`}><p className="font-medium">{option.id === route.selected_alternative ? "Selected route" : `Alternative ${option.id + 1}`}</p><p className="text-sm text-gray-600">{option.distance_km} km - {formatDuration(option.duration_minutes)}</p></div>)}</div></div>}{route.traffic_level && <div className="mb-4 grid gap-4 md:grid-cols-2"><div className={`rounded-lg p-4 ${route.traffic_level === "High" ? "bg-red-50 text-red-800" : route.traffic_level === "Moderate" ? "bg-amber-50 text-amber-800" : "bg-green-50 text-green-800"}`}><p className="font-semibold">Traffic estimate: {route.traffic_level}</p><p className="text-sm">Estimated delay: {route.traffic_delay_minutes} min - adjusted duration: {route.adjusted_duration_display || formatDuration(route.adjusted_duration_minutes)}</p></div><div className="rounded-lg bg-slate-50 p-4 text-slate-800"><p className="font-semibold">Estimated toll gates: {route.toll_gates_estimate}</p><p className="text-sm">{route.routing_provider ? `Route provider: ${route.routing_provider}` : "Planning estimate based on route distance."}</p></div></div>}<MapView routeGeometry={route.geometry} startLocation={route.trip.start_location} endLocation={route.trip.end_location} /></section>}
  </div>;
}
