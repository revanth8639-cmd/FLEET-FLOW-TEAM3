import { useEffect, useState } from "react";
import api from "../api/axios";
import { useAuth } from "../context/AuthContext";

const emptyForm = { vehicle_id: "", filled_by: "", fuel_amount: "", fuel_cost: "", fuel_station: "", fuel_date: "" };

export default function FuelRecords() {
  const { user } = useAuth();
  const isDriver = user?.role === "Driver";
  const isReadOnly = user?.role === "Dispatcher";
  const canSelectDriver = ["Admin", "FleetManager"].includes(user?.role);
  const canDelete = user?.role === "Admin";
  const [records, setRecords] = useState([]);
  const [vehicles, setVehicles] = useState([]);
  const [drivers, setDrivers] = useState([]);
  const [form, setForm] = useState(emptyForm);
  const [editingId, setEditingId] = useState(null);
  const [showForm, setShowForm] = useState(false);
  const [search, setSearch] = useState("");
  const [error, setError] = useState("");

  async function loadData() {
    try {
      const [fuelResponse, vehicleResponse, driverResponse] = await Promise.all([api.get("/fuel/"), api.get("/vehicles/"), api.get("/drivers/")]);
      setRecords(fuelResponse.data);
      setVehicles(vehicleResponse.data);
      setDrivers(driverResponse.data);
      setError("");
    } catch (requestError) {
      setError(requestError.response?.data?.detail || "Unable to load fuel records.");
    }
  }

  useEffect(() => {
    const initialLoad = window.setTimeout(() => void loadData(), 0);
    const interval = window.setInterval(() => void loadData(), 30000);
    return () => { window.clearTimeout(initialLoad); window.clearInterval(interval); };
  }, []);

  async function saveRecord(event) {
    event.preventDefault();
    const payload = { ...form, fuel_amount: Number(form.fuel_amount), fuel_cost: Number(form.fuel_cost), fuel_date: form.fuel_date ? new Date(form.fuel_date).toISOString() : null };
    try {
      if (editingId) {
        const updatePayload = { fuel_amount: payload.fuel_amount, fuel_cost: payload.fuel_cost, fuel_station: payload.fuel_station, fuel_date: payload.fuel_date, filled_by: payload.filled_by || null };
        await api.put(`/fuel/${editingId}`, updatePayload);
      } else {
        await api.post("/fuel/", payload);
      }
      setForm(emptyForm);
      setEditingId(null);
      setShowForm(false);
      await loadData();
    } catch (requestError) {
      setError(requestError.response?.data?.detail || "Unable to save fuel record.");
    }
  }

  async function deleteRecord(record) {
    if (!window.confirm(`Delete fuel record for ${vehicleName(record.vehicle_id)}?`)) return;
    try {
      await api.delete(`/fuel/${record.fuel_id}`);
      await loadData();
    } catch (requestError) {
      setError(requestError.response?.data?.detail || "Unable to delete fuel record.");
    }
  }

  const vehicleName = (id) => vehicles.find((vehicle) => vehicle.vehicle_id === id)?.registration_number || id;
  const driverName = (vehicleId) => drivers.find((driver) => driver.vehicle_id === vehicleId)?.name || "—";
  // The vehicle endpoint is already scoped to the current driver. This keeps
  // persistent Fleet Manager assignments available even without an active trip.
  const selectableVehicles = vehicles;
  const filteredRecords = records.filter((record) => `${vehicleName(record.vehicle_id)} ${driverName(record.vehicle_id)} ${record.fuel_station}`.toLowerCase().includes(search.toLowerCase()));
  const totalFuelCost = records.reduce((total, record) => total + (record.fuel_cost || 0), 0);
  const totalFuelVolume = records.reduce((total, record) => total + (record.fuel_amount || 0), 0);

  return <div className="p-8 bg-gray-100 min-h-screen">
    <h1 className="text-4xl font-bold mb-2">Fuel Records</h1>
    <div className="flex flex-wrap items-center justify-between gap-4 mb-6"><p className="text-gray-600">{isReadOnly ? "Fuel records are available for operational review only." : isDriver ? "Select the vehicle assigned to you by Fleet Manager to record fuel details." : "Fuel entries submitted or edited by drivers appear here automatically."}</p>{!isReadOnly && <button type="button" onClick={() => { setForm(emptyForm); setEditingId(null); setShowForm(true); }} disabled={isDriver && !selectableVehicles.length} className="bg-blue-600 text-white rounded-lg px-5 py-3 disabled:bg-gray-400">Add Fuel Record</button>}</div>
    {error && <div className="mb-4 rounded bg-red-50 p-3 text-red-700">{error}</div>}
    <section className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-2">
      <div className="rounded-lg bg-white p-5 shadow-sm"><p className="text-xs font-semibold uppercase text-slate-500">Total Fuel Cost</p><p className="mt-2 text-2xl font-bold text-emerald-700">Rs.{totalFuelCost.toFixed(2)}</p></div>
      <div className="rounded-lg bg-white p-5 shadow-sm"><p className="text-xs font-semibold uppercase text-slate-500">Fuel Volume</p><p className="mt-2 text-2xl font-bold text-violet-700">{totalFuelVolume.toFixed(1)} L</p></div>
    </section>
    {showForm && <form onSubmit={saveRecord} className="bg-white rounded-xl shadow p-6 grid grid-cols-1 md:grid-cols-2 gap-4">
      <select required value={form.vehicle_id} disabled={Boolean(editingId)} onChange={(event) => setForm({ ...form, vehicle_id: event.target.value })} className="border rounded-lg p-3 disabled:bg-gray-100">
        <option value="">Select vehicle</option>
        {selectableVehicles.map((vehicle) => <option key={vehicle.vehicle_id} value={vehicle.vehicle_id}>{vehicle.registration_number}{vehicle.shipment ? ` — Shipment ${vehicle.shipment}` : ""}</option>)}
      </select>
      {canSelectDriver && <select value={form.filled_by} onChange={(event) => setForm({ ...form, filled_by: event.target.value })} className="border rounded-lg p-3">
        <option value="">Select driver (optional)</option>
        {drivers.map((driver) => <option key={driver.driver_id} value={driver.name}>{driver.name}</option>)}
      </select>}
      {isDriver && !selectableVehicles.length && <p className="md:col-span-2 text-sm text-amber-700">Fleet Manager has not assigned a vehicle to you yet.</p>}
      <input required type="number" min="0" step="0.01" placeholder="Fuel quantity (L)" value={form.fuel_amount} onChange={(event) => setForm({ ...form, fuel_amount: event.target.value })} className="border rounded-lg p-3" />
      <input required type="number" min="0" step="0.01" placeholder="Amount" value={form.fuel_cost} onChange={(event) => setForm({ ...form, fuel_cost: event.target.value })} className="border rounded-lg p-3" />
      <input required placeholder="Fuel station" value={form.fuel_station} onChange={(event) => setForm({ ...form, fuel_station: event.target.value })} className="border rounded-lg p-3" />
      <input type="datetime-local" value={form.fuel_date} onChange={(event) => setForm({ ...form, fuel_date: event.target.value })} className="border rounded-lg p-3" />
      <div className="flex gap-3"><button className="bg-blue-600 text-white rounded-lg px-5 py-3">{editingId ? "Update Fuel Record" : "Save Fuel Record"}</button><button type="button" onClick={() => { setForm(emptyForm); setEditingId(null); setShowForm(false); }} className="bg-gray-200 rounded-lg px-5">Cancel</button></div>
    </form>}
    <div className="bg-white rounded-xl shadow p-6 mt-6"><input placeholder="Search vehicle, driver, or station..." value={search} onChange={(event) => setSearch(event.target.value)} className="border rounded-lg p-3 w-full mb-5" />
      <div className={`overflow-x-auto ${isReadOnly ? "[&_th:last-child]:hidden [&_td:last-child]:hidden" : ""}`}><table className="w-full"><thead className="bg-gray-100"><tr><th className="p-3 text-left">Vehicle</th><th>Driver</th><th>Quantity</th><th>Amount</th><th>Station</th><th>Date</th><th>Actions</th></tr></thead><tbody>
        {filteredRecords.map((record) => <tr key={record.fuel_id} className="border-b text-center"><td className="p-3 text-left">{vehicleName(record.vehicle_id)}</td><td>{record.filled_by || driverName(record.vehicle_id)}</td><td>{record.fuel_amount} L</td><td>₹{record.fuel_cost}</td><td>{record.fuel_station}</td><td>{new Date(record.fuel_date).toLocaleString()}</td><td><button onClick={() => { setEditingId(record.fuel_id); setForm({ vehicle_id: record.vehicle_id, filled_by: record.filled_by || "", fuel_amount: record.fuel_amount, fuel_cost: record.fuel_cost, fuel_station: record.fuel_station, fuel_date: record.fuel_date?.slice(0, 16) || "" }); setShowForm(true); }} className="mr-2 rounded bg-yellow-500 px-3 py-1 text-white">Edit</button>{canDelete && <button onClick={() => void deleteRecord(record)} className="rounded bg-red-600 px-3 py-1 text-white">Delete</button>}</td></tr>)}
        {!filteredRecords.length && <tr><td colSpan="7" className="p-6 text-center text-gray-500">No fuel records found.</td></tr>}
      </tbody></table></div>
    </div>
  </div>;
}
