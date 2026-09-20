import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './lib/auth';
import Header from './components/Header';
import LandingPage from './pages/LandingPage';
import CitizenDashboard from './pages/CitizenDashboard';
import ReportIssuePage from './pages/ReportIssuePage';
import ComplaintDetailPage from './pages/ComplaintDetailPage';
import AdminDashboard from './pages/AdminDashboard';
import AdminMapPage from './pages/AdminMapPage';
import DemoControlPanel from './pages/DemoControlPanel';

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <div className="min-h-screen bg-slate-50 flex flex-col font-sans">
          <Header />
          <main className="flex-1">
            <Routes>
              <Route path="/" element={<LandingPage />} />
              <Route path="/citizen" element={<CitizenDashboard />} />
              <Route path="/citizen/report" element={<ReportIssuePage />} />
              <Route path="/citizen/complaints/:id" element={<ComplaintDetailPage />} />
              <Route path="/admin" element={<AdminDashboard />} />
              <Route path="/admin/map" element={<AdminMapPage />} />
              <Route path="/admin/complaints/:id" element={<ComplaintDetailPage />} />
              <Route path="/demo" element={<DemoControlPanel />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </main>
        </div>
      </BrowserRouter>
    </AuthProvider>
  );
}
