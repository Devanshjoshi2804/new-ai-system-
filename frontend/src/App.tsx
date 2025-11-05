import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import ChatContainer from './features/chat/components/ChatContainer';
import OnboardingWizard from './features/onboarding/components/OnboardingWizard';
import PartnerDashboard from './features/dashboard/components/PartnerDashboard';
import OCRViewer from './features/ocr/components/OCRViewer';
import './App.css';

function App() {
  // DEV MODE: Use default tenant for testing
  const defaultTenantId = 'dev-tenant-default';
  const defaultPartnerName = 'Demo Logistics';

  return (
    <Router>
      <Routes>
        {/* Landing - redirect to onboarding */}
        <Route path="/" element={<Navigate to="/onboard" replace />} />
        
        {/* Onboarding Wizard */}
        <Route path="/onboard" element={<OnboardingWizard />} />
        
        {/* Chat Interface */}
        <Route 
          path="/chat" 
          element={
            <div className="h-screen w-screen overflow-hidden">
              <ChatContainer 
                tenantId={defaultTenantId} 
                partnerName={defaultPartnerName} 
              />
            </div>
          } 
        />
        
        {/* Dashboard */}
        <Route 
          path="/dashboard" 
          element={
            <PartnerDashboard />
          } 
        />
        
        {/* OCR Viewer */}
        <Route path="/ocr" element={<OCRViewer />} />
        
        {/* Catch all */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Router>
  );
}

export default App;
