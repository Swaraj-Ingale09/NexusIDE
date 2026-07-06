import { createContext, useState, useEffect, useContext, useCallback, useRef } from 'react';
import api from '../utils/api';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const mountedRef = useRef(true);

  const clearAuth = useCallback(() => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user');
    setUser(null);
    setProfile(null);
    window.dispatchEvent(new Event('authStatusChanged'));
  }, []);

  const fetchUserProfile = useCallback(async () => {
    try {
      const res = await api.get('/api/profile/');
      if (mountedRef.current) {
        setProfile(res.data);
      }
    } catch (err) {
      if (err.response?.status === 401) {
        clearAuth();
      }
    } finally {
      if (mountedRef.current) {
        setLoading(false);
      }
    }
  }, [clearAuth]);

  // Load user from localStorage on init
  useEffect(() => {
    mountedRef.current = true;
    const storedUser = localStorage.getItem('user');
    const token = localStorage.getItem('access_token');
    
    if (storedUser && token) {
      try {
        const parsed = JSON.parse(storedUser);
        setUser(parsed); // eslint-disable-line react-hooks/set-state-in-effect
        fetchUserProfile();
      } catch {
        localStorage.removeItem('user');
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        setLoading(false);
      }
    } else {
      setLoading(false);
    }

    const handleAuthChange = () => {
      const u = localStorage.getItem('user');
      if (!u) {
        setUser(null);
        setProfile(null);
      } else {
        try {
          setUser(JSON.parse(u));
        } catch {
          setUser(null);
          setProfile(null);
        }
      }
    };

    window.addEventListener('authStatusChanged', handleAuthChange);
    return () => {
      mountedRef.current = false;
      window.removeEventListener('authStatusChanged', handleAuthChange);
    };
  }, [fetchUserProfile]);

  // Set up heartbeat tracking
  useEffect(() => {
    if (!user) return;

    const interval = setInterval(async () => {
      try {
        await api.post('/api/heartbeat/', {
          page: window.location.pathname,
          is_active: true
        });
      } catch {
        // heartbeat errors are non-critical
      }
    }, 60000);

    return () => clearInterval(interval);
  }, [user]);

  const login = async (username, password) => {
    try {
      const res = await api.post('/api/auth/login/', { username, password });
      if (res.data.success) {
        localStorage.setItem('access_token', res.data.access);
        localStorage.setItem('refresh_token', res.data.refresh);
        localStorage.setItem('user', JSON.stringify(res.data.user));
        setUser(res.data.user);
        
        const profileRes = await api.get('/api/profile/');
        setProfile(profileRes.data);
        
        window.dispatchEvent(new Event('authStatusChanged'));
        return { success: true };
      }
      return { success: false, error: res.data.error || 'Login failed' };
    } catch (err) {
      return {
        success: false,
        error: err.response?.data?.error || err.response?.data?.detail || 'Invalid credentials'
      };
    }
  };

  const register = async (username, email, password) => {
    try {
      const res = await api.post('/api/auth/register/', { username, email, password });
      if (res.data.success) {
        localStorage.setItem('access_token', res.data.access);
        localStorage.setItem('refresh_token', res.data.refresh);
        localStorage.setItem('user', JSON.stringify(res.data.user));
        setUser(res.data.user);
        
        const profileRes = await api.get('/api/profile/');
        setProfile(profileRes.data);
        
        window.dispatchEvent(new Event('authStatusChanged'));
        return { success: true };
      }
      return { success: false, errors: res.data.errors };
    } catch (err) {
      return {
        success: false,
        error: err.response?.data?.error || 'Registration failed',
        errors: err.response?.data?.errors
      };
    }
  };

  const logout = async () => {
    try {
      await api.post('/api/auth/logout/');
    } catch {
      // logout API errors are non-critical
    } finally {
      clearAuth();
    }
  };

  const refreshProfile = async () => {
    if (user) {
      await fetchUserProfile();
    }
  };

  const value = {
    user,
    profile,
    loading,
    isAuthenticated: !!user,
    login,
    register,
    logout,
    refreshProfile
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

// eslint-disable-next-line react-refresh/only-export-components -- context provider exports hook
export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within an AuthProvider');
  return context;
};
