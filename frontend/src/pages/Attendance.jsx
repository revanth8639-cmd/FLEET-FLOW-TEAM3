import { useEffect, useState } from "react";
import api from "../api/axios";
import { useAuth } from "../context/AuthContext";

const emptyForm = { driver_id: "", date: "", status: "Present" };

export default function Attendance() {
  const { user } = useAuth();
  const canManage = ["Admin", "FleetManager"].includes(user?.role);
  const [records, setRecords] = useState([]);
  const [drivers, setDrivers] = useState([]);
  const [trips, setTrips] = useState([]);
  const [vehicles, setVehicles] = useState([]);
  const [form, setForm] = useState(emptyForm);
  const [editingId, setEditingId] = useState(null);
  const [expandedDriver, setExpandedDriver] = useState(null);
  const [error, setError] = useState("");

  async function load() {
    try {
      const [attendance, driverData, tripData, vehicleData] = await Promise.all([api.get("/attendance/"), api.get("/drivers/"), api.get("/trips/"), api.get("/vehicles/")]);
      setRecords(Array.isArray(attendance.data) ? attendance.data : []);
      setDrivers(Array.isArray(driverData.data) ? driverData.data : []);
      setTrips(Array.isArray(tripData.data) ? tripData.data : []);
      setVehicles(Array.isArray(vehicleData.data) ? vehicleData.data : []);
      setError("");
    } catch (requestError) {
      setError(requestError.response?.data?.detail || "Unable to load attendance.");
    }
  }

  useEffect(() => {
    const timer = window.setTimeout(() => void load(), 0);
    return () => window.clearTimeout(timer);
  }, []);

  const driverName = (id) => drivers.find((driver) => String(driver.driver_id) === String(id))?.name || "Unknown driver";
  const activeTripVehicle = (driverId) => {
    const activeTrip = trips.find((trip) => String(trip.driver_id) === String(driverId) && ["Scheduled", "In Progress"].includes(trip.status));
    if (!activeTrip) return "No active trip";
    return vehicles.find((vehicle) => String(vehicle.vehicle_id) === String(activeTrip.vehicle_id))?.registration_number || "Assigned vehicle";
  };
  const uniqueDrivers = Object.values(drivers.reduce((groups, driver) => {
    const key = driver.name.trim().toLowerCase();
    if (!groups[key]) groups[key] = driver;
    return groups;
  }, {}));
  const groups = Object.values(records.reduce((result, record) => {
    const name = driverName(record.driver_id);
    const key = name.trim().toLowerCase();
    if (!result[key]) result[key] = { name, driverIds: [], records: [] };
    if (!result[key].driverIds.includes(record.driver_id)) result[key].driverIds.push(record.driver_id);
    result[key].records.push(record);
    return result;
  }, {})).sort((a, b) => a.name.localeCompare(b.name));

  const save = async (event) => {
    event.preventDefault();
    setError("");
    try {
      const payload = { driver_id: form.driver_id, date: form.date, status: form.status, check_in: new Date(`${form.date}T00:00:00`).toISOString(), check_out: null };
      if (editingId) await api.put(`/attendance/${editingId}`, payload);
      else await api.post("/attendance/", payload);
      setForm(emptyForm);
      setEditingId(null);
      await load();
    } catch (requestError) {
      setError(requestError.response?.data?.detail || "Unable to save attendance.");
    }
  };

  const edit = (record) => {
    setEditingId(record.attendance_id);
    setForm({ driver_id: record.driver_id, date: record.date || record.check_in?.slice(0, 10) || "", status: record.status });
  };

  const remove = async (id) => {
    if (!window.confirm("Delete this attendance record?")) return;
    try {
      await api.delete(`/attendance/${id}`);
      await load();
    } catch (requestError) {
      setError(requestError.response?.data?.detail || "Unable to delete attendance.");
    }
  };

  return <div className="min-h-screen bg-gray-100 p-8"><h1 className="mb-2 text-4xl font-bold">Driver Attendance</h1><p className="mb-6 text-gray-600">{canManage ? "Mark Present, Absent, or Leave for any registered driver." : "Your attendance history."}</p>{error && <div className="mb-4 rounded bg-red-50 p-3 text-red-700">{error}</div>}{canManage && <form onSubmit={save} className="grid gap-4 rounded-xl bg-white p-6 md:grid-cols-3"><select required value={form.driver_id} onChange={(event) => setForm({ ...form, driver_id: event.target.value })} className="rounded-lg border p-3"><option value="">Select driver</option>{uniqueDrivers.map((driver) => <option key={driver.driver_id} value={driver.driver_id}>{driver.name}</option>)}</select><select value={form.status} onChange={(event) => setForm({ ...form, status: event.target.value })} className="rounded-lg border p-3"><option>Present</option><option>Absent</option><option>Leave</option></select><input required type="date" value={form.date} onChange={(event) => setForm({ ...form, date: event.target.value })} className="rounded-lg border p-3" /><div className="flex gap-3 md:col-span-3"><button className="rounded-lg bg-blue-600 p-3 text-white">{editingId ? "Update Attendance" : "Mark Attendance"}</button>{editingId && <button type="button" onClick={() => { setForm(emptyForm); setEditingId(null); }} className="rounded-lg bg-gray-200 px-4">Cancel</button>}</div></form>}<div className="mt-6 overflow-x-auto rounded-xl bg-white p-6 shadow"><table className="w-full"><thead className="bg-gray-100"><tr><th className="p-3">S.No</th><th className="text-left">Driver</th><th>Active trip vehicle</th><th>Latest date</th><th>Status</th>{canManage && <th>Actions</th>}</tr></thead><tbody>{groups.map((group, index) => { const history = [...group.records].sort((a, b) => String(b.date || b.check_in).localeCompare(String(a.date || a.check_in))); const latest = history[0]; const isOpen = expandedDriver === group.name; return <><tr className="border-b text-center" key={group.name}><td className="p-3 font-semibold text-gray-500">{index + 1}</td><td className="text-left"><button type="button" onClick={() => setExpandedDriver(isOpen ? null : group.name)} className="font-semibold text-blue-700 underline">{group.name}</button></td><td>{activeTripVehicle(latest?.driver_id || group.driverIds[0])}</td><td>{latest?.date || latest?.check_in?.slice(0, 10) || "-"}</td><td>{latest?.status || "-"}</td>{canManage && <td>{latest && <button onClick={() => edit(latest)} className="rounded bg-yellow-500 px-3 py-1 text-white">Edit</button>}</td>}</tr>{isOpen && <tr key={`${group.name}-history`}><td colSpan={canManage ? "6" : "5"} className="bg-slate-50 p-4"><h3 className="mb-2 font-semibold">{group.name} attendance history</h3><div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">{history.map((record) => <div key={record.attendance_id} className="rounded border bg-white p-3"><b>{record.date || record.check_in?.slice(0, 10)}</b><p className="text-sm text-slate-600">{record.status}</p>{canManage && <button onClick={() => void remove(record.attendance_id)} className="mt-2 text-sm text-red-600">Delete</button>}</div>)}</div></td></tr>}</>; })}{!groups.length && <tr><td colSpan={canManage ? "6" : "5"} className="p-6 text-center text-gray-500">No attendance records yet.</td></tr>}</tbody></table></div></div>;
}
