import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export const ProtectedRoute = ({ children, requiredPermission, allowedRoles }) => {
  const { user, isAuthenticated, loading, hasPermission } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div style={spinnerContainerStyle}>
        <div style={spinnerStyle}></div>
        <p style={loadingTextStyle}>Securing connection...</p>
      </div>
    );
  }

  if (!isAuthenticated) {
    // Redirect to login page and save previous page location
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (requiredPermission && !hasPermission(requiredPermission)) {
    return <Navigate to="/dashboard" replace />;
  }

  if (allowedRoles && allowedRoles.length > 0) {
    const userRole = (user?.role_name || user?.role?.name || '').toLowerCase();
    const isAllowed = allowedRoles.some(r => {
      const lowerR = r.toLowerCase();
      if (lowerR === 'admin' && (userRole.includes('admin') || userRole === 'administrator')) return true;
      if (lowerR === 'manager' && (userRole.includes('manager') || userRole.includes('marketing'))) return true;
      if (lowerR === 'creator' && (userRole.includes('creator') || userRole.includes('content'))) return true;
      if (lowerR === 'business' && userRole.includes('business')) return true;
      return userRole === lowerR;
    });
    if (!isAllowed) {
      return <Navigate to="/dashboard" replace />;
    }
  }

  return children;
};

// Inline helper styles for loading states
const spinnerContainerStyle = {
  display: 'flex',
  flexDirection: 'column',
  justifyContent: 'center',
  alignItems: 'center',
  height: '100vh',
  width: '100vw',
  backgroundColor: '#09090e',
  color: '#f8fafc',
  gap: '16px'
};

const spinnerStyle = {
  width: '50px',
  height: '50px',
  border: '3px solid rgba(99, 102, 241, 0.1)',
  borderTop: '3px solid #6366f1',
  borderRadius: '50%',
  animation: 'spin 1s linear infinite',
};

// Insert animation globally if not loaded
if (typeof document !== 'undefined') {
  const style = document.createElement('style');
  style.innerHTML = `
    @keyframes spin {
      0% { transform: rotate(0deg); }
      100% { transform: rotate(360deg); }
    }
  `;
  document.head.appendChild(style);
}

const loadingTextStyle = {
  fontFamily: 'Outfit, sans-serif',
  fontSize: '1rem',
  color: '#94a3b8',
  letterSpacing: '0.05em'
};