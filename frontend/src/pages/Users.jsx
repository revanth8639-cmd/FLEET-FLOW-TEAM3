import { useEffect, useState } from "react";
import api from "../api/axios";
import { useAuth } from "../context/AuthContext";

const roles = ["Admin", "FleetManager", "Dispatcher", "Driver"];

export default function Users() {
  const { user } = useAuth();
  const [users, setUsers] = useState([]);
  const [error, setError] = useState("");
  const [busyId, setBusyId] = useState(null);

  async function load() {
    try { const response = await api.get("/auth/users"); setUsers(response.data); setError(""); }
    catch (requestError) { setError(requestError.response?.data?.detail || "Unable to load users."); }
  }

  useEffect(() => { const timer = window.setTimeout(() => void load(), 0); return () => window.clearTimeout(timer); }, []);

  async function changeRole(account, role) {
    if (role === account.role) return;
    try { setBusyId(account.user_id); await api.patch(`/auth/users/${account.user_id}/role`, { role }); await load(); }
    catch (requestError) { setError(requestError.response?.data?.detail || "Unable to update user role."); }
    finally { setBusyId(null); }
  }

  async function remove(account) {
    if (!window.confirm(`Delete ${account.full_name}?`)) return;
    try { setBusyId(account.user_id); await api.delete(`/auth/users/${account.user_id}`); await load(); }
    catch (requestError) { setError(requestError.response?.data?.detail || "Unable to delete user."); }
    finally { setBusyId(null); }
  }

  if (user?.role !== "Admin") return <main className="p-8"><h1 className="text-3xl font-bold">User Management</h1><p className="mt-3 text-slate-600">Only Admin users can manage roles and accounts.</p></main>;
  return <main className="min-h-screen bg-slate-50 p-5 md:p-8"><div className="mb-6"><h1 className="text-3xl font-bold text-slate-900">User Management</h1><p className="mt-1 text-slate-500">Update account roles or remove accounts.</p></div>{error && <div className="mb-5 rounded-md border border-red-200 bg-red-50 px-4 py-3 text-red-700">{error}</div>}<section className="overflow-x-auto rounded-lg bg-white p-5 shadow-sm"><table className="w-full min-w-[720px] text-sm"><thead className="border-y border-slate-100 bg-slate-50 text-left text-xs uppercase text-slate-500"><tr><th className="px-3 py-3">Name</th><th className="px-3 py-3">Email</th><th className="px-3 py-3">Phone</th><th className="px-3 py-3">Role</th><th className="px-3 py-3">Actions</th></tr></thead><tbody>{users.map((account) => <tr key={account.user_id} className="border-b border-slate-100 text-slate-700"><td className="px-3 py-4 font-medium">{account.full_name}</td><td className="px-3 py-4">{account.email}</td><td className="px-3 py-4">{account.phone || "-"}</td><td className="px-3 py-4"><select value={account.role} disabled={busyId === account.user_id} onChange={(event) => void changeRole(account, event.target.value)} className="rounded-md border border-slate-200 px-2 py-1.5"><option value={account.role}>{account.role}</option>{roles.filter((role) => role !== account.role).map((role) => <option key={role}>{role}</option>)}</select></td><td className="px-3 py-4"><button disabled={busyId === account.user_id || account.user_id === user.user_id} onClick={() => void remove(account)} className="rounded-md bg-rose-600 px-3 py-1.5 font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50">Delete</button></td></tr>)}{!users.length && <tr><td colSpan="5" className="px-3 py-10 text-center text-slate-500">No users found.</td></tr>}</tbody></table></section></main>;
}
