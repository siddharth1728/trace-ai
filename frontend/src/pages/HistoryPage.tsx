import React, { useState, useEffect } from 'react';
import {
  History,
  FolderSearch,
  ExternalLink,
  Trash2,
  RefreshCw,
} from 'lucide-react';
import { api } from '../api/client';
import { SessionSummary } from '../types';

interface HistoryPageProps {
  onOpenSession: (sessionId: string) => void;
}

export const HistoryPage: React.FC<HistoryPageProps> = ({ onOpenSession }) => {
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchSessions = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await api.getSessions();
      setSessions(response.sessions);
    } catch (err: any) {
      setError(err.message || 'Failed to load historical debugging sessions.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchSessions();
  }, []);

  const handleDelete = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm('Are you sure you want to delete this debugging session?')) return;
    try {
      await api.deleteSession(id);
      setSessions((prev) => prev.filter((s) => s.id !== id));
    } catch (err: any) {
      alert(`Delete failed: ${err.message}`);
    }
  };

  return (
    <div className="space-y-5 max-w-5xl mx-auto">
      {/* Header */}
      <div className="bg-surface border border-surfaceBorder rounded-xl p-5 flex items-center justify-between">
        <div>
          <h1 className="text-lg font-bold text-white flex items-center gap-2">
            <History className="w-5 h-5 text-emerald-400" />
            Session History
          </h1>
          <p className="text-xs text-gray-400 mt-1">
            Persisted SQLite investigation sessions, evidence trails, and diagnosed root causes.
          </p>
        </div>
        <button
          onClick={fetchSessions}
          disabled={isLoading}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-background border border-surfaceBorder text-xs text-gray-300 hover:text-white transition-colors"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {error && (
        <div className="p-3 bg-red-950/60 border border-red-800 rounded-lg text-xs text-red-300">
          {error}
        </div>
      )}

      {/* Session List */}
      {isLoading ? (
        <div className="p-12 text-center text-xs text-gray-500 font-mono">
          Loading historical sessions from SQLite...
        </div>
      ) : sessions.length === 0 ? (
        <div className="bg-surface border border-surfaceBorder rounded-xl p-12 text-center space-y-3">
          <div className="w-12 h-12 rounded-full bg-background border border-surfaceBorder flex items-center justify-center mx-auto text-gray-400">
            <FolderSearch className="w-6 h-6" />
          </div>
          <h3 className="font-semibold text-sm text-gray-200">No Past Sessions Yet</h3>
          <p className="text-xs text-gray-500 max-w-md mx-auto">
            Start a new investigation in the Investigate tab to record evidence and diagnoses here.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {sessions.map((sess) => {
            const isCompleted = sess.status === 'COMPLETED';
            const isFailed = sess.status === 'FAILED';
            return (
              <div
                key={sess.id}
                onClick={() => onOpenSession(sess.id)}
                className="p-4 bg-surface hover:bg-surface/80 border border-surfaceBorder rounded-xl transition-all cursor-pointer flex flex-col md:flex-row items-start md:items-center justify-between gap-4 group"
              >
                <div className="space-y-1.5 flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs font-bold text-emerald-400">{sess.id}</span>
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-mono font-semibold ${
                        isCompleted
                          ? 'bg-emerald-950 text-emerald-400 border border-emerald-800'
                          : isFailed
                          ? 'bg-red-950 text-red-400 border border-red-800'
                          : 'bg-blue-950 text-blue-400 border border-blue-800'
                      }`}
                    >
                      {sess.status}
                    </span>
                    <span className="text-[11px] text-gray-500 font-mono">
                      {sess.created_at ? new Date(sess.created_at).toLocaleString() : ''}
                    </span>
                  </div>
                  <h3 className="font-medium text-xs text-white truncate">{sess.title || sess.user_goal}</h3>
                  {sess.likely_root_cause && (
                    <p className="text-[11px] text-gray-400 truncate">
                      <span className="text-emerald-400 font-medium">Diagnosed:</span> {sess.likely_root_cause}
                    </p>
                  )}
                </div>

                <div className="flex items-center gap-4 shrink-0">
                  {sess.confidence > 0 && (
                    <div className="text-right">
                      <div className="text-xs font-mono font-bold text-emerald-400">
                        {Math.round(sess.confidence * 100)}%
                      </div>
                      <span className="text-[9px] text-gray-500 font-mono">confidence</span>
                    </div>
                  )}
                  <button
                    onClick={(e) => handleDelete(sess.id, e)}
                    className="p-1.5 rounded text-gray-500 hover:text-red-400 hover:bg-red-950/40 transition-colors"
                    title="Delete session"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                  <button className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-background group-hover:bg-emerald-600 text-gray-300 group-hover:text-white border border-surfaceBorder text-xs font-medium transition-colors">
                    <span>Inspect</span>
                    <ExternalLink className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
