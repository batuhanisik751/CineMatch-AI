import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import type { ReactNode } from "react";

import { API_BASE_URL } from "../config";

const TOKEN_KEY = "cinematch_auth_token";

interface AuthState {
  token: string | null;
  userId: number;
  username: string;
  email: string;
}

interface AuthContextValue extends AuthState {
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, username: string, password: string) => Promise<void>;
  logout: () => void;
}

function decodeTokenPayload(token: string): { sub: number; username: string; exp: number } | null {
  try {
    const parts = token.split(".");
    if (parts.length !== 3) return null;
    // JWT uses base64url encoding (- and _ instead of + and /, no padding).
    // atob() only handles standard base64, so convert first.
    let b64 = parts[1].replace(/-/g, "+").replace(/_/g, "/");
    b64 += "=".repeat((4 - (b64.length % 4)) % 4);
    const payload = JSON.parse(atob(b64));
    return {
      sub: Number(payload.sub),
      username: payload.username || "",
      exp: payload.exp,
    };
  } catch {
    return null;
  }
}

function loadAuthFromStorage(): AuthState {
  const token = localStorage.getItem(TOKEN_KEY);
  if (!token) return { token: null, userId: 0, username: "", email: "" };

  const payload = decodeTokenPayload(token);
  if (!payload) {
    localStorage.removeItem(TOKEN_KEY);
    return { token: null, userId: 0, username: "", email: "" };
  }

  // Check expiry
  if (payload.exp * 1000 < Date.now()) {
    localStorage.removeItem(TOKEN_KEY);
    return { token: null, userId: 0, username: "", email: "" };
  }

  return { token, userId: payload.sub, username: payload.username, email: "" };
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [auth, setAuth] = useState<AuthState>(loadAuthFromStorage);

  // Check token expiry on interval
  useEffect(() => {
    const interval = setInterval(() => {
      if (auth.token) {
        const payload = decodeTokenPayload(auth.token);
        if (!payload || payload.exp * 1000 < Date.now()) {
          localStorage.removeItem(TOKEN_KEY);
          setAuth({ token: null, userId: 0, username: "", email: "" });
        }
      }
    }, 60_000);
    return () => clearInterval(interval);
  }, [auth.token]);

  const login = useCallback(async (email: string, password: string) => {
    const body = new URLSearchParams();
    body.append("username", email);
    body.append("password", password);

    const res = await fetch(`${API_BASE_URL}/api/v1/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body,
    });

    if (!res.ok) {
      const data = await res.json().catch(() => ({ detail: "Login failed" }));
      throw new Error(data.detail || "Login failed");
    }

    const data = await res.json();
    const token: string = data.access_token;
    localStorage.setItem(TOKEN_KEY, token);
    const payload = decodeTokenPayload(token);
    setAuth({
      token,
      userId: payload?.sub ?? 0,
      username: payload?.username ?? "",
      email,
    });
  }, []);

  const register = useCallback(async (email: string, username: string, password: string) => {
    const res = await fetch(`${API_BASE_URL}/api/v1/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, username, password }),
    });

    if (!res.ok) {
      const data = await res.json().catch(() => ({ detail: "Registration failed" }));
      throw new Error(data.detail || "Registration failed");
    }

    const data = await res.json();
    const token: string = data.access_token;
    localStorage.setItem(TOKEN_KEY, token);
    const payload = decodeTokenPayload(token);
    setAuth({
      token,
      userId: payload?.sub ?? 0,
      username: payload?.username ?? "",
      email,
    });
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    setAuth({ token: null, userId: 0, username: "", email: "" });
  }, []);

  // Listen for 401 errors from apiFetch and auto-logout
  useEffect(() => {
    const handler = () => {
      localStorage.removeItem(TOKEN_KEY);
      setAuth({ token: null, userId: 0, username: "", email: "" });
    };
    window.addEventListener("auth:logout", handler);
    return () => window.removeEventListener("auth:logout", handler);
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      ...auth,
      isAuthenticated: auth.token !== null && auth.userId > 0,
      login,
      register,
      logout,
    }),
    [auth, login, register, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
