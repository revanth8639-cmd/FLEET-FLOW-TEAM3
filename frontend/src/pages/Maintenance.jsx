import { useEffect, useState } from "react";
import { useAuth } from "../context/AuthContext";
import api from "../api/axios";

const emptyForm = { vehicle_id: "", service_type: "", description: "", service_date: "", next_service_date: "", cost: "", status: "Scheduled" };
const statusClass = { Scheduled: "bg-amber-100 text-amber-800", Pending: "bg-amber-100 text-amber-800", "In Progress": "bg-slate-200 text-slate-700", Completed: "bg-emerald-100 text-emerald-800", Resolved: "bg-emerald-100 text-emerald-800" };
const isResolved = (status) => ["completed", "resolved"].includes((status || "").toLowerCase());
const alertClass = (alertStatus) => alertStatus === "Overdue" ? "text-rose-700" : "text-amber-700";
const dueDateFor = (record) => {
  const defaultDue = record.service_date ? new Date(new Date(record.service_date).getTime() + 5 * 24 * 60 * 60 * 1000) : null;
  return record.alert_due_date || defaultDue?.toISOString() || record.next_service_date || null;
};
const alertStatusFor = (record) => {
  if (isResolved(record.status)) return null;
  const dueDate = dueDateFor(record);
  if (!dueDate) return null;
  const remaining = new Date(dueDate).getTime() - Date.now();
  if (remaining <= 0) return "Overdue";
  const days = Math.ceil(remaining / (24 * 60 * 60 * 1000));
  if (days <= 1) return "Due tomorrow";
  return days <= 5 ? `Due in ${days} days` : null;
};

const formatDate = (value) => value ? new Date(value).toLocaleString() : "-";
const serviceDateValue = (record) => {
  const parsed = Date.parse(record.service_date || "");
  return Number.isNaN(parsed) ? Number.MAX_SAFE_INTEGER : parsed;
};

export default function Maintenance() {
  const { user } = useAuth();
  const [records, setRecords] = useState([]);
  const [vehicles, setVehicles] = useState([]);
  const [form, setForm] = useState(emptyForm);
  const [editingId, setEditingId] = useState(null);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("All");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [busyId, setBusyId] = useState(null);
  const [refreshing, setRefreshing] = useState(false);

  const canManage = ["Admin", "FleetManager"].includes(user?.role);
  const canDelete = user?.role === "Admin";

  async function loadData() {
    try {
      const [maintenance, vehicleList] = await Promise.all([api.get("/maintenance/"), api.get("/vehicles/")]);
      setRecords(Array.isArray(maintenance.data) ? maintenance.data : []);
      setVehicles(Array.isArray(vehicleList.data) ? vehicleList.data : []);
      setError("");
    } catch (requestError) {
      setError(requestError.response?.data?.detail || "Unable to load maintenance records.");
    }
  }

  async function refreshData() {
    setRefreshing(true);
    try {
      await loadData();
    } finally {
      setRefreshing(false);
    }
  }

  useEffect(() => {
    const timer = window.setTimeout(() => void loadData(), 0);
    return () => window.clearTimeout(timer);
  }, []);

  async function scheduleMaintenance(event) {
    event.preventDefault();
    setSaving(true);
    try {
      const payload = {
        ...form,
        cost: form.cost ? Number(form.cost) : null,
        service_date: form.service_date ? new Date(form.service_date).toISOString() : null,
        next_service_date: form.next_service_date ? new Date(form.next_service_date).toISOString() : null,
      };
      if (editingId) await api.put(`/maintenance/${editingId}`, payload);
      else await api.post("/maintenance/", payload);
      setForm(emptyForm);
      setEditingId(null);
      await loadData();
    } catch (requestError) {
      setError(requestError.response?.data?.detail || "Unable to schedule maintenance.");
    } finally {
      setSaving(false);
    }
  }

  function editRecord(record) {
    setEditingId(record.maintenance_id);
    setForm({ vehicle_id: record.vehicle_id, service_type: record.service_type || "", description: record.description || "", service_date: record.service_date ? record.service_date.slice(0, 16) : "", next_service_date: record.next_service_date ? record.next_service_date.slice(0, 16) : "", cost: record.cost ?? "", status: record.status || "Scheduled" });
  }

  async function updateStatus(record, status) {
    setBusyId(record.maintenance_id);
    try {
      await api.put(`/maintenance/${record.maintenance_id}`, { status });
      await loadData();
    } catch (requestError) {
      setError(requestError.response?.data?.detail || "Unable to update maintenance status.");
    } finally {
      setBusyId(null);
    }
  }

  async function deleteRecord(record) {
    if (!window.confirm(`Delete ${record.service_type} for this vehicle?`)) return;
    try {
      await api.delete(`/maintenance/${record.maintenance_id}`);
      await loadData();
    } catch (requestError) {
      setError(requestError.response?.data?.detail || "Unable to delete maintenance record.");
    }
  }

  const vehicleName = (id) => vehicles.find((vehicle) => vehicle.vehicle_id === id)?.registration_number || "Unknown vehicle";
  const activeAlerts = records.filter((record) => alertStatusFor(record));
  const totalMaintenanceCost = records.reduce((total, record) => total + (record.cost || 0), 0);
  const visibleRecords = records.filter((record) => {
    const query = `${vehicleName(record.vehicle_id)} ${record.service_type} ${record.status}`.toLowerCase();
    return query.includes(search.trim().toLowerCase()) && (statusFilter === "All" || record.status === statusFilter);
  }).sort((left, right) => serviceDateValue(left) - serviceDateValue(right));

  return <main className="min-h-screen bg-slate-50 p-5 md:p-8">
    <div className="mb-6 flex flex-col gap-4 md:flex-row md:items-start md:justify-between"><div><h1 className="text-3xl font-bold text-slate-900">Fleet Maintenance</h1><p className="mt-1 text-slate-500">Track vehicle servicing and maintenance alerts.</p></div><button type="button" disabled={refreshing} onClick={() => void refreshData()} className="rounded-md border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60">{refreshing ? "Refreshing..." : "Refresh"}</button></div>
    {error && <div className="mb-5 rounded-md border border-red-200 bg-red-50 px-4 py-3 text-red-700">{error}</div>}
    {canManage && <section className="mb-5 rounded-lg border border-amber-200 bg-amber-50 p-4"><div className="mb-3 flex items-center justify-between"><div><h2 className="font-semibold text-amber-950">Active Maintenance Service Alerts ({activeAlerts.length})</h2><p className="text-xs text-amber-800">Due within five days or overdue maintenance requires attention.</p></div><span className="rounded-full bg-amber-700 px-2.5 py-1 text-xs font-semibold text-white">{activeAlerts.length} Active</span></div><div className="grid gap-3 md:grid-cols-2">{activeAlerts.map((record) => { const alertStatus = alertStatusFor(record); return <div key={record.maintenance_id} className="flex items-center justify-between rounded-md bg-white px-3 py-2 shadow-sm"><div><p className="text-sm font-semibold text-slate-800">{vehicleName(record.vehicle_id)} - {record.service_type}</p><p className={`text-xs ${alertClass(alertStatus)}`}><span aria-hidden="true">●</span> {alertStatus}</p></div>{record.status === "In Progress" ? <button onClick={() => void updateStatus(record, "Completed")} className="rounded-md bg-violet-600 px-3 py-1.5 text-sm font-semibold text-white">Complete</button> : <button onClick={() => void updateStatus(record, "In Progress")} className="rounded-md bg-violet-600 px-3 py-1.5 text-sm font-semibold text-white">Start</button>}</div>; })}{!activeAlerts.length && <p className="text-sm text-amber-800">No due or overdue maintenance alerts.</p>}</div></section>}
    <section className="mb-5 grid grid-cols-1 gap-3 sm:grid-cols-2"><div className="rounded-lg bg-white p-4 shadow-sm"><p className="text-xs font-semibold uppercase text-slate-500">Maintenance Expense</p><p className="mt-2 text-2xl font-bold text-slate-900">Rs.{totalMaintenanceCost.toFixed(2)}</p></div><div className="rounded-lg bg-white p-4 shadow-sm"><p className="text-xs font-semibold uppercase text-slate-500">Service Records</p><p className="mt-2 text-2xl font-bold text-emerald-700">{records.length}</p></div></section>
    {canManage && <form onSubmit={scheduleMaintenance} className="mb-5 grid grid-cols-1 gap-4 rounded-lg bg-white p-5 shadow-sm md:grid-cols-2 xl:grid-cols-3">
      <select required disabled={Boolean(editingId)} value={form.vehicle_id} onChange={(event) => setForm({ ...form, vehicle_id: event.target.value })} className="rounded-md border border-slate-200 px-3 py-2.5 disabled:bg-slate-100"><option value="">Select vehicle</option>{vehicles.map((vehicle) => <option key={vehicle.vehicle_id} value={vehicle.vehicle_id}>{vehicle.registration_number}</option>)}</select>
      <input required value={form.service_type} onChange={(event) => setForm({ ...form, service_type: event.target.value })} placeholder="Service type" className="rounded-md border border-slate-200 px-3 py-2.5" />
      <input value={form.description} onChange={(event) => setForm({ ...form, description: event.target.value })} placeholder="Description" className="rounded-md border border-slate-200 px-3 py-2.5" />
      <label className="text-sm font-medium text-slate-600">Service date<input required type="datetime-local" value={form.service_date} onChange={(event) => setForm({ ...form, service_date: event.target.value })} className="mt-1 block w-full rounded-md border border-slate-200 px-3 py-2.5" /></label>
      <input type="datetime-local" value={form.next_service_date} onChange={(event) => setForm({ ...form, next_service_date: event.target.value })} className="rounded-md border border-slate-200 px-3 py-2.5" />
      <input type="number" min="0" step="0.01" value={form.cost} onChange={(event) => setForm({ ...form, cost: event.target.value })} placeholder="Cost" className="rounded-md border border-slate-200 px-3 py-2.5" />
      <div className="flex gap-2"><button disabled={saving} className="rounded-md bg-violet-600 px-5 py-2.5 font-semibold text-white hover:bg-violet-700 disabled:cursor-not-allowed disabled:opacity-60">{saving ? "Saving..." : editingId ? "Update Maintenance" : "Schedule Maintenance"}</button>{editingId && <button type="button" onClick={() => { setForm(emptyForm); setEditingId(null); }} className="rounded-md bg-slate-200 px-4 py-2.5 font-semibold text-slate-700">Cancel</button>}</div>
    </form>}
    <section className="rounded-lg bg-white p-4 shadow-sm">
      <div className="mb-4 flex flex-col gap-3 sm:flex-row"><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search vehicle or maintenance" className="w-full rounded-md border border-slate-200 px-3 py-2.5 sm:max-w-sm" /><select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)} className="rounded-md border border-slate-200 px-3 py-2.5 sm:w-44"><option value="All">All statuses</option><option value="Scheduled">Scheduled</option><option value="Pending">Pending</option><option value="In Progress">In Progress</option><option value="Completed">Completed</option><option value="Resolved">Resolved</option></select></div>
      <div className="overflow-x-auto"><table className="w-full min-w-[850px] text-sm"><thead className="border-y border-slate-100 bg-slate-50 text-left text-xs uppercase text-slate-500"><tr><th className="px-3 py-3">Vehicle</th><th className="px-3 py-3">Type</th><th className="px-3 py-3">Service Date</th><th className="px-3 py-3">Next Service</th><th className="px-3 py-3">Cost</th><th className="px-3 py-3">Status</th><th className="px-3 py-3">Actions</th></tr></thead><tbody>
        {visibleRecords.map((record) => {
          const isBusy = busyId === record.maintenance_id;
          return <tr key={record.maintenance_id} className="border-b border-slate-100 text-slate-700"><td className="px-3 py-4 font-medium">{vehicleName(record.vehicle_id)}</td><td className="px-3 py-4">{record.service_type}</td><td className="px-3 py-4">{formatDate(record.service_date)}</td><td className="px-3 py-4">{formatDate(dueDateFor(record))}</td><td className="px-3 py-4">{record.cost == null ? "-" : `Rs.${record.cost.toFixed(2)}`}</td><td className="px-3 py-4"><span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${statusClass[record.status] || "bg-slate-100 text-slate-700"}`}>{record.status}</span>{(record.alert_status || alertStatusFor(record)) && <div className={`mt-1 text-xs font-semibold ${alertClass(record.alert_status || alertStatusFor(record))}`}><span aria-hidden="true">●</span> {record.alert_status || alertStatusFor(record)}</div>}</td><td className="px-3 py-4">
            {canManage && <button onClick={() => editRecord(record)} className="mr-2 rounded-md bg-amber-500 px-3 py-1.5 font-semibold text-white hover:bg-amber-600">Edit</button>}
            {canManage && ["Scheduled", "Pending"].includes(record.status) && <button disabled={isBusy} onClick={() => void updateStatus(record, "In Progress")} className="rounded-md bg-violet-600 px-3 py-1.5 font-semibold text-white hover:bg-violet-700 disabled:opacity-60">Start</button>}
            {canManage && record.status === "In Progress" && <button disabled={isBusy} onClick={() => void updateStatus(record, "Completed")} className="rounded-md bg-violet-600 px-3 py-1.5 font-semibold text-white hover:bg-violet-700 disabled:opacity-60">{isBusy ? "Completing..." : "Complete"}</button>}
            {canDelete && isResolved(record.status) && <button onClick={() => void deleteRecord(record)} className="rounded-md bg-rose-600 px-3 py-1.5 font-semibold text-white hover:bg-rose-700">Delete</button>}
            {!canManage && !canDelete && <span className="text-slate-400">-</span>}
          </td></tr>;
        })}
        {!visibleRecords.length && <tr><td colSpan="7" className="px-3 py-10 text-center text-slate-500">No maintenance records found.</td></tr>}
      </tbody></table></div>
    </section>
  </main>;
}
