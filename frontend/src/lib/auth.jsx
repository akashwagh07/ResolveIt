import React, { createContext, useContext, useState, useEffect } from 'react';

const AuthContext = createContext(null);

const STORAGE_KEY = 'resolveit_demo_session';
const PASSCODE_KEY = 'resolveit_demo_passcode';

export function AuthProvider({ children }) {
  const [session, setSessionState] = useState(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      return saved ? JSON.parse(saved) : null;
    } catch {
      return null;
    }
  });

  const [authNotice, setAuthNotice] = useState('');

  useEffect(() => {
    const handleAuthError = (event) => {
      const message = event?.detail || 'Unauthorized: session expired or invalid credentials.';
      clearSession(message);
    };

    window.addEventListener('resolveit:auth_error', handleAuthError);
    return () => window.removeEventListener('resolveit:auth_error', handleAuthError);
  }, []);

  const setSession = (sessionData, passcode = '') => {
    const newSession = {
      role: sessionData.role,
      userId: sessionData.userId || sessionData.id || null,
      name: (sessionData.name || '').trim(),
      departmentId: sessionData.departmentId || null,
      departmentName: (sessionData.departmentName || '').trim(),
      citizenContact: (sessionData.citizenContact || '').trim(),
    };

    setSessionState(newSession);
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(newSession));
      if (passcode) {
        sessionStorage.setItem(PASSCODE_KEY, passcode);
      } else {
        sessionStorage.removeItem(PASSCODE_KEY);
      }
    } catch {
      // Ignore storage errors
    }
  };

  const clearSession = (notice = '') => {
    setSessionState(null);
    if (notice) setAuthNotice(notice);
    try {
      localStorage.removeItem(STORAGE_KEY);
      sessionStorage.removeItem(PASSCODE_KEY);
    } catch {
      // Ignore storage errors
    }
  };

  const clearAuthNotice = () => {
    setAuthNotice('');
  };

  const isCitizen = session?.role === 'CITIZEN';
  const isOfficer = session?.role === 'OFFICER';
  const isAdmin = session?.role === 'ADMIN';

  return (
    <AuthContext.Provider
      value={{
        session,
        setSession,
        clearSession,
        authNotice,
        setAuthNotice,
        clearAuthNotice,
        isCitizen,
        isOfficer,
        isAdmin,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
