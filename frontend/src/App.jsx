import React from "react";
import {
  BrowserRouter,
  Routes,
  Route,
  Navigate,
} from "react-router-dom";

import { AuthProvider } from "./context/AuthContext";
import { ProtectedRoute } from "./components/ProtectedRoute";
//import ProtectedRoute from "./components/ProtectedRoute";
// ============================================================
// PAGES
// ============================================================

import Login from "./pages/Auth/Login";
import Register from "./pages/Auth/Register";
import ForgotPassword from "./pages/Auth/ForgotPassword";
import ResetPassword from "./pages/Auth/ResetPassword";

import Dashboard from "./pages/Dashboard/Dashboard";

import CreatePost from "./pages/CreatePost/CreatePost";

import SocialAccounts from "./pages/SocialAccounts/SocialAccounts";
import Campaigns from "./pages/Campaigns/Campaigns";
import Scheduler from "./pages/Scheduler/Scheduler";
import Reports from "./pages/Reports/Reports";
import TeamManagement from "./pages/Team/TeamManagement";
import Settings from "./pages/Settings/Settings";
import Profile from "./pages/Profile/Profile";

// Analytics
import Analytics from "./pages/Analytics/Analytics";

// ============================================================
// COMPONENTS
// ============================================================

import Wallpaper from "./components/Wallpaper";


function App() {
  return (
    <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <AuthProvider>

        <Routes>

          {/* ================================================== */}
          {/* PUBLIC AUTH ROUTES */}
          {/* ================================================== */}

          <Route
            path="/login"
            element={<Login />}
          />

          <Route
            path="/register"
            element={<Register />}
          />

          <Route
            path="/forgot-password"
            element={<ForgotPassword />}
          />

          <Route
            path="/reset-password"
            element={<ResetPassword />}
          />


          {/* ================================================== */}
          {/* DASHBOARD */}
          {/* ================================================== */}

          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <Dashboard />
              </ProtectedRoute>
            }
          />


          {/* ================================================== */}
          {/* SCHEDULER & CONTENT */}
          {/* ================================================== */}

          <Route
            path="/scheduler"
            element={
              <ProtectedRoute
                allowedRoles={[
                  "admin",
                  "manager",
                  "creator",
                  "business",
                ]}
              >
                <Dashboard />
              </ProtectedRoute>
            }
          />

          <Route
            path="/create-post"
            element={
              <ProtectedRoute
                allowedRoles={[
                  "admin",
                  "manager",
                  "creator",
                  "business",
                ]}
              >
                <Dashboard />
              </ProtectedRoute>
            }
          />


          {/* ================================================== */}
          {/* CAMPAIGNS */}
          {/* ================================================== */}

          <Route
            path="/campaigns"
            element={
              <ProtectedRoute
                allowedRoles={[
                  "admin",
                  "manager",
                  "business",
                  "creator",
                ]}
              >
                <Dashboard />
              </ProtectedRoute>
            }
          />


          {/* ================================================== */}
          {/* SOCIAL ACCOUNTS */}
          {/* ================================================== */}

          <Route
            path="/social-accounts"
            element={
              <ProtectedRoute
                allowedRoles={[
                  "admin",
                  "manager",
                  "business",
                  "creator",
                ]}
                requiredPermission="post:create"
              >
                <Dashboard />
              </ProtectedRoute>
            }
          />


          {/* ================================================== */}
          {/* ANALYTICS & REPORTS */}
          {/* ================================================== */}

          <Route
            path="/analytics"
            element={
              <ProtectedRoute
                allowedRoles={[
                  "admin",
                  "manager",
                  "creator",
                  "business",
                ]}
                requiredPermission="analytics:view"
              >
                <Dashboard />
              </ProtectedRoute>
            }
          />

          <Route
            path="/reports"
            element={
              <ProtectedRoute
                allowedRoles={[
                  "admin",
                  "manager",
                  "business",
                ]}
              >
                <Dashboard />
              </ProtectedRoute>
            }
          />


          {/* ================================================== */}
          {/* TEAM & USER MANAGEMENT */}
          {/* ================================================== */}

          <Route
            path="/team"
            element={
              <ProtectedRoute
                allowedRoles={[
                  "admin",
                  "manager",
                  "business",
                ]}
              >
                <Dashboard />
              </ProtectedRoute>
            }
          />

          <Route
            path="/profile"
            element={
              <ProtectedRoute>
                <Dashboard />
              </ProtectedRoute>
            }
          />

          <Route
            path="/settings"
            element={
              <ProtectedRoute>
                <Dashboard />
              </ProtectedRoute>
            }
          />


          {/* ================================================== */}
          {/* DEFAULT REDIRECT */}
          {/* ================================================== */}

          <Route
            path="/"
            element={
              <Navigate
                to="/dashboard"
                replace
              />
            }
          />


          {/* ================================================== */}
          {/* UNKNOWN ROUTE */}
          {/* ================================================== */}

          <Route
            path="*"
            element={
              <Navigate
                to="/dashboard"
                replace
              />
            }
          />

        </Routes>

      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;