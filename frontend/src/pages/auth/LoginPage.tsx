import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../../hooks/useAuth";

export default function LoginPage() {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(email, password);
      navigate("/", { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
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
          <p className="text-[#d4c5ab] mt-2 text-sm">Sign in to your account</p>
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
            <label htmlFor="password" className="block text-sm font-medium text-[#d4c5ab] mb-2">
              Password
            </label>
            <input
              id="password"
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full bg-[#1e1e1f] border border-white/10 rounded-lg px-4 py-3 text-on-surface focus:outline-none focus:border-[#FFC107] focus:ring-1 focus:ring-[#FFC107] transition-colors"
              placeholder="Enter your password"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-[#FFC107] text-[#131314] font-bold py-3 rounded-lg hover:bg-[#ffca2c] transition-colors disabled:opacity-50 disabled:cursor-not-allowed font-headline"
          >
            {loading ? "Signing in..." : "Sign In"}
          </button>

          <p className="text-center text-sm text-[#d4c5ab]">
            Don't have an account?{" "}
            <Link to="/register" className="text-[#FFC107] hover:underline font-medium">
              Create one
            </Link>
          </p>
        </form>
      </div>
    </div>
  );
}
