import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import api from "../api/axios";

export default function Signup() {
  const { signup } = useAuth();
  const navigate = useNavigate();

  const [form, setForm] = useState({
    full_name: "",
    email: "",
    password: "",
    phone: "",
    role: "FleetManager",
  });

  const [confirmPassword, setConfirmPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [showOtp, setShowOtp] = useState(false);
  const [otp, setOtp] = useState("");

  const handleChange = (e) => {
    setForm({
      ...form,
      [e.target.name]: e.target.value,
    });
  };

  const sendOTP = async () => {
    if (form.password !== confirmPassword) {
      alert("Passwords do not match");
      return;
    }

    try {
      const response = await api.post("/auth/send-otp", {
        email: form.email,
      });

      const developmentOtp = response.data.development_otp;
      alert(developmentOtp ? `Development OTP: ${developmentOtp}` : "OTP sent to your email.");
      setShowOtp(true);
    } catch (err) {
      alert(
        err.response?.data?.detail ||
          "Failed to send OTP"
      );
    }
  };

  const verifyAndSignup = async () => {
    setLoading(true);

    try {
      await api.post("/auth/verify-otp", {
        email: form.email,
        otp,
      });

      await signup(form);

      alert("Account created successfully!");

      navigate("/login");
    } catch (err) {
      alert(
        err.response?.data?.detail ||
          err.message
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#071329] flex items-center justify-center px-4 py-10">

      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-20 left-10 w-72 h-72 bg-indigo-600/10 rounded-full blur-3xl" />
        <div className="absolute bottom-10 right-10 w-96 h-96 bg-cyan-500/10 rounded-full blur-3xl" />
      </div>

      <div className="relative w-full max-w-md">
        <div className="bg-[#17243a] border border-slate-700/60 rounded-2xl shadow-2xl px-7 py-8">

          <div className="flex justify-center mb-5">
            <div className="w-14 h-14 rounded-xl bg-cyan-500/20 border border-cyan-400/20 flex items-center justify-center">
              <span className="text-3xl">🚚</span>
            </div>
          </div>

          <h1 className="text-2xl font-bold text-white text-center">
            Create Fleet Account
          </h1>

          <p className="text-sm text-slate-400 text-center mt-2 mb-7">
            Register your manager or driver account to get started
          </p>

          {!showOtp ? (
            <form className="space-y-4">
              {/* Full Name */}
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Full Name
                </label>

                <input
                  type="text"
                  name="full_name"
                  placeholder="Enter your full name"
                  value={form.full_name}
                  onChange={handleChange}
                  required
                  className="w-full bg-[#111c30] border border-slate-700 rounded-lg py-3 px-3 text-white"
                />
              </div>

              {/* Email */}
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Email Address
                </label>

                <input
                  type="email"
                  name="email"
                  placeholder="abc@email.com"
                  value={form.email}
                  onChange={handleChange}
                  required
                  className="w-full bg-[#111c30] border border-slate-700 rounded-lg py-3 px-3 text-white"
                />
              </div>

              {/* Password */}
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Password
                </label>

                <input
                  type="password"
                  name="password"
                  placeholder="Create password"
                  value={form.password}
                  onChange={handleChange}
                  required
                  className="w-full bg-[#111c30] border border-slate-700 rounded-lg py-3 px-3 text-white"
                />

                <div className="text-xs mt-2 space-y-1">
                  <p className={/[A-Z]/.test(form.password) ? "text-green-400" : "text-red-400"}>
                    ✓ Uppercase letter
                  </p>

                  <p className={/[a-z]/.test(form.password) ? "text-green-400" : "text-red-400"}>
                    ✓ Lowercase letter
                  </p>

                  <p className={/\d/.test(form.password) ? "text-green-400" : "text-red-400"}>
                    ✓ Number
                  </p>

                  <p className={/[@$!%*?&]/.test(form.password) ? "text-green-400" : "text-red-400"}>
                    ✓ Special character
                  </p>

                  <p className={form.password.length >= 8 ? "text-green-400" : "text-red-400"}>
                    ✓ Minimum 8 characters
                  </p>
                </div>
              </div>

              {/* Confirm Password */}
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Confirm Password
                </label>

                <input
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="Confirm Password"
                  required
                  className="w-full bg-[#111c30] border border-slate-700 rounded-lg py-3 px-3 text-white"
                />

                {confirmPassword && (
                  <p
                    className={
                      confirmPassword === form.password
                        ? "text-green-400 text-sm mt-1"
                        : "text-red-400 text-sm mt-1"
                    }
                  >
                    {confirmPassword === form.password
                      ? "✓ Passwords match"
                      : "✗ Passwords do not match"}
                  </p>
                )}
              </div>

              {/* Phone */}
              <input
                type="text"
                name="phone"
                placeholder="Phone Number"
                value={form.phone}
                onChange={handleChange}
                className="w-full bg-[#111c30] border border-slate-700 rounded-lg py-3 px-3 text-white"
              />

              {/* Role */}
              <select
                name="role"
                value={form.role}
                onChange={handleChange}
                className="w-full bg-[#111c30] border border-slate-700 rounded-lg py-3 px-3 text-white"
              >
                <option value="FleetManager">Fleet Manager</option>
                <option value="Driver">Driver</option>
                <option value="Dispatcher">Dispatcher</option>
                <option value="Admin">Admin</option>
              </select>

              <button
                type="button"
                onClick={sendOTP}
                className="w-full bg-indigo-600 hover:bg-indigo-500 text-white font-semibold py-3 rounded-lg"
              >
                Send OTP
              </button>
            </form>
          ) : (
            <div className="space-y-5">

              <h2 className="text-xl text-center text-white font-semibold">
                Verify OTP
              </h2>

              <p className="text-center text-slate-400 text-sm">
                Enter the 6-digit OTP sent to
                <br />
                <span className="text-cyan-400">{form.email}</span>
              </p>

              <input
                type="text"
                maxLength={6}
                placeholder="Enter OTP"
                value={otp}
                onChange={(e) => setOtp(e.target.value)}
                className="w-full bg-[#111c30] border border-slate-700 rounded-lg py-3 px-3 text-white text-center tracking-[10px] text-xl"
              />

              <button
                onClick={verifyAndSignup}
                disabled={loading}
                className="w-full bg-green-600 hover:bg-green-500 text-white font-semibold py-3 rounded-lg"
              >
                {loading ? "Creating Account..." : "Verify OTP & Create Account"}
              </button>

              <button
                onClick={() => setShowOtp(false)}
                className="w-full border border-slate-600 text-slate-300 py-3 rounded-lg"
              >
                Back
              </button>

            </div>
          )}

          <p className="text-center text-sm text-slate-400 mt-6">
            Already have an account?{" "}
            <button
              type="button"
              onClick={() => navigate("/login")}
              className="text-indigo-400 hover:text-indigo-300"
            >
              Login
            </button>
          </p>

        </div>
      </div>
    </div>
  );
}
