import { useEffect, useState } from "react";
import {
  getDrivers,
  createDriver,
  updateDriver,
  deleteDriver,
} from "../api/driverApi";
import { getShipments } from "../api/shipmentApi";
import { getVehicles } from "../api/vehicleApi";
import { useAuth } from "../context/AuthContext";

export default function Drivers() {
  const { user } = useAuth();
  const canManage = ["Admin", "FleetManager"].includes(user?.role);
  const canDelete = canManage;
  const [drivers, setDrivers] = useState([]);
  const [shipments, setShipments] = useState([]);
  const [vehicles, setVehicles] = useState([]);
  const [editingId, setEditingId] = useState(null);
  const [error, setError] = useState("");

  const [formData, setFormData] = useState({
    name: "",
    phone: "",
    license_number: "",
    vehicle_id: "",
    status: "Available",
  });

  useEffect(() => {
    if (!user) return;
    loadDrivers();
    loadShipments();
    loadVehicles();
  }, [user]);

  async function loadDrivers() {
    try {
      const data = await getDrivers();
      setDrivers(data);
    } catch (error) {
      console.error(error);
      setError(error.response?.data?.detail || "Unable to load drivers.");
    }
  }

  async function loadShipments() {
    try {
      setShipments(await getShipments());
    } catch (error) {
      console.error(error);
      setError(error.response?.data?.detail || "Unable to load shipment assignments.");
    }
  }

  async function loadVehicles() {
    try {
      setVehicles(await getVehicles());
    } catch (error) {
      console.error(error);
      setError(error.response?.data?.detail || "Unable to load vehicles.");
    }
  }

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
  };

  const handleAdd = async () => {
    try {
      const payload = { ...formData, vehicle_id: formData.vehicle_id || null };
      if (editingId) {
        await updateDriver(editingId, payload);
      } else {
        await createDriver(payload);
      }

      setFormData({
        name: "",
        phone: "",
        license_number: "",
        vehicle_id: "",
        status: "Available",
      });
      setEditingId(null);

      loadDrivers();
      loadShipments();
      loadVehicles();
    } catch (error) {
      console.error(error);
      setError(error.response?.data?.detail || "Unable to save driver.");
    }
  };

  const assignedShipment = (driverId) =>
    shipments.find((shipment) => shipment.driver_id === driverId);

  const handleDelete = async (id) => {
    if (!window.confirm("Delete this driver?")) return;

    try {
      await deleteDriver(id);
      loadDrivers();
    } catch (error) {
      console.error(error);
      setError(error.response?.data?.detail || "Unable to delete driver.");
    }
  };

  const handleEdit = (driver) => {
    setEditingId(driver.driver_id);
    setFormData({ name: driver.name, phone: driver.phone, license_number: driver.license_number, vehicle_id: driver.vehicle_id || "", status: driver.status || "Available" });
  };

  return (
    <div className="p-8">
      <h1 className="text-3xl font-bold">Driver Management</h1>
      <p className="text-gray-600 mb-5">Total drivers: <b>{drivers.length}</b> | Available: <b>{drivers.filter((driver) => driver.status === "Available").length}</b></p>
      {error && <div className="mb-4 rounded bg-red-50 p-3 text-red-700">{error}</div>}

      {/* Driver accounts can view driver details but cannot change them. */}
      {canManage && <div className="flex gap-3 mb-6 flex-wrap">
        <input
          type="text"
          name="name"
          placeholder="Driver Name"
          value={formData.name}
          onChange={handleChange}
          className="border p-2 rounded"
        />

        <select
          name="vehicle_id"
          value={formData.vehicle_id}
          onChange={handleChange}
          className="border p-2 rounded"
        >
          <option value="">No vehicle assigned</option>
          {vehicles.map((vehicle) => <option key={vehicle.vehicle_id} value={vehicle.vehicle_id}>{vehicle.registration_number}</option>)}
        </select>

        <input
          type="text"
          name="phone"
          placeholder="Phone Number"
          value={formData.phone}
          onChange={handleChange}
          className="border p-2 rounded"
        />

        <input
          type="text"
          name="license_number"
          placeholder="License Number"
          value={formData.license_number}
          onChange={handleChange}
          className="border p-2 rounded"
        />

        <select name="status" value={formData.status} onChange={handleChange} className="border p-2 rounded">
          <option>Available</option>
          <option>Assigned</option>
          <option>On Trip</option>
          <option>Unavailable</option>
        </select>

        <button
          onClick={handleAdd}
          className="bg-blue-600 text-white px-5 py-2 rounded hover:bg-blue-700"
        >
          {editingId ? "Update Driver" : "Add Driver"}
        </button>
        {editingId && <button onClick={() => { setEditingId(null); setFormData({ name: "", phone: "", license_number: "", vehicle_id: "", status: "Available" }); }} className="bg-gray-200 px-5 py-2 rounded">Cancel</button>}
      </div>}

      {/* Drivers Table */}
      <table className="w-full border border-gray-300">
        <thead className="bg-green-600 text-white">
          <tr>
            <th className="p-3">Driver Name</th>
            <th>Phone</th>
            <th>License Number</th>
            <th>Assigned Vehicle</th>
            <th>Shipment Assignment</th>
            {canManage && <th>Action</th>}
          </tr>
        </thead>

        <tbody>
          {drivers.length > 0 ? (
            drivers.map((driver) => (
              <tr key={driver.driver_id} className="border-b text-center">
                {(() => {
                  const shipment = assignedShipment(driver.driver_id);
                  return <>
                <td className="p-3">{driver.name}</td>
                <td>{driver.phone}</td>
                <td>{driver.license_number}</td>
                <td>{vehicles.find((vehicle) => vehicle.vehicle_id === driver.vehicle_id)?.registration_number || "Not assigned"}</td>
                <td>
                  <span className={`px-3 py-1 rounded-full ${shipment ? "bg-blue-100 text-blue-700" : "bg-gray-100 text-gray-600"}`}>
                    {shipment ? `Assigned — ${shipment.tracking_number}` : "Not assigned"}
                  </span>
                </td>
                {canManage && <td>
                  <button
                    onClick={() => handleEdit(driver)}
                    className="bg-yellow-500 text-white px-4 py-1 rounded hover:bg-yellow-600 mr-2"
                  >
                    Edit
                  </button>
                  {canDelete && <button
                    onClick={() => handleDelete(driver.driver_id)}
                    className="bg-red-600 text-white px-4 py-1 rounded hover:bg-red-700"
                  >
                    Delete
                  </button>}
                </td>}
                  </>;
                })()}
              </tr>
            ))
          ) : (
            <tr>
              <td colSpan="6" className="p-4 text-gray-500">
                No drivers found.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
