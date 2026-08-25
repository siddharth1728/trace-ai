import React, { useRef, useState } from 'react';
import {
  Code,
  FileCode,
  Play,
  Upload,
  Terminal,
  Sparkles,
  AlertCircle,
  FileText,
  X,
} from 'lucide-react';

interface CodePaneProps {
  sourceCode: string;
  onSourceCodeChange: (code: string) => void;
  userGoal: string;
  onUserGoalChange: (goal: string) => void;
  errorDescription: string;
  onErrorDescriptionChange: (desc: string) => void;
  tracebackInput: string;
  onTracebackInputChange: (tb: string) => void;
  selectedFilename: string | null;
  onFileSelect: (file: File) => void;
  onClearFile: () => void;
  onStartInvestigation: () => void;
  isInvestigating: boolean;
  disabled?: boolean;
}

const SAMPLE_PROGRAMS = [
  {
    name: 'Verified Root Cause',
    goal: 'Debug crash when formatting user name',
    error: "AttributeError: 'NoneType' object has no attribute 'upper'",
    code: `def get_user_profile(user_db, user_id):
    user = user_db.get(user_id)
    return {
        "id": user_id,
        "name": user.get("name").upper(),
        "role": user.get("role", "member")
    }

database = {1: {"name": "Alice", "role": "admin"}, 2: {}}
print(get_user_profile(database, 2))`,
  },
  {
    name: 'Misleading Error',
    goal: 'Fix bug where order history is bleeding between customers',
    error: '',
    code: `def create_customer_record(name, orders=[]):
    orders.append("signup_bonus")
    return {"name": name, "order_history": orders}

customer1 = create_customer_record("Alice")
customer2 = create_customer_record("Bob")

print(f"Customer 1: {customer1}")
print(f"Customer 2: {customer2}")`,
  },
  {
    name: 'Insufficient Evidence',
    goal: 'Debug script failing to process config file',
    error: 'FileNotFoundError: [Errno 2] No such file or directory: \'/etc/app_config.json\'',
    code: `import json

def load_app_config():
    with open('/etc/app_config.json', 'r') as f:
        return json.load(f)

def initialize_system():
    config = load_app_config()
    print(f"Starting system with mode: {config.get('mode', 'default')}")

initialize_system()`,
  },
];

export const CodePane: React.FC<CodePaneProps> = ({
  sourceCode,
  onSourceCodeChange,
  userGoal,
  onUserGoalChange,
  errorDescription,
  onErrorDescriptionChange,
  tracebackInput,
  onTracebackInputChange,
  selectedFilename,
  onFileSelect,
  onClearFile,
  onStartInvestigation,
  isInvestigating,
  disabled = false,
}) => {
  const [showTraceback, setShowTraceback] = useState(Boolean(tracebackInput));
  const [uploadError, setUploadError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setUploadError(null);
    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.name.endsWith('.py')) {
      setUploadError('Invalid file. Only Python (.py) source files are supported.');
      return;
    }
    if (file.size > 256 * 1024) {
      setUploadError('File size exceeds the 256 KB limit.');
      return;
    }

    onFileSelect(file);
  };

  const loadSample = (sample: (typeof SAMPLE_PROGRAMS)[0]) => {
    onSourceCodeChange(sample.code);
    onUserGoalChange(sample.goal);
    onErrorDescriptionChange(sample.error);
    onClearFile();
    setUploadError(null);
  };

  const lineCount = sourceCode.split('\n').length;

  return (
    <div className="bg-surface border border-surfaceBorder rounded-xl p-5 flex flex-col h-full space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-surfaceBorder">
        <div className="flex items-center gap-2">
          <Code className="w-4 h-4 text-emerald-400" />
          <h2 className="font-semibold text-sm text-white">Target Python Code</h2>
        </div>
        {selectedFilename && (
          <div className="flex items-center gap-1.5 px-2 py-0.5 rounded bg-surfaceBorder text-xs text-gray-300 font-mono">
            <FileCode className="w-3.5 h-3.5 text-blue-400" />
            <span className="truncate max-w-[140px]">{selectedFilename}</span>
            <button
              onClick={onClearFile}
              className="text-gray-400 hover:text-red-400 ml-1"
              title="Remove file"
            >
              <X className="w-3 h-3" />
            </button>
          </div>
        )}
      </div>

      {/* Sample Quick Loaders */}
      <div className="flex flex-wrap items-center gap-1.5">
        <span className="text-[11px] text-gray-400 flex items-center gap-1 mr-1">
          <Sparkles className="w-3 h-3 text-yellow-400" />
          Samples:
        </span>
        {SAMPLE_PROGRAMS.map((sample) => (
          <button
            key={sample.name}
            onClick={() => loadSample(sample)}
            disabled={isInvestigating}
            className="text-[11px] px-2 py-0.5 rounded bg-background hover:bg-surfaceBorder text-gray-300 border border-surfaceBorder transition-colors disabled:opacity-50"
          >
            {sample.name}
          </button>
        ))}
      </div>

      {/* Upload Banner / Drag-Drop */}
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileInputChange}
        accept=".py"
        className="hidden"
      />
      <div
        onClick={() => !isInvestigating && fileInputRef.current?.click()}
        className={`border border-dashed border-surfaceBorder rounded-lg p-2.5 text-center cursor-pointer hover:border-emerald-500/50 hover:bg-background/40 transition-colors ${
          isInvestigating ? 'opacity-50 cursor-not-allowed' : ''
        }`}
      >
        <div className="flex items-center justify-center gap-2 text-xs text-gray-400">
          <Upload className="w-3.5 h-3.5 text-emerald-400" />
          <span>Upload a <code className="font-mono text-emerald-400">.py</code> script</span>
          <span className="text-gray-500">(Max 256KB)</span>
        </div>
      </div>

      {uploadError && (
        <div className="flex items-center gap-2 p-2 rounded-lg bg-red-950/60 border border-red-800 text-xs text-red-300">
          <AlertCircle className="w-4 h-4 text-red-400 shrink-0" />
          <span>{uploadError}</span>
        </div>
      )}

      {/* Code Editor Area */}
      <div className="relative flex-1 flex flex-col min-h-[220px] bg-background rounded-lg border border-surfaceBorder font-mono text-xs overflow-hidden focus-within:border-emerald-500/60">
        <div className="flex items-center justify-between px-3 py-1.5 bg-surface/50 border-b border-surfaceBorder/60 text-[11px] text-gray-400 select-none">
          <span className="flex items-center gap-1.5">
            <FileText className="w-3 h-3 text-gray-400" />
            python_script.py
          </span>
          <span>{lineCount} lines</span>
        </div>
        <textarea
          value={sourceCode}
          onChange={(e) => onSourceCodeChange(e.target.value)}
          disabled={isInvestigating || disabled}
          placeholder={`# Paste your Python code here...\ndef buggy_function():\n    pass`}
          className="w-full flex-1 p-3 bg-transparent text-gray-100 font-mono text-xs resize-none focus:outline-none placeholder:text-gray-600 leading-relaxed"
          spellCheck={false}
        />
      </div>

      {/* Problem & Goal Input */}
      <div className="space-y-1.5">
        <label className="text-xs font-semibold text-gray-300 flex items-center justify-between">
          <span>What problem or goal are you debugging?</span>
          <span className="text-[10px] text-emerald-400 font-normal">Required</span>
        </label>
        <input
          type="text"
          value={userGoal}
          onChange={(e) => onUserGoalChange(e.target.value)}
          disabled={isInvestigating}
          placeholder="e.g. Fix crash when formatting username with None key"
          className="w-full px-3 py-2 bg-background border border-surfaceBorder rounded-lg text-xs text-gray-100 placeholder:text-gray-600 focus:outline-none focus:border-emerald-500 transition-colors"
        />
      </div>

      {/* Error Description & Traceback (Optional Accordion) */}
      <div className="space-y-2">
        <div className="space-y-1">
          <label className="text-xs text-gray-400 flex items-center justify-between">
            <span>Observed Error Message <span className="text-gray-500">(optional)</span></span>
          </label>
          <input
            type="text"
            value={errorDescription}
            onChange={(e) => onErrorDescriptionChange(e.target.value)}
            disabled={isInvestigating}
            placeholder="e.g. AttributeError: 'NoneType' object has no attribute 'upper'"
            className="w-full px-3 py-1.5 bg-background border border-surfaceBorder rounded-lg text-xs text-gray-200 placeholder:text-gray-600 focus:outline-none focus:border-surfaceBorder"
          />
        </div>

        <button
          type="button"
          onClick={() => setShowTraceback(!showTraceback)}
          className="text-[11px] text-gray-400 hover:text-emerald-400 flex items-center gap-1.5 font-medium transition-colors"
        >
          <Terminal className="w-3 h-3" />
          {showTraceback ? 'Hide Python Traceback' : '+ Add Python Traceback'}
        </button>

        {showTraceback && (
          <textarea
            value={tracebackInput}
            onChange={(e) => onTracebackInputChange(e.target.value)}
            disabled={isInvestigating}
            placeholder="Paste raw Python stack trace here..."
            rows={3}
            className="w-full p-2.5 bg-background border border-surfaceBorder rounded-lg font-mono text-[11px] text-gray-300 placeholder:text-gray-600 focus:outline-none focus:border-surfaceBorder leading-tight"
          />
        )}
      </div>

      {/* Start Button */}
      <button
        onClick={onStartInvestigation}
        disabled={isInvestigating || !sourceCode.trim() || !userGoal.trim()}
        className={`w-full py-2.5 px-4 rounded-lg font-medium text-xs flex items-center justify-center gap-2 transition-all shadow-md ${
          isInvestigating
            ? 'bg-emerald-800/50 text-emerald-300 cursor-wait border border-emerald-700/50'
            : !sourceCode.trim() || !userGoal.trim()
            ? 'bg-surfaceBorder text-gray-500 cursor-not-allowed'
            : 'bg-emerald-600 hover:bg-emerald-500 text-white hover:shadow-emerald-900/30'
        }`}
      >
        {isInvestigating ? (
          <>
            <div className="w-3.5 h-3.5 border-2 border-emerald-300 border-t-transparent rounded-full animate-spin"></div>
            <span>Investigating Grounded Evidence...</span>
          </>
        ) : (
          <>
            <Play className="w-3.5 h-3.5 fill-current" />
            <span>Start Investigation</span>
          </>
        )}
      </button>
    </div>
  );
};
