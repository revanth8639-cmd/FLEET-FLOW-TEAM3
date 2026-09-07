import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { useEffect, useState } from "react";
import { FaBell } from "react-icons/fa";
import api from "../api/axios";

export default function Header() {
  const { user } = useAuth();
  const [notifications, setNotifications] = useState([]);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (!user) return undefined;
    let cancelled = false;
    const load = async () => {
      try { const response = await api.get("/notifications/"); if (!cancelled) setNotifications(response.data); } catch { /* page-level notification view remains available */ }
    };
    void load();
    const interval = window.setInterval(load, 30000);
    return () => { cancelled = true; window.clearInterval(interval); };
  }, [user]);

  const unread = notifications.filter((item) => !item.is_read).length;
  const markAllRead = async () => { await api.post("/notifications/read-all"); setNotifications((items) => items.map((item) => ({ ...item, is_read: true }))); };

  return (
    <div className="h-16 bg-white shadow flex justify-between items-center px-8">
      <h1 className="text-2xl font-bold">
        FleetFlow Dashboard
      </h1>

      <div className="flex items-center gap-5">
        <div className="relative"><button type="button" title="Notifications" onClick={() => setOpen((value) => !value)} className="relative rounded-full p-2 text-slate-600 hover:bg-slate-100"><FaBell />{unread > 0 && <span className="absolute -right-1 -top-1 min-w-5 rounded-full bg-red-600 px-1 text-center text-xs text-white">{unread}</span>}</button>{open && <div className="absolute right-0 z-20 mt-2 w-80 rounded-lg border border-slate-200 bg-white p-3 shadow-xl"><div className="mb-2 flex items-center justify-between"><b>Notifications</b>{unread > 0 && <button type="button" onClick={() => void markAllRead()} className="text-xs text-blue-600">Mark all read</button>}</div><div className="max-h-72 overflow-y-auto">{notifications.slice(0, 8).map((item) => <button type="button" key={item.notification_id} onClick={async () => { if (!item.is_read) { await api.post(`/notifications/${item.notification_id}/read`); setNotifications((items) => items.map((entry) => entry.notification_id === item.notification_id ? { ...entry, is_read: true } : entry)); } }} className={`block w-full border-b px-2 py-2 text-left text-sm ${item.is_read ? "text-slate-500" : "font-semibold text-slate-900"}`}><span className="mr-1 text-xs uppercase text-slate-400">{item.type}</span>{item.title}<p className="font-normal">{item.message}</p></button>)}{!notifications.length && <p className="p-3 text-sm text-slate-500">No notifications.</p>}</div></div>}</div>
        <Link to="/profile" className="text-right hover:text-blue-600">
        <h2 className="font-semibold">
          {user ? `Welcome, ${user.full_name}` : "Loading account…"}
        </h2>

        <p className="text-gray-500">
          {user?.role || ""}
        </p>
        </Link>
      </div>
    </div>
  );
}
