import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";

export default function ProtectedRoute() {
  const { isAuthenticated } = useAuth();
  // Also check localStorage directly — React state may not have propagated yet
  // after login/register stores the token synchronously
  const hasToken = !!localStorage.getItem("cinematch_auth_token");
  if (!isAuthenticated && !hasToken) return <Navigate to="/login" replace />;
  return <Outlet />;
}
