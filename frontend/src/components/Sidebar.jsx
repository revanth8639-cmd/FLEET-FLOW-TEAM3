import { NavLink, useNavigate } from "react-router-dom";
import {
  FaTachometerAlt,
  FaTruck,
  FaUsers,
  FaBoxes,
  FaRoute,
  FaTools,
  FaGasPump,
  FaUserCheck,
  FaChartBar,
  FaSignOutAlt,
  FaUserCog,
} from "react-icons/fa";
import { useAuth } from "../context/AuthContext";

export default function Sidebar() {
  const { logout, user } = useAuth();
  const navigate = useNavigate();
  const menuItems = [
    { name: "Dashboard", path: "/dashboard", icon: <FaTachometerAlt /> },
    { name: "Vehicles", path: "/vehicles", icon: <FaTruck /> },
    { name: "Drivers", path: "/drivers", icon: <FaUsers /> },
    { name: "Shipments", path: "/shipments", icon: <FaBoxes /> },
    { name: "Trips", path: "/trips", icon: <FaRoute /> },
    { name: "Maintenance", path: "/maintenance", icon: <FaTools /> },
    { name: "Fuel Records", path: "/fuel", icon: <FaGasPump /> },
    { name: "Attendance", path: "/attendance", icon: <FaUserCheck /> },
    { name: "Reports", path: "/reports", icon: <FaChartBar /> },
    { name: "My Profile", path: "/profile", icon: <FaUsers /> },
    { name: "Users & Roles", path: "/users", icon: <FaUserCog /> },
    { name: "Leave Requests", path: "/leaves", icon: <FaUserCheck /> },
  ];

  const visibleItems = menuItems.filter((item) => {
    if (!user) return true;
    // Drivers use the same protected shell, with APIs scoping their data to
    // their own vehicle, trips, maintenance, and attendance.
    if (item.path === "/users") return user.role === "Admin";
    return true;
  });

  return (
    <div className="w-64 h-screen bg-slate-900 text-white fixed left-0 top-0 flex flex-col">

      {/* Logo */}
      <div className="p-6 border-b border-slate-700">
        <h1 className="text-3xl font-bold flex items-center gap-3">
          🚚 FleetFlow
        </h1>
        <p className="text-slate-400 text-sm mt-1">
          Fleet Management System
        </p>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto p-4 space-y-2">

        {visibleItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) =>
              `flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 ${
                isActive
                  ? "bg-blue-600 shadow-lg"
                  : "hover:bg-slate-800"
              }`
            }
          >
            <span className="text-lg">{item.icon}</span>
            <span>{item.name}</span>
          </NavLink>
        ))}

      </nav>

      {/* Logout */}
      <div className="border-t border-slate-700 p-4">
        <button onClick={() => { logout(); navigate("/login"); }} className="w-full flex items-center justify-center gap-2 bg-red-600 hover:bg-red-700 py-3 rounded-xl font-semibold transition">
          <FaSignOutAlt />
          Logout
        </button>
      </div>

    </div>
  );
}
