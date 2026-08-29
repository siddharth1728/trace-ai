import { useState } from 'react';
import { AppLayout } from './layouts/AppLayout';
import { InvestigatePage } from './pages/InvestigatePage';
import { HistoryPage } from './pages/HistoryPage';
import { ProfilePage } from './pages/ProfilePage';
import { SettingsPage } from './pages/SettingsPage';

export function App() {
  const [currentTab, setCurrentTab] = useState<'investigate' | 'history' | 'profile' | 'settings'>('investigate');
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null);

  const handleOpenSession = (sessionId: string) => {
    setSelectedSessionId(sessionId);
    setCurrentTab('investigate');
  };

  return (
    <AppLayout currentTab={currentTab} onTabChange={setCurrentTab}>
      {currentTab === 'investigate' ? (
        <InvestigatePage key={selectedSessionId || 'new'} initialSessionId={selectedSessionId} />
      ) : currentTab === 'history' ? (
        <HistoryPage onOpenSession={handleOpenSession} />
      ) : currentTab === 'profile' ? (
        <ProfilePage />
      ) : (
        <SettingsPage />
      )}
    </AppLayout>
  );
}

export default App;
