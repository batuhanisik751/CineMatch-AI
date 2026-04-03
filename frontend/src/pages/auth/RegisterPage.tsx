import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../../hooks/useAuth";

export default function RegisterPage() {
  const navigate = useNavigate();
  const { register } = useAuth();
  const [email, setEmail] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    if (password !== confirmPassword) {
      setError("Passwords do not match");
      return;
    }
    if (password.length < 8) {
      setError("Password must be at least 8 characters");
      return;
    }
    if (username.length < 3) {
      setError("Username must be at least 3 characters");
      return;
    }

    setLoading(true);
    try {
      await register(email, username, password);
      navigate("/onboarding", { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed");
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#131314] flex items-center justify-center px-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-10">
          <h1 className="text-4xl font-black tracking-tighter text-[#FFC107] uppercase font-headline">
            CINEMA PRIVATE
          </h1>
          <p className="text-[#d4c5ab] mt-2 text-sm">Create your account</p>
        </div>

        <form
          onSubmit={handleSubmit}
          className="glass-panel rounded-2xl p-8 space-y-6"
        >
          {error && (
            <div className="bg-red-500/10 border border-red-500/30 text-red-400 rounded-lg px-4 py-3 text-sm">
              {error}
            </div>
          )}

          <div>
            <label htmlFor="email" className="block text-sm font-medium text-[#d4c5ab] mb-2">
              Email
            </label>
            <input
              id="email"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full bg-[#1e1e1f] border border-white/10 rounded-lg px-4 py-3 text-on-surface focus:outline-none focus:border-[#FFC107] focus:ring-1 focus:ring-[#FFC107] transition-colors"
              placeholder="you@example.com"
            />
          </div>

          <div>
            <label htmlFor="username" className="block text-sm font-medium text-[#d4c5ab] mb-2">
              Username
            </label>
            <input
              id="username"
              type="text"
              required
              minLength={3}
              maxLength={50}
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full bg-[#1e1e1f] border border-white/10 rounded-lg px-4 py-3 text-on-surface focus:outline-none focus:border-[#FFC107] focus:ring-1 focus:ring-[#FFC107] transition-colors"
              placeholder="Choose a username"
            />
          </div>

          <div>
            <label htmlFor="password" className="block text-sm font-medium text-[#d4c5ab] mb-2">
              Password
            </label>
            <input
              id="password"
              type="password"
              required
              minLength={8}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full bg-[#1e1e1f] border border-white/10 rounded-lg px-4 py-3 text-on-surface focus:outline-none focus:border-[#FFC107] focus:ring-1 focus:ring-[#FFC107] transition-colors"
              placeholder="At least 8 characters"
            />
          </div>

          <div>
            <label htmlFor="confirmPassword" className="block text-sm font-medium text-[#d4c5ab] mb-2">
              Confirm Password
            </label>
            <input
              id="confirmPassword"
              type="password"
              required
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              className="w-full bg-[#1e1e1f] border border-white/10 rounded-lg px-4 py-3 text-on-surface focus:outline-none focus:border-[#FFC107] focus:ring-1 focus:ring-[#FFC107] transition-colors"
              placeholder="Repeat your password"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-[#FFC107] text-[#131314] font-bold py-3 rounded-lg hover:bg-[#ffca2c] transition-colors disabled:opacity-50 disabled:cursor-not-allowed font-headline"
          >
            {loading ? "Creating account..." : "Create Account"}
          </button>

          <p className="text-center text-sm text-[#d4c5ab]">
            Already have an account?{" "}
            <Link to="/login" className="text-[#FFC107] hover:underline font-medium">
              Sign in
            </Link>
          </p>
        </form>
      </div>
    </div>
  );
}
