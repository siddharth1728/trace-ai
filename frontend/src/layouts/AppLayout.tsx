import React from 'react';
import { Header } from '../components/Header';
import { Footer } from '../components/Footer';

interface AppLayoutProps {
  currentTab: 'investigate' | 'history' | 'profile';
  onTabChange: (tab: 'investigate' | 'history' | 'profile') => void;
  children: React.ReactNode;
}

export const AppLayout: React.FC<AppLayoutProps> = ({
  currentTab,
  onTabChange,
  children,
}) => {
  return (
    <div className="min-h-screen flex flex-col bg-background text-gray-100 font-sans">
      <Header currentTab={currentTab} onTabChange={onTabChange} />
      <main className="flex-1 max-w-7xl w-full mx-auto p-6">{children}</main>
      <Footer />
    </div>
  );
};
