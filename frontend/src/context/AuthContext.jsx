import { createContext, useContext, useEffect, useState } from "react";
import api from "../api/axios";

const AuthContext = createContext();

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  const refreshUser = async () => {
    const token = sessionStorage.getItem("token");
    if (!token) {
      setUser(null);
      setIsLoading(false);
      return null;
    }

    try {
      const response = await api.get("/auth/me");
      setUser(response.data);
      return response.data;
    } catch {
      sessionStorage.removeItem("token");
      setUser(null);
      return null;
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void refreshUser();
    }, 0);
    return () => window.clearTimeout(timer);
  }, []);

  const login = async (email, password) => {
    setIsLoading(true);
    const formData = new URLSearchParams();

    formData.append("username", email);
    formData.append("password", password);

    try {
      const res = await api.post(
        "/auth/login",
        formData,
        {
          headers: {
            "Content-Type": "application/x-www-form-urlencoded",
          },
        }
      );

      console.log("Login Success:", res.data);

      sessionStorage.setItem("token", res.data.access_token);
      await refreshUser();

      return res.data;
    } catch (err) {
      setIsLoading(false);
      console.error("Login Failed:", err.response?.data);
      throw err;
    }
  };

  const signup = async (data) => {
    const res = await api.post("/auth/signup", data);
    return res.data;
  };

  const logout = () => {
    sessionStorage.removeItem("token");
    setUser(null);
    setIsLoading(false);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        login,
        signup,
        logout,
        refreshUser,
        setUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth() {
  return useContext(AuthContext);
}
