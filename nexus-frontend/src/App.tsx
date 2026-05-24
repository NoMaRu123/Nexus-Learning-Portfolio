import { Navigate, Route, Routes } from "react-router-dom";

import ProtectedRoute from "@/components/ProtectedRoute";
import ChatWidget from "@/components/ChatWidget";
import Login from "@/pages/Login";
import Register from "@/pages/Register";
import Dashboard from "@/pages/Dashboard";
import SkillDetail from "@/pages/SkillDetail";
import ProjectDetail from "@/pages/ProjectDetail";
import Profile from "@/pages/Profile";

/**
 * Root application component.
 *
 * Defines the route structure with public auth pages and protected
 * application pages. In Tracker Mode, protected routes redirect
 * unauthenticated users to /login. In Portfolio Mode, all routes
 * are publicly accessible for read-only viewing.
 */
function App() {
  return (
    <>
      <Routes>
        {/* Public auth routes */}
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />

        {/* Protected application routes */}
        <Route element={<ProtectedRoute />}>
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/skills/:id" element={<SkillDetail />} />
          <Route path="/projects/:id" element={<ProjectDetail />} />
          <Route path="/profile" element={<Profile />} />
        </Route>

        {/* Default redirect */}
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>

      {/* Chat widget available on all pages */}
      <ChatWidget />
    </>
  );
}

export default App;
