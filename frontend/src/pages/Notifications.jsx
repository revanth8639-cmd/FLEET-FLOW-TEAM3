import { useEffect, useState } from "react";
import api from "../api/axios";

export default function Notifications() {
  const [notifications, setNotifications] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    api.get("/notifications/")
      .then((response) => {
        if (active) {
          setNotifications(response.data);
          setError("");
        }
      })
      .catch((requestError) => {
        if (active) setError(requestError.response?.data?.detail || "Unable to load notifications.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => { active = false; };
  }, []);

  async function markRead(notificationId) {
    try {
      await api.post(`/notifications/${notificationId}/read`);
      setNotifications((items) => items.map((item) => (
        item.notification_id === notificationId ? { ...item, is_read: true } : item
      )));
    } catch (requestError) {
      setError(requestError.response?.data?.detail || "Unable to mark notification as read.");
    }
  }

  async function markAllRead() {
    try {
      await api.post("/notifications/read-all");
      setNotifications((items) => items.map((item) => ({ ...item, is_read: true })));
    } catch (requestError) {
      setError(requestError.response?.data?.detail || "Unable to mark notifications as read.");
    }
  }

  const unread = notifications.filter((item) => !item.is_read).length;

  return (
    <div className="min-h-screen bg-gray-100 p-8">
      <h1 className="mb-2 text-3xl font-bold">Notifications</h1>
      <p className="mb-6 text-gray-600">System alerts for your account, newest first.</p>
      {error && <div className="mb-4 rounded-lg bg-red-50 p-3 text-red-700">{error}</div>}

      <div className="overflow-hidden rounded-lg bg-white shadow">
        <div className="flex items-center justify-between border-b p-4">
          <span className="text-sm text-gray-600">Unread: {unread}</span>
          <button type="button" disabled={!unread} onClick={() => void markAllRead()} className="text-sm font-semibold text-blue-600 disabled:text-gray-400">Mark all read</button>
        </div>
        <table className="w-full">
          <thead className="bg-gray-200"><tr><th className="p-3 text-left">Alert</th><th className="p-3 text-left">Message</th><th className="p-3 text-left">Created</th><th className="p-3 text-center">Status</th></tr></thead>
          <tbody>
            {!loading && notifications.map((item) => <tr key={item.notification_id} className={`border-t ${item.is_read ? "" : "bg-blue-50"}`}><td className="p-3 font-semibold">{item.title}<div className="text-xs uppercase text-gray-400">{item.type}</div></td><td className="p-3">{item.message}</td><td className="p-3">{new Date(item.created_at).toLocaleString()}</td><td className="p-3 text-center">{item.is_read ? <span className="text-gray-500">Read</span> : <button type="button" onClick={() => void markRead(item.notification_id)} className="rounded bg-blue-600 px-3 py-1 text-white">Mark read</button>}</td></tr>)}
            {!loading && !notifications.length && <tr><td colSpan="4" className="p-6 text-center text-gray-500">No notifications available.</td></tr>}
            {loading && <tr><td colSpan="4" className="p-6 text-center text-gray-500">Loading notifications...</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
