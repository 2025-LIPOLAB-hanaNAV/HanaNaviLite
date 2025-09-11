import React, { useEffect, useMemo, useState } from 'react';
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
  const [currentView, setCurrentView] = useState('home');
  const [isDarkMode, setIsDarkMode] = useState(false);
  const [selectedEvidence, setSelectedEvidence] = useState<EvidenceItem | null>(null);
  const [showEvidencePanel, setShowEvidencePanel] = useState(false);

  const toggleTheme = () => {
    setIsDarkMode(!isDarkMode);
    document.documentElement.classList.toggle('dark');
  };

  const handleSearch = (query: string, files?: File[]) => {
    setCurrentView('chat');
    console.log('Search:', query, files);
  };

  const handleQuestionClick = (question: string) => {
    setCurrentView('chat');
    console.log('Question clicked:', question);
  };

  const handlePresetClick = (preset: any) => {
    setCurrentView('chat');
    console.log('Preset clicked:', preset);
  };

  const handleEvidenceClick = (evidence: EvidenceItem) => {
    setSelectedEvidence(evidence);
    setShowEvidencePanel(true);
    console.log('Evidence clicked:', evidence);
  };

  // URL 해시와 뷰 상태 연동 (#/chat 등)
  const validViews = useMemo(() => new Set(['home', 'chat', 'saved', 'documents', 'admin']), []);
  useEffect(() => {
    const readHash = () => {
      const h = window.location.hash.replace(/^#\/?/, '');
      if (h && validViews.has(h)) {
        setCurrentView(h);
      }
    };
    // 초기 로드 시 해시 반영
    readHash();
    // 브라우저 뒤/앞 이동 시 반영
    const onHashChange = () => readHash();
    window.addEventListener('hashchange', onHashChange);
    return () => window.removeEventListener('hashchange', onHashChange);
  }, [validViews]);

  // 뷰가 바뀔 때 URL 해시 업데이트
  useEffect(() => {
    const currentHash = window.location.hash.replace(/^#\/?/, '');
    if (currentHash !== currentView) {
      window.history.replaceState(null, '', `#/${currentView}`);
    }
  }, [currentView]);

  const renderCurrentView = () => {
    switch (currentView) {
      case 'home':
        return (
          <HomePage
            onSearch={handleSearch}
            onQuestionClick={handleQuestionClick}
            onPresetClick={handlePresetClick}
          />
        );
      case 'chat':
        return (
          <ChatPage
            onEvidenceClick={handleEvidenceClick}
          />
        );
      case 'saved':
        return (
          <SavedDestinations
            onDestinationClick={(dest) => console.log('Destination clicked:', dest)}
            onRerunJourney={(dest) => {
              setCurrentView('chat');
              console.log('Rerun journey:', dest);
            }}
          />
        );
      case 'documents':
        return (
          <DocumentViewer />
        );
      case 'admin':
        return (
          <AdminConsole />
        );
      default:
        return null;
    }
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
        onViewChange={setCurrentView}
        isDark={isDarkMode}
        onThemeToggle={toggleTheme}
        showRightPanel={showEvidencePanel}
        rightPanelContent={renderRightPanelContent()}
      >
        {renderCurrentView()}
      </AppShell>
    </div>
  );
}
