import { useEffect, useState } from "react";
import { createVehicle, deleteVehicle, getVehicles, updateVehicle } from "../api/vehicleApi";
import { useAuth } from "../context/AuthContext";

const emptyForm = { registration_number: "", vehicle_type: "", capacity: "", fuel_type: "", status: "Available" };

export default function Vehicles() {
  const { user } = useAuth();
  const canManage = ["Admin", "FleetManager"].includes(user?.role);
  const [vehicles, setVehicles] = useState([]);
  const [form, setForm] = useState(emptyForm);
  const [editingId, setEditingId] = useState(null);
  const [error, setError] = useState("");
  const loadVehicles = async () => { try { setVehicles(await getVehicles()); } catch (requestError) { setError(requestError.response?.data?.detail || "Failed to load vehicles."); } };
  useEffect(() => { const timer = setTimeout(() => { void loadVehicles(); }, 0); return () => clearTimeout(timer); }, []);
  const reset = () => { setForm(emptyForm); setEditingId(null); };
  const save = async (event) => { event.preventDefault(); setError(""); try { editingId ? await updateVehicle(editingId, form) : await createVehicle(form); reset(); await loadVehicles(); } catch (requestError) { setError(requestError.response?.data?.detail || "Unable to save vehicle."); } };
  const remove = async (vehicle) => { if (!window.confirm(`Delete ${vehicle.registration_number}?`)) return; setError(""); try { await deleteVehicle(vehicle.vehicle_id); await loadVehicles(); } catch (requestError) { setError(requestError.response?.data?.detail || "Unable to delete vehicle."); } };

  return <div className="p-8"><h1 className="text-3xl font-bold">Vehicle Management</h1><p className="text-gray-600 mb-5">Total vehicles: <b>{vehicles.length}</b> | Available: <b>{vehicles.filter((item) => item.status === "Available").length}</b></p>{error && <div className="mb-4 rounded bg-red-50 p-3 text-red-700">{error}</div>}
    {canManage && <form onSubmit={save} className="grid grid-cols-1 gap-3 mb-8 md:grid-cols-3"><input required placeholder="Registration" value={form.registration_number} onChange={(event) => setForm({ ...form, registration_number: event.target.value })} className="border p-2 rounded"/><input required placeholder="Vehicle type" value={form.vehicle_type} onChange={(event) => setForm({ ...form, vehicle_type: event.target.value })} className="border p-2 rounded"/><input required placeholder="Capacity" value={form.capacity} onChange={(event) => setForm({ ...form, capacity: event.target.value })} className="border p-2 rounded"/><input required placeholder="Fuel type" value={form.fuel_type} onChange={(event) => setForm({ ...form, fuel_type: event.target.value })} className="border p-2 rounded"/><select value={form.status} onChange={(event) => setForm({ ...form, status: event.target.value })} className="border p-2 rounded"><option>Available</option><option>Maintenance</option><option>Unavailable</option></select><div className="flex gap-2"><button className="rounded bg-blue-600 px-4 text-white">{editingId ? "Update Vehicle" : "Add Vehicle"}</button>{editingId && <button type="button" onClick={reset} className="rounded bg-gray-200 px-4">Cancel</button>}</div></form>}
    <div className="overflow-x-auto"><table className="w-full border"><thead className="bg-blue-600 text-white"><tr><th className="p-3 text-left">Registration</th><th>Vehicle Type</th><th>Capacity</th><th>Fuel Type</th><th>Status</th>{canManage && <th>Actions</th>}</tr></thead><tbody>{vehicles.map((vehicle) => <tr key={vehicle.vehicle_id} className="border-b text-center"><td className="p-3 text-left">{vehicle.registration_number}</td><td>{vehicle.vehicle_type}</td><td>{vehicle.capacity}</td><td>{vehicle.fuel_type}</td><td>{vehicle.status}</td>{canManage && <td><button onClick={() => { setEditingId(vehicle.vehicle_id); setForm({ registration_number: vehicle.registration_number, vehicle_type: vehicle.vehicle_type, capacity: vehicle.capacity, fuel_type: vehicle.fuel_type, status: vehicle.status }); }} className="mr-2 rounded bg-amber-500 px-3 py-1 text-white">Edit</button><button onClick={() => void remove(vehicle)} className="rounded bg-red-600 px-3 py-1 text-white">Delete</button></td>}</tr>)}{!vehicles.length && <tr><td colSpan={canManage ? 6 : 5} className="p-6 text-center">No vehicles found.</td></tr>}</tbody></table></div></div>;
}
