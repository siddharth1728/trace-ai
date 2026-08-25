import React, { useState } from 'react';
import { AlertCircle, RotateCcw } from 'lucide-react';
import { CodePane } from '../components/CodePane';
import { InvestigationPipeline } from '../components/InvestigationPipeline';
import { DiagnosisPane } from '../components/DiagnosisPane';
import { Header } from '../components/Header';
import { useInvestigationStream } from '../hooks/useInvestigationStream';
import { api } from '../api/client';
import { SessionDetail } from '../types';

interface InvestigatePageProps {
  initialSessionId?: string | null;
}

export const InvestigatePage: React.FC<InvestigatePageProps> = ({ initialSessionId }) => {
  const [sourceCode, setSourceCode] = useState<string>(
    `def get_user_profile(user_db, user_id):
    user = user_db.get(user_id)
    return {
        "id": user_id,
        "name": user.get("name").upper(),
        "role": user.get("role", "member")
    }

database = {1: {"name": "Alice", "role": "admin"}, 2: {}}
print(get_user_profile(database, 2))`
  );
  const [userGoal, setUserGoal] = useState<string>(
    'Debug crash when formatting user name with None'
  );
  const [errorDescription, setErrorDescription] = useState<string>(
    "AttributeError: 'NoneType' object has no attribute 'upper'"
  );
  const [tracebackInput, setTracebackInput] = useState<string>('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const [activeSessionId, setActiveSessionId] = useState<string | null>(initialSessionId || null);
  const [initialSessionData, setInitialSessionData] = useState<SessionDetail | null>(null);
  const [isStarting, setIsStarting] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Load existing session if initialSessionId is provided
  React.useEffect(() => {
    if (initialSessionId) {
      api.getSession(initialSessionId)
        .then((data) => {
          setInitialSessionData(data);
          setActiveSessionId(data.id);
          if (data.source_code) setSourceCode(data.source_code);
          if (data.user_goal) setUserGoal(data.user_goal);
          if (data.error_description) setErrorDescription(data.error_description);
          if (data.traceback_input) setTracebackInput(data.traceback_input);
        })
        .catch((err) => {
          setErrorMessage(`Failed to load session '${initialSessionId}': ${err.message}`);
        });
    }
  }, [initialSessionId]);

  // Hook connecting to live SSE stream
  const streamState = useInvestigationStream(activeSessionId, initialSessionData);

  const isInvestigating = isStarting || streamState.status === 'RUNNING';

  const handleStartInvestigation = async () => {
    if (!sourceCode.trim() || !userGoal.trim()) {
      setErrorMessage('Please provide both Python source code and an investigation goal.');
      return;
    }

    setIsStarting(true);
    setErrorMessage(null);

    try {
      let session: SessionDetail;
      if (selectedFile) {
        session = await api.uploadSession(
          selectedFile,
          userGoal,
          errorDescription || undefined,
          tracebackInput || undefined
        );
      } else {
        session = await api.createSession({
          source_code: sourceCode,
          user_goal: userGoal,
          error_description: errorDescription || undefined,
          traceback_input: tracebackInput || undefined,
        });
      }

      setInitialSessionData(session);
      setActiveSessionId(session.id);

      // Launch background investigation
      await api.startInvestigation(session.id, { provider: 'mock', max_iterations: 8 });
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to initiate debugging investigation.');
    } finally {
      setIsStarting(false);
    }
  };

  const handleResetSession = () => {
    setActiveSessionId(null);
    setInitialSessionData(null);
    setErrorMessage(null);
  };

  return (
    <div className="space-y-4">
      <Header />

      {/* Error Alert */}
      {errorMessage && (
        <div className="p-3 bg-red-950/80 border border-red-700/80 rounded-xl flex items-center justify-between text-xs text-red-200">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-red-400 shrink-0" />
            <span>{errorMessage}</span>
          </div>
          <button
            onClick={() => setErrorMessage(null)}
            className="text-red-400 hover:text-white font-mono text-xs"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Reset Session Bar if active */}
      {activeSessionId && (
        <div className="bg-surface border border-surfaceBorder rounded-lg px-4 py-2 flex items-center justify-between text-xs">
          <div className="flex items-center gap-2">
            <span className="text-gray-400">Active Investigation:</span>
            <span className="font-mono text-emerald-400 font-semibold">{activeSessionId}</span>
          </div>
          <button
            onClick={handleResetSession}
            disabled={isInvestigating}
            className="flex items-center gap-1.5 text-gray-400 hover:text-white text-xs transition-colors disabled:opacity-40"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            New Investigation
          </button>
        </div>
      )}

      {/* 3-Pane Responsive Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
        {/* Left: Code Pane (4 cols) */}
        <div className="lg:col-span-4 min-h-[620px]">
          <CodePane
            sourceCode={sourceCode}
            onSourceCodeChange={setSourceCode}
            userGoal={userGoal}
            onUserGoalChange={setUserGoal}
            errorDescription={errorDescription}
            onErrorDescriptionChange={setErrorDescription}
            tracebackInput={tracebackInput}
            onTracebackInputChange={setTracebackInput}
            selectedFilename={selectedFile ? selectedFile.name : null}
            onFileSelect={(file) => {
              setSelectedFile(file);
              const reader = new FileReader();
              reader.onload = (e) => {
                const text = e.target?.result as string;
                if (text) setSourceCode(text);
              };
              reader.readAsText(file);
            }}
            onClearFile={() => setSelectedFile(null)}
            onStartInvestigation={handleStartInvestigation}
            isInvestigating={isInvestigating}
          />
        </div>

        {/* Center: Investigation Pipeline (5 cols) */}
        <div className="lg:col-span-5 min-h-[620px]">
          <InvestigationPipeline
            status={streamState.status}
            activeTool={streamState.activeTool}
            currentStepIndex={streamState.currentStepIndex}
            planSteps={streamState.planSteps}
            observations={streamState.observations}
            hypotheses={streamState.hypotheses}
            evidence={streamState.evidence}
            counterchecks={streamState.counterchecks}
          />
        </div>

        {/* Right: Diagnosis & Learning (3 cols) */}
        <div className="lg:col-span-3 min-h-[620px]">
          <DiagnosisPane
            diagnosis={streamState.diagnosis}
            status={streamState.status}
            confidence={streamState.confidence}
          />
        </div>
      </div>
    </div>
  );
};
