import React, { useState } from 'react';
import { ShieldCheck, Info, X, Activity, History, Brain } from 'lucide-react';

interface HeaderProps {
  currentTab?: 'investigate' | 'history' | 'profile';
  onTabChange?: (tab: 'investigate' | 'history' | 'profile') => void;
}

export const Header: React.FC<HeaderProps> = ({ currentTab, onTabChange }) => {
  const [showInfo, setShowInfo] = useState(false);

  return (
    <>
      <header className="flex flex-col md:flex-row items-center justify-between mb-6 pb-6 border-b border-surfaceBorder gap-4">
        <div className="flex flex-col">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-blue-600 flex items-center justify-center shadow-lg shadow-blue-900/50">
              <ShieldCheck className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-white tracking-tight">TRACE</h1>
              <div className="flex items-center gap-2 mt-0.5">
                <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-blue-950 text-blue-400 border border-blue-800">
                  v0.4
                </span>
                <span className="text-xs text-gray-400 font-medium tracking-wide">
                  DETERMINISTIC DEBUGGING AGENT
                </span>
              </div>
            </div>
          </div>
          <p className="mt-3 text-sm text-gray-400 font-medium">
            Understand your bugs. <span className="text-gray-300">Understand how you debug.</span>
          </p>
        </div>

        <div className="flex items-center gap-4">
          {currentTab && onTabChange && (
            <div className="flex bg-surface border border-surfaceBorder rounded-lg p-1 text-sm font-medium">
              <button
                onClick={() => onTabChange('investigate')}
                className={`flex items-center gap-2 px-4 py-1.5 rounded-md transition-colors ${
                  currentTab === 'investigate'
                    ? 'bg-blue-600 text-white shadow-sm'
                    : 'text-gray-400 hover:text-gray-200 hover:bg-surfaceBorder'
                }`}
              >
                <Activity className="w-4 h-4" />
                Investigate
              </button>
              <button
                onClick={() => onTabChange('history')}
                className={`flex items-center gap-2 px-4 py-1.5 rounded-md transition-colors ${
                  currentTab === 'history'
                    ? 'bg-blue-600 text-white shadow-sm'
                    : 'text-gray-400 hover:text-gray-200 hover:bg-surfaceBorder'
                }`}
              >
                <History className="w-4 h-4" />
                History
              </button>
              <button
                onClick={() => onTabChange('profile')}
                className={`flex items-center gap-2 px-4 py-1.5 rounded-md transition-colors ${
                  currentTab === 'profile'
                    ? 'bg-blue-600 text-white shadow-sm'
                    : 'text-gray-400 hover:text-gray-200 hover:bg-surfaceBorder'
                }`}
              >
                <Brain className="w-4 h-4" />
                Profile
              </button>
            </div>
          )}

          <button
            onClick={() => setShowInfo(true)}
            className="flex items-center gap-2 px-4 py-2 bg-surface hover:bg-surfaceBorder border border-surfaceBorder rounded-lg text-sm font-medium text-gray-300 transition-colors"
          >
            <Info className="w-4 h-4" />
            How TRACE Works
          </button>
        </div>
      </header>

      {/* Info Modal */}
      {showInfo && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
          <div className="bg-surface border border-surfaceBorder rounded-2xl w-full max-w-2xl overflow-hidden shadow-2xl flex flex-col max-h-[90vh]">
            <div className="flex items-center justify-between p-5 border-b border-surfaceBorder">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-blue-600/20 flex items-center justify-center text-blue-400">
                  <Info className="w-5 h-5" />
                </div>
                <h2 className="text-lg font-bold text-white">How TRACE Works</h2>
              </div>
              <button
                onClick={() => setShowInfo(false)}
                className="text-gray-400 hover:text-white transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            
            <div className="p-6 overflow-y-auto space-y-6">
              <p className="text-sm text-gray-300 leading-relaxed">
                Most AI coding assistants guess the answer based on patterns in their training data. 
                They hallucinate, provide plausible but incorrect fixes, and rarely explain <em>why</em> something is broken.
                <br /><br />
                <strong>TRACE is different.</strong> It is a deterministic debugging agent that proves its diagnoses through a rigorous scientific method.
              </p>
              
              <div className="space-y-4">
                <div className="p-4 bg-background border border-surfaceBorder rounded-xl space-y-1.5">
                  <h3 className="font-semibold text-emerald-400 text-sm flex items-center gap-2">
                    <span className="w-5 h-5 rounded-full bg-emerald-950 flex items-center justify-center text-xs">1</span>
                    Static Analysis & Execution
                  </h3>
                  <p className="text-xs text-gray-400 pl-7 leading-relaxed">
                    TRACE reads the AST of your code and executes it in a secure sandbox to reproduce the exact error.
                  </p>
                </div>
                
                <div className="p-4 bg-background border border-surfaceBorder rounded-xl space-y-1.5">
                  <h3 className="font-semibold text-yellow-400 text-sm flex items-center gap-2">
                    <span className="w-5 h-5 rounded-full bg-yellow-950 flex items-center justify-center text-xs">2</span>
                    Hypothesis Generation
                  </h3>
                  <p className="text-xs text-gray-400 pl-7 leading-relaxed">
                    It formulates multiple candidate hypotheses for the root cause and seeks explicit evidence to support or refute each one.
                  </p>
                </div>
                
                <div className="p-4 bg-background border border-surfaceBorder rounded-xl space-y-1.5">
                  <h3 className="font-semibold text-purple-400 text-sm flex items-center gap-2">
                    <span className="w-5 h-5 rounded-full bg-purple-950 flex items-center justify-center text-xs">3</span>
                    Counterexample Disproof
                  </h3>
                  <p className="text-xs text-gray-400 pl-7 leading-relaxed">
                    Before confirming a diagnosis, TRACE actively tries to <em>disprove</em> its leading hypothesis by generating and running counter-tests.
                  </p>
                </div>
              </div>
              
              <div className="p-4 bg-blue-950/20 border border-blue-900/50 rounded-xl">
                <p className="text-xs text-blue-200 leading-relaxed text-center font-medium">
                  The result is a zero-hallucination diagnosis grounded entirely in reproducible evidence.
                </p>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
};
