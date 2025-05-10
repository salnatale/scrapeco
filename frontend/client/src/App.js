import React from 'react';
import { Routes, Route } from 'react-router-dom';
import HomePage from './pages/HomePage';
import UploadPage from './pages/UploadPage';
import LoginPage from './pages/LoginPage'
import LinkedinInstructionsPage from './pages/LinkedinInstructionsPage';
import ResultsPage from './pages/ResultsPage';
import Navbar from './components/Navbar';

const App = () => {
  return (
    <>
      <Navbar />
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/upload" element={<UploadPage />} />
        <Route path="/linkedin-instructions" element={<LinkedinInstructionsPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/results" element={<ResultsPage />} />
      </Routes>
    </>
  );
};

export default App;
