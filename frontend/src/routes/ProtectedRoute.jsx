import { Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function ProtectedRoute({ children }) {
  const token = sessionStorage.getItem("token");
  const { user, isLoading } = useAuth();

  if (isLoading) {
    return <div className="grid min-h-screen place-items-center bg-gray-100 text-lg text-gray-600">Loading account...</div>;
  }

  if (!token || !user) {
    return <Navigate to="/login" />;
  }

  return children;
}
