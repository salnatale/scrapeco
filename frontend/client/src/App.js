// frontend/client/src/App.js
import React from 'react';
import { Routes, Route } from 'react-router-dom';
import HomePage from './pages/HomePage';
import UploadPage from './pages/UploadPage';
import LoginPage from './pages/LoginPage';
import ResultsPage from './pages/ResultsPage';
import VCDashboard from './pages/VCDashboard';
import Navbar from './components/Navbar';
import { VCProvider } from './context/VCContext';

const App = () => {
  return (
    <VCProvider>
      <Navbar />
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/upload" element={<UploadPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/results" element={<ResultsPage />} />
        <Route path="/vc-dashboard" element={<VCDashboard />} />
      </Routes>
    </VCProvider>
  );
};

export default App;