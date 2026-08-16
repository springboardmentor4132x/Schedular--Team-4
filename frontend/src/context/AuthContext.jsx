import React, { createContext, useContext, useState, useEffect } from 'react';
import api from '../services/api';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  // Checks user credentials session on bootstrap
  const checkAuth = async () => {
    try {
      const response = await api.get('/users/profile');
      setUser(response.data);
      setIsAuthenticated(true);
    } catch (error) {
      setUser(null);
      setIsAuthenticated(false);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    checkAuth();

    // Listen for dead session events from Axios interceptors
    const handleAuthExpired = () => {
      setUser(null);
      setIsAuthenticated(false);
    };

    window.addEventListener('auth-expired', handleAuthExpired);
    return () => {
      window.removeEventListener('auth-expired', handleAuthExpired);
    };
  }, []);

  const login = async (email, password) => {
    setLoading(true);
    try {
      const response = await api.post('/auth/login', { email, password });
      
      // Update Axios Authorization header
      const { access_token } = response.data;
      api.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;

      // Fetch user profile
      const profileResponse = await api.get('/users/profile');
      setUser(profileResponse.data);
      setIsAuthenticated(true);
      return profileResponse.data;
    } catch (error) {
      logoutState();
      throw error;
    } finally {
      setLoading(false);
    }
  };

  const logoutState = () => {
    setUser(null);
    setIsAuthenticated(false);
    delete api.defaults.headers.common['Authorization'];
  };

  const logout = async () => {
    try {
      await api.post('/auth/logout');
    } catch (error) {
      console.error('Logout API failed', error);
    } finally {
      logoutState();
    }
  };

  const register = async (name, email, password, confirmPassword, roleName) => {
    try {
      await api.post('/auth/register', {
        name,
        email,
        password,
        confirm_password: confirmPassword,
        role_name: roleName
      });
    } catch (error) {
      throw error;
    }
  };

  const refreshProfile = async () => {
    try {
      const response = await api.get('/users/profile');
      setUser(response.data);
    } catch (error) {
      console.error('Failed to refresh profile', error);
    }
  };

  const hasPermission = (permission) => {
    if (!user) return false;
    
    // Normalize role name
    const roleName = user.role_name || user.role?.name || '';
    if (roleName === 'Administrator') return true;

    // Check if permission is a string
    const permString = typeof permission === 'string' ? permission : (permission?.name || '');
    if (!permString) return false;

    // Fallback to static mapping if permissions array is not present on user object
    const permissions = user.role?.permissions || [];
    if (permissions.length > 0) {
      return permissions.some(p => p.name === permString);
    }

    // Static role-to-permissions mapping based on role_name
    const ROLE_PERMISSIONS = {
      'Administrator': ['team:create', 'team:invite', 'team:remove', 'post:create', 'post:publish', 'post:delete', 'analytics:view', 'settings:edit'],
      'Business User': ['team:invite', 'post:create', 'post:publish', 'post:delete', 'analytics:view', 'settings:edit'],
      'Team Manager': ['team:invite', 'post:create', 'post:publish', 'post:delete', 'analytics:view', 'settings:edit'],
      'Marketing Team': ['team:invite', 'post:create', 'post:publish', 'post:delete', 'analytics:view', 'settings:edit'],
      'Marketing Specialist': ['team:invite', 'post:create', 'post:publish', 'post:delete', 'analytics:view', 'settings:edit'],
      'Content Creator': ['post:create', 'analytics:view']
    };

    const allowedPermissions = ROLE_PERMISSIONS[roleName] || [];
    return allowedPermissions.includes(permString);
  };

  return (
    <AuthContext.Provider value={{
      user,
      loading,
      isAuthenticated,
      login,
      logout,
      register,
      refreshProfile,
      hasPermission
    }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used inside an AuthProvider');
  }
  return context;
};
