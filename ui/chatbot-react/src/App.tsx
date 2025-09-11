import React, { useState } from 'react';
import { Routes, Route, useNavigate, useLocation } from 'react-router-dom';
import { AppShell } from './components/AppShell';
import { HomePage } from './components/HomePage';
import { ChatPage } from './components/ChatPage';
import { SavedDestinations } from './components/SavedDestinations';
import { AdminConsole } from './components/AdminConsole';
import { DocumentViewer } from './components/DocumentViewer';
import { EvidencePanel } from './components/EvidencePanel';

interface EvidenceItem {
  id: string;
  title: string;
  section: string;
  page?: number;
  confidence: number;
  type: 'official' | 'unofficial' | 'restricted';
  preview: string;
}

export default function App() {
  const navigate = useNavigate();
  const location = useLocation();
  const [isDarkMode, setIsDarkMode] = useState(false);
  const [selectedEvidence, setSelectedEvidence] = useState<EvidenceItem | null>(null);
  const [showEvidencePanel, setShowEvidencePanel] = useState(false);

  // Get current view from URL path
  const currentView = location.pathname === '/' ? 'home' : location.pathname.substring(1);

  const toggleTheme = () => {
    setIsDarkMode(!isDarkMode);
    document.documentElement.classList.toggle('dark');
  };

  const handleSearch = (query: string, files?: File[]) => {
    navigate('/chat');
    console.log('Search:', query, files);
  };

  const handleQuestionClick = (question: string) => {
    navigate('/chat');
    console.log('Question clicked:', question);
  };

  const handlePresetClick = (preset: any) => {
    navigate('/chat');
    console.log('Preset clicked:', preset);
  };

  const handleEvidenceClick = (evidence: EvidenceItem) => {
    setSelectedEvidence(evidence);
    setShowEvidencePanel(true);
    console.log('Evidence clicked:', evidence);
  };

  const handleViewChange = (view: string) => {
    navigate(view === 'home' ? '/' : `/${view}`);
  };

  const renderRightPanelContent = () => {
    if (!showEvidencePanel || !selectedEvidence) return null;
    
    return (
      <EvidencePanel
        evidence={selectedEvidence}
        onClose={() => setShowEvidencePanel(false)}
      />
    );
  };

  return (
    <div className="min-h-screen text-foreground" style={{ background: 'var(--background)' }}>
      <AppShell
        currentView={currentView}
        onViewChange={handleViewChange}
        isDark={isDarkMode}
        onThemeToggle={toggleTheme}
        showRightPanel={showEvidencePanel}
        rightPanelContent={renderRightPanelContent()}
      >
        <Routes>
          <Route path="/" element={
            <HomePage
              onSearch={handleSearch}
              onQuestionClick={handleQuestionClick}
              onPresetClick={handlePresetClick}
            />
          } />
          <Route path="/chat" element={
            <ChatPage
              onEvidenceClick={handleEvidenceClick}
            />
          } />
          <Route path="/saved" element={
            <SavedDestinations
              onDestinationClick={(dest) => console.log('Destination clicked:', dest)}
              onRerunJourney={(dest) => {
                navigate('/chat');
                console.log('Rerun journey:', dest);
              }}
            />
          } />
          <Route path="/documents" element={<DocumentViewer />} />
          <Route path="/admin" element={<AdminConsole />} />
        </Routes>
      </AppShell>
    </div>
  );
}