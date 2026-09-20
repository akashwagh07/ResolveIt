import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './lib/auth';
import Header from './components/Header';
import LandingPage from './pages/LandingPage';
import CitizenDashboard from './pages/CitizenDashboard';
import ReportIssuePage from './pages/ReportIssuePage';
import ComplaintDetailPage from './pages/ComplaintDetailPage';
import OfficerDashboard from './pages/OfficerDashboard';
import AdminDashboard from './pages/AdminDashboard';
import AdminMapPage from './pages/AdminMapPage';
import DemoControlPanel from './pages/DemoControlPanel';

function RoleGuard({ allowedRoles, children }) {
  const { session } = useAuth();

  if (!session || !session.role) {
    return <Navigate to="/" replace state={{ message: 'Please select a demo persona to access that page.' }} />;
  }

  if (!allowedRoles.includes(session.role)) {
    return (
      <Navigate
        to="/"
        replace
        state={{
          message: `Access denied: page requires ${allowedRoles.join(' or ')} role, but you are currently in session as ${session.role}.`,
        }}
      />
    );
  }

  return children;
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <div className="min-h-screen bg-slate-50 flex flex-col font-sans">
          <Header />
          <main className="flex-1">
            <Routes>
              {/* Public Landing & Persona Picker */}
              <Route path="/" element={<LandingPage />} />

              {/* Citizen Routes */}
              <Route
                path="/citizen"
                element={
                  <RoleGuard allowedRoles={['CITIZEN']}>
                    <CitizenDashboard />
                  </RoleGuard>
                }
              />
              <Route
                path="/citizen/report"
                element={
                  <RoleGuard allowedRoles={['CITIZEN']}>
                    <ReportIssuePage />
                  </RoleGuard>
                }
              />
              <Route
                path="/citizen/complaints/:id"
                element={
                  <RoleGuard allowedRoles={['CITIZEN', 'OFFICER', 'ADMIN']}>
                    <ComplaintDetailPage />
                  </RoleGuard>
                }
              />

              {/* Officer Routes */}
              <Route
                path="/officer"
                element={
                  <RoleGuard allowedRoles={['OFFICER']}>
                    <OfficerDashboard />
                  </RoleGuard>
                }
              />
              <Route
                path="/officer/complaints/:id"
                element={
                  <RoleGuard allowedRoles={['CITIZEN', 'OFFICER', 'ADMIN']}>
                    <ComplaintDetailPage />
                  </RoleGuard>
                }
              />

              {/* Admin Routes */}
              <Route
                path="/admin"
                element={
                  <RoleGuard allowedRoles={['ADMIN']}>
                    <AdminDashboard />
                  </RoleGuard>
                }
              />
              <Route
                path="/admin/map"
                element={
                  <RoleGuard allowedRoles={['ADMIN']}>
                    <AdminMapPage />
                  </RoleGuard>
                }
              />
              <Route
                path="/admin/complaints/:id"
                element={
                  <RoleGuard allowedRoles={['CITIZEN', 'OFFICER', 'ADMIN']}>
                    <ComplaintDetailPage />
                  </RoleGuard>
                }
              />
              <Route
                path="/demo"
                element={
                  <RoleGuard allowedRoles={['ADMIN']}>
                    <DemoControlPanel />
                  </RoleGuard>
                }
              />

              {/* Shared Canonical Complaint Route */}
              <Route
                path="/complaints/:id"
                element={
                  <RoleGuard allowedRoles={['CITIZEN', 'OFFICER', 'ADMIN']}>
                    <ComplaintDetailPage />
                  </RoleGuard>
                }
              />

              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </main>
        </div>
      </BrowserRouter>
    </AuthProvider>
  );
}
