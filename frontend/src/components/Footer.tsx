import React from 'react';
import { ShieldCheck, GitBranch } from 'lucide-react';

export const Footer: React.FC = () => {
  return (
    <footer className="border-t border-surfaceBorder bg-surface/50 px-6 py-3 text-xs text-gray-500 mt-auto">
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        <div className="flex items-center gap-4">
          <span className="flex items-center gap-1.5 text-gray-400">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
            Sandbox Isolated Execution
          </span>
          <span className="text-gray-600">|</span>
          <span className="flex items-center gap-1.5 text-gray-400">
            <GitBranch className="w-3.5 h-3.5 text-blue-400" />
            Evidence Engine Active
          </span>
        </div>
        <div className="text-gray-500 font-mono">
          TRACE v0.3.0 &bull; Student AI Debugging Assistant
        </div>
      </div>
    </footer>
  );
};
