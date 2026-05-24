import { Navigate, Outlet } from "react-router-dom";

import { useAuth } from "@/context/AuthContext";
import { useMode } from "@/context/ModeContext";

/**
 * Route wrapper that enforces authentication in Tracker Mode.
 *
 * - **Tracker Mode**: redirects unauthenticated users to /login.
 * - **Portfolio Mode**: allows public access (read-only viewing).
 *
 * Wrap protected `<Route>` elements with this component as a layout route.
 *
 * **Validates: Requirements 1.2, 5.4, 14.1**
 */
export default function ProtectedRoute() {
  const { isAuthenticated } = useAuth();
  const { isTrackerMode } = useMode();

  if (isTrackerMode && !isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
}
