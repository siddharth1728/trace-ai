import React, { useState, useEffect } from 'react';
import { Shield, Lock, Trash2, CheckCircle2, RefreshCw } from 'lucide-react';

export const SettingsPage: React.FC = () => {
  const [telemetryOptIn, setTelemetryOptIn] = useState<boolean>(() => {
    const saved = localStorage.getItem('trace_analytics_opt_in');
    return saved !== null ? saved === 'true' : true;
  });
  const [savedNotification, setSavedNotification] = useState<string | null>(null);

  useEffect(() => {
    localStorage.setItem('trace_analytics_opt_in', telemetryOptIn ? 'true' : 'false');
  }, [telemetryOptIn]);

  const handleToggle = () => {
    const nextVal = !telemetryOptIn;
    setTelemetryOptIn(nextVal);
    setSavedNotification(
      nextVal
        ? 'Debugging telemetry collection is now enabled.'
        : 'Telemetry collection disabled. No session analytics will be recorded.'
    );
    setTimeout(() => setSavedNotification(null), 4000);
  };

  const handleClearLocalStorage = () => {
    if (confirm('Clear local preferences and settings?')) {
      localStorage.clear();
      setTelemetryOptIn(true);
      setSavedNotification('Local storage settings have been reset.');
      setTimeout(() => setSavedNotification(null), 4000);
    }
  };

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      {/* Page Title */}
      <div className="pb-4 border-b border-surfaceBorder">
        <h2 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
          <Shield className="w-5 h-5 text-blue-400" />
          Settings & Privacy Controls
        </h2>
        <p className="text-xs text-gray-400 mt-1">
          Configure how TRACE handles student session data, local telemetry persistence, and privacy preferences.
        </p>
      </div>

      {savedNotification && (
        <div className="p-3 bg-blue-950/80 border border-blue-700 rounded-xl flex items-center gap-2 text-xs text-blue-200">
          <CheckCircle2 className="w-4 h-4 text-blue-400 shrink-0" />
          <span>{savedNotification}</span>
        </div>
      )}

      {/* Main Privacy Card */}
      <div className="bg-surface border border-surfaceBorder rounded-xl p-6 space-y-6">
        <div className="flex items-start justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <Lock className="w-4 h-4 text-emerald-400" />
              <h3 className="font-semibold text-sm text-white">Debugging Telemetry & Analytics</h3>
            </div>
            <p className="text-xs text-gray-400 max-w-xl leading-relaxed">
              When enabled, TRACE computes structural code metrics (AST complexity, LOC) and debugging behavior stats
              (static inspection rate, hypothesis churn, countercheck execution) to build your factual learning profile.
            </p>
          </div>
          {/* Toggle Switch */}
          <button
            onClick={handleToggle}
            type="button"
            className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${
              telemetryOptIn ? 'bg-emerald-600' : 'bg-surfaceBorder'
            }`}
          >
            <span
              className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
                telemetryOptIn ? 'translate-x-5' : 'translate-x-0'
              }`}
            />
          </button>
        </div>

        {/* Privacy Guarantees */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2">
          <div className="p-3.5 bg-background border border-surfaceBorder rounded-lg space-y-1">
            <div className="flex items-center gap-1.5 text-xs font-semibold text-emerald-400">
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span>What TRACE Measures</span>
            </div>
            <p className="text-[11px] text-gray-400 leading-relaxed">
              AST node counts, cyclomatic complexity, tool sequence entropy, verification success rate, and direct evidence ratio.
            </p>
          </div>
          <div className="p-3.5 bg-background border border-surfaceBorder rounded-lg space-y-1">
            <div className="flex items-center gap-1.5 text-xs font-semibold text-blue-400">
              <Shield className="w-3.5 h-3.5" />
              <span>What TRACE Never Collects</span>
            </div>
            <p className="text-[11px] text-gray-400 leading-relaxed">
              Zero PII, no student passwords, no API keys, no network exfiltration, and no external tracking cookies.
            </p>
          </div>
        </div>
      </div>

      {/* Data Management Card */}
      <div className="bg-surface border border-surfaceBorder rounded-xl p-6 space-y-4">
        <div className="flex items-center gap-2 pb-2 border-b border-surfaceBorder">
          <Trash2 className="w-4 h-4 text-red-400" />
          <h3 className="font-semibold text-sm text-white">Local Data Management</h3>
        </div>
        <p className="text-xs text-gray-400 leading-relaxed">
          Manage locally stored user preferences and cache stored in your browser.
        </p>
        <div className="pt-1">
          <button
            onClick={handleClearLocalStorage}
            className="flex items-center gap-2 px-3 py-1.5 bg-red-950/60 hover:bg-red-900 border border-red-800 text-red-300 text-xs rounded-lg transition-colors"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            Reset Local Preferences
          </button>
        </div>
      </div>
    </div>
  );
};
