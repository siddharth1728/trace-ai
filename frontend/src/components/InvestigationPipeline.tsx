import React, { useState } from 'react';
import {
  Activity,
  CheckCircle2,
  XCircle,
  Clock,
  FlaskConical,
  GitBranch,
  Eye,
  Scale,
  Sparkles,
  ChevronDown,
  ChevronRight,
  MessageSquare,
  HelpCircle,
  Play,
  UserCheck,
  Send,
  FastForward,
} from 'lucide-react';
import {
  CodeRevision,
  Countercheck,
  Evidence,
  Hypothesis,
  InvestigationMode,
  Observation,
  PlanStep,
  SessionStatus,
  SocraticPrompt,
  StudentActivitySummary,
  StudentHypothesis,
  StudentTestInput,
} from '../types';
import { InteractionTimeline } from './InteractionTimeline';

interface InvestigationPipelineProps {
  status: SessionStatus;
  activeTool: string | null;
  currentStepIndex: number | null;
  planSteps: PlanStep[];
  observations: Observation[];
  hypotheses: Hypothesis[];
  evidence: Evidence[];
  counterchecks: Countercheck[];
  mode?: InvestigationMode;
  studentHypotheses?: StudentHypothesis[];
  studentTestInputs?: StudentTestInput[];
  revisions?: CodeRevision[];
  activeSocraticPrompt?: SocraticPrompt | null;
  studentActivity?: StudentActivitySummary | null;
  onSubmitStudentHypothesis?: (hypothesis: string, targetLine?: string, confidence?: number) => void;
  onSubmitStudentTestInput?: (testExpr: string, rationale?: string, isBoundary?: boolean) => void;
  onAnswerSocraticPrompt?: (promptId: string, answer: string, skip: boolean) => void;
}

export const InvestigationPipeline: React.FC<InvestigationPipelineProps> = ({
  status,
  activeTool,
  currentStepIndex,
  planSteps,
  observations,
  hypotheses,
  evidence,
  counterchecks,
  mode = 'GUIDED',
  studentHypotheses = [],
  studentTestInputs = [],
  revisions = [],
  activeSocraticPrompt = null,
  studentActivity = null,
  onSubmitStudentHypothesis,
  onSubmitStudentTestInput,
  onAnswerSocraticPrompt,
}) => {
  const [activeTab, setActiveTab] = useState<'timeline' | 'hypotheses' | 'evidence' | 'countercheck' | 'interactive'>(
    mode === 'INTERACTIVE' ? 'interactive' : 'timeline'
  );
  const [expandedObs, setExpandedObs] = useState<Record<string, boolean>>({});

  // Local Form States for Interactive Actions
  const [hypothesisText, setHypothesisText] = useState('');
  const [targetFunction, setTargetFunction] = useState('');
  const [studentConfidence, setStudentConfidence] = useState(0.7);

  const [testExpr, setTestExpr] = useState('');
  const [testRationale, setTestRationale] = useState('');
  const [isBoundary, setIsBoundary] = useState(false);

  const [socraticAnswer, setSocraticAnswer] = useState('');

  const toggleObs = (id: string) => {
    setExpandedObs((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const handleHypothesisSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!hypothesisText.trim() || !onSubmitStudentHypothesis) return;
    onSubmitStudentHypothesis(hypothesisText.trim(), targetFunction.trim() || undefined, studentConfidence);
    setHypothesisText('');
    setTargetFunction('');
  };

  const handleTestSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!testExpr.trim() || !onSubmitStudentTestInput) return;
    onSubmitStudentTestInput(testExpr.trim(), testRationale.trim() || undefined, isBoundary);
    setTestExpr('');
    setTestRationale('');
    setIsBoundary(false);
  };

  const handleSocraticSubmit = (skip: boolean) => {
    if (!activeSocraticPrompt || !onAnswerSocraticPrompt) return;
    onAnswerSocraticPrompt(activeSocraticPrompt.id, socraticAnswer.trim(), skip);
    setSocraticAnswer('');
  };

  const getStatusBadge = () => {
    switch (status) {
      case 'RUNNING':
        return (
          <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-blue-950/80 border border-blue-600/50 text-blue-400 text-xs font-mono animate-pulse">
            <Activity className="w-3.5 h-3.5 animate-spin" />
            <span>RUNNING: {activeTool || 'Synthesizing'}</span>
          </div>
        );
      case 'COMPLETED':
        return (
          <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-950/80 border border-emerald-600/50 text-emerald-400 text-xs font-mono">
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>INVESTIGATION VERIFIED</span>
          </div>
        );
      case 'FAILED':
        return (
          <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-red-950/80 border border-red-600/50 text-red-400 text-xs font-mono">
            <XCircle className="w-3.5 h-3.5" />
            <span>INVESTIGATION FAILED</span>
          </div>
        );
      case 'BLOCKED':
        return (
          <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-yellow-950/80 border border-yellow-600/50 text-yellow-400 text-xs font-mono">
            <Scale className="w-3.5 h-3.5" />
            <span>INVESTIGATION BLOCKED</span>
          </div>
        );
      default:
        return (
          <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-surfaceBorder text-gray-400 text-xs font-mono">
            <Clock className="w-3.5 h-3.5" />
            <span>IDLE / READY</span>
          </div>
        );
    }
  };

  const hasData =
    planSteps.length > 0 ||
    observations.length > 0 ||
    hypotheses.length > 0 ||
    studentHypotheses.length > 0 ||
    studentTestInputs.length > 0;

  if (!hasData && status === 'CREATED') {
    return (
      <div className="bg-surface border border-surfaceBorder rounded-xl p-8 flex flex-col items-center justify-center text-center h-full min-h-[450px] space-y-4">
        <div className="w-14 h-14 rounded-2xl bg-background border border-surfaceBorder flex items-center justify-center text-emerald-400 shadow-inner">
          <GitBranch className="w-7 h-7" />
        </div>
        <div className="space-y-1 max-w-sm">
          <h3 className="font-semibold text-sm text-gray-200">Investigation Pipeline Ready</h3>
          <p className="text-xs text-gray-400 leading-relaxed">
            Provide Python code and click{' '}
            <span className="text-emerald-400 font-medium">
              {mode === 'INTERACTIVE' ? 'Start Interactive Session' : 'Start Investigation'}
            </span>{' '}
            to observe live AST analysis, hypothesis verification, and collaborative debugging.
          </p>
        </div>
        <div className="grid grid-cols-2 gap-2 text-left w-full max-w-xs text-[11px] text-gray-400 pt-2 font-mono">
          <div className="p-2 rounded bg-background border border-surfaceBorder/60 flex items-center gap-1.5">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
            <span>AST Static Audit</span>
          </div>
          <div className="p-2 rounded bg-background border border-surfaceBorder/60 flex items-center gap-1.5">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
            <span>Sandbox Execution</span>
          </div>
          <div className="p-2 rounded bg-background border border-surfaceBorder/60 flex items-center gap-1.5">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
            <span>Student Hypotheses</span>
          </div>
          <div className="p-2 rounded bg-background border border-surfaceBorder/60 flex items-center gap-1.5">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
            <span>Calibrated Proof</span>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-surface border border-surfaceBorder rounded-xl p-5 flex flex-col h-full space-y-4">
      {/* Header & Status */}
      <div className="flex items-center justify-between pb-3 border-b border-surfaceBorder">
        <div className="flex items-center gap-2">
          <GitBranch className="w-4 h-4 text-blue-400" />
          <h2 className="font-semibold text-sm text-white">Investigation Pipeline</h2>
          {mode === 'INTERACTIVE' && (
            <span className="px-2 py-0.5 rounded-full bg-indigo-950 text-indigo-300 border border-indigo-700/60 text-[10px] font-mono font-semibold">
              INTERACTIVE
            </span>
          )}
        </div>
        {getStatusBadge()}
      </div>

      {/* Pipeline Navigation Tabs */}
      <div className="flex items-center gap-1 bg-background p-1 rounded-lg border border-surfaceBorder text-xs overflow-x-auto">
        <button
          onClick={() => setActiveTab('timeline')}
          className={`flex-1 py-1.5 px-2 rounded-md font-medium transition-colors flex items-center justify-center gap-1.5 whitespace-nowrap ${
            activeTab === 'timeline'
              ? 'bg-surface text-white border border-surfaceBorder shadow-sm'
              : 'text-gray-400 hover:text-gray-200'
          }`}
        >
          <Activity className="w-3.5 h-3.5" />
          <span>Timeline ({planSteps.length})</span>
        </button>
        <button
          onClick={() => setActiveTab('hypotheses')}
          className={`flex-1 py-1.5 px-2 rounded-md font-medium transition-colors flex items-center justify-center gap-1.5 whitespace-nowrap ${
            activeTab === 'hypotheses'
              ? 'bg-surface text-white border border-surfaceBorder shadow-sm'
              : 'text-gray-400 hover:text-gray-200'
          }`}
        >
          <Sparkles className="w-3.5 h-3.5 text-yellow-400" />
          <span>Possible Causes ({hypotheses.length + studentHypotheses.length})</span>
        </button>
        <button
          onClick={() => setActiveTab('interactive')}
          className={`flex-1 py-1.5 px-2 rounded-md font-medium transition-colors flex items-center justify-center gap-1.5 whitespace-nowrap ${
            activeTab === 'interactive'
              ? 'bg-indigo-900/60 text-indigo-200 border border-indigo-600/60 shadow-sm'
              : 'text-indigo-400 hover:text-indigo-200'
          }`}
        >
          <UserCheck className="w-3.5 h-3.5" />
          <span>Your Actions ({studentHypotheses.length + studentTestInputs.length})</span>
        </button>
        <button
          onClick={() => setActiveTab('evidence')}
          className={`flex-1 py-1.5 px-2 rounded-md font-medium transition-colors flex items-center justify-center gap-1.5 whitespace-nowrap ${
            activeTab === 'evidence'
              ? 'bg-surface text-white border border-surfaceBorder shadow-sm'
              : 'text-gray-400 hover:text-gray-200'
          }`}
        >
          <Eye className="w-3.5 h-3.5 text-blue-400" />
          <span>Why TRACE Believes This ({evidence.length})</span>
        </button>
        <button
          onClick={() => setActiveTab('countercheck')}
          className={`flex-1 py-1.5 px-2 rounded-md font-medium transition-colors flex items-center justify-center gap-1.5 whitespace-nowrap ${
            activeTab === 'countercheck'
              ? 'bg-surface text-white border border-surfaceBorder shadow-sm'
              : 'text-gray-400 hover:text-gray-200'
          }`}
        >
          <FlaskConical className="w-3.5 h-3.5 text-purple-400" />
          <span>TRACE Tested Its Conclusion ({counterchecks.length})</span>
        </button>
      </div>

      {/* Content Area */}
      <div className="flex-1 overflow-y-auto space-y-4 max-h-[580px] pr-1">
        {/* TAB 1: TIMELINE (Plan & Observations) */}
        {activeTab === 'timeline' && (
          <div className="space-y-4">
            {/* Planned Steps */}
            <div className="space-y-2">
              <span className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider">
                Investigation Plan
              </span>
              <div className="space-y-2">
                {planSteps.map((step) => {
                  const isCurrent = step.step_index === currentStepIndex;
                  return (
                    <div
                      key={step.id}
                      className={`p-3 rounded-lg border text-xs transition-all ${
                        isCurrent
                          ? 'bg-blue-950/40 border-blue-500/60 shadow-sm'
                          : step.status === 'DONE'
                          ? 'bg-background/80 border-surfaceBorder/80 text-gray-200'
                          : step.status === 'FAILED'
                          ? 'bg-red-950/30 border-red-800/40 text-gray-300'
                          : 'bg-background/40 border-surfaceBorder/40 text-gray-400'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-gray-400 font-bold">#{step.step_index}</span>
                          <span className="font-medium text-white">{step.title}</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="px-2 py-0.5 rounded bg-surface border border-surfaceBorder text-[10px] font-mono text-gray-300">
                            {step.tool_name}
                          </span>
                          {step.status === 'DONE' && (
                            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                          )}
                          {step.status === 'IN_PROGRESS' && (
                            <Activity className="w-4 h-4 text-blue-400 animate-spin" />
                          )}
                          {step.status === 'FAILED' && (
                            <XCircle className="w-4 h-4 text-red-400" />
                          )}
                          {step.status === 'PENDING' && (
                            <Clock className="w-4 h-4 text-gray-500" />
                          )}
                        </div>
                      </div>
                      {step.expected_outcome && (
                        <p className="mt-1.5 text-[11px] text-gray-400">
                          <span className="text-gray-500">Expected:</span> {step.expected_outcome}
                        </p>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Observations Feed */}
            {observations.length > 0 && (
              <div className="space-y-2 pt-2 border-t border-surfaceBorder">
                <span className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider">
                  Recorded Observations ({observations.length})
                </span>
                <div className="space-y-2">
                  {observations.map((obs) => {
                    const isExpanded = Boolean(expandedObs[obs.id]);
                    return (
                      <div
                        key={obs.id}
                        className="p-3 bg-background border border-surfaceBorder rounded-lg text-xs space-y-2"
                      >
                        <div
                          className="flex items-center justify-between cursor-pointer select-none"
                          onClick={() => toggleObs(obs.id)}
                        >
                          <div className="flex items-center gap-2">
                            {isExpanded ? (
                              <ChevronDown className="w-3.5 h-3.5 text-gray-400" />
                            ) : (
                              <ChevronRight className="w-3.5 h-3.5 text-gray-400" />
                            )}
                            <span className="font-mono text-emerald-400 text-[11px] font-semibold">
                              {obs.id}
                            </span>
                            <span className="px-1.5 py-0.5 rounded bg-surface border border-surfaceBorder text-[10px] font-mono text-gray-300">
                              {obs.tool_name}
                            </span>
                          </div>
                          <span
                            className={`px-2 py-0.5 rounded text-[10px] font-mono font-medium ${
                              obs.is_success
                                ? 'bg-emerald-950 text-emerald-400 border border-emerald-800/60'
                                : 'bg-red-950 text-red-400 border border-red-800/60'
                            }`}
                          >
                            {obs.is_success ? 'SUCCESS' : 'FAILED'}
                          </span>
                        </div>
                        <p className="text-gray-200 text-xs pl-5">{obs.summary}</p>
                        {isExpanded && obs.output_data && (
                          <div className="mt-2 pl-5">
                            <pre className="p-2 bg-surface/80 rounded border border-surfaceBorder text-[11px] font-mono text-gray-300 overflow-x-auto">
                              {JSON.stringify(obs.output_data, null, 2)}
                            </pre>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        )}

        {/* TAB 2: HYPOTHESES (TRACE & STUDENT DUAL SECTIONS) */}
        {activeTab === 'hypotheses' && (
          <div className="space-y-4">
            {/* Student Articulated Hypotheses */}
            {studentHypotheses.length > 0 && (
              <div className="space-y-2">
                <div className="flex items-center gap-1.5 text-xs font-semibold text-indigo-300">
                  <UserCheck className="w-3.5 h-3.5 text-indigo-400" />
                  <span>Student Hypotheses ({studentHypotheses.length})</span>
                </div>
                {studentHypotheses.map((sh) => (
                  <div
                    key={sh.id}
                    className="p-3 bg-indigo-950/20 border border-indigo-700/50 rounded-lg text-xs space-y-2"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-indigo-400 font-bold">{sh.id}</span>
                        <span className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-indigo-900 text-indigo-200 border border-indigo-700">
                          Turn #{sh.turn_number}
                        </span>
                      </div>
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold ${
                          sh.status === 'SUPPORTED'
                            ? 'bg-emerald-500 text-black'
                            : sh.status === 'CONTRADICTED'
                            ? 'bg-red-500 text-white'
                            : 'bg-surfaceBorder text-gray-300'
                        }`}
                      >
                        {sh.status}
                      </span>
                    </div>
                    <p className="text-gray-100">{sh.hypothesis_text}</p>
                    {sh.target_function_or_line && (
                      <p className="text-[11px] text-gray-400 font-mono">
                        Target: {sh.target_function_or_line}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            )}

            {/* TRACE Agent Hypotheses */}
            <div className="space-y-2">
              <div className="flex items-center gap-1.5 text-xs font-semibold text-yellow-300">
                <Sparkles className="w-3.5 h-3.5 text-yellow-400" />
                <span>TRACE Agent Internal Hypotheses ({hypotheses.length})</span>
              </div>
              {hypotheses.length === 0 ? (
                <p className="text-xs text-gray-500 text-center py-4">No agent hypotheses proposed yet.</p>
              ) : (
                hypotheses.map((hyp) => {
                  const isVerified = hyp.status === 'VERIFIED' || hyp.status === 'CONFIRMED';
                  const isDisproven = hyp.status === 'DISPROVEN' || hyp.status === 'REJECTED';
                  const isSupported = hyp.status === 'SUPPORTED';

                  return (
                    <div
                      key={hyp.id}
                      className={`p-4 rounded-xl border space-y-3 transition-all relative overflow-hidden ${
                        isVerified
                          ? 'bg-emerald-950/40 border-emerald-500/60 shadow-lg shadow-emerald-900/20'
                          : isDisproven
                          ? 'bg-red-950/30 border-red-800/60 opacity-90'
                          : isSupported
                          ? 'bg-blue-950/40 border-blue-500/60 shadow-md'
                          : 'bg-background border-surfaceBorder'
                      }`}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="space-y-1">
                          <div className="flex items-center gap-2">
                            <span className="font-mono text-xs font-bold text-gray-400">{hyp.id}</span>
                            <span
                              className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold tracking-wider ${
                                isVerified
                                  ? 'bg-emerald-500 text-black'
                                  : isDisproven
                                  ? 'bg-red-500 text-white'
                                  : isSupported
                                  ? 'bg-blue-500 text-white'
                                  : 'bg-surfaceBorder text-gray-300'
                              }`}
                            >
                              {hyp.status}
                            </span>
                          </div>
                          <p className="text-xs font-medium text-gray-100">{hyp.statement}</p>
                        </div>
                        <div className="text-right shrink-0">
                          <div className="text-sm font-mono font-bold text-emerald-400">
                            {Math.round(hyp.confidence * 100)}%
                          </div>
                          <span className="text-[10px] text-gray-500">calibrated</span>
                        </div>
                      </div>

                      {/* Confidence Bar */}
                      <div className="w-full h-1.5 rounded-full bg-surfaceBorder overflow-hidden">
                        <div
                          className={`h-full transition-all duration-500 ${
                            isVerified ? 'bg-emerald-400' : isDisproven ? 'bg-red-400' : 'bg-blue-400'
                          }`}
                          style={{ width: `${Math.max(5, hyp.confidence * 100)}%` }}
                        ></div>
                      </div>

                      {hyp.rationale && (
                        <p className="text-[11px] text-gray-400 bg-surface/50 p-2 rounded border border-surfaceBorder/60">
                          <span className="text-gray-500 font-semibold">Rationale:</span> {hyp.rationale}
                        </p>
                      )}
                    </div>
                  );
                })
              )}
            </div>
          </div>
        )}

        {/* TAB 3: INTERACTIVE STUDENT WORKSPACE */}
        {activeTab === 'interactive' && (
          <div className="space-y-4">
            {/* Student Activity Summary Header */}
            {studentActivity && (
              <div className="grid grid-cols-4 gap-2 text-center text-xs font-mono">
                <div className="p-2 bg-background border border-surfaceBorder rounded-lg">
                  <div className="text-indigo-400 font-bold text-sm">{studentActivity.revisions_count}</div>
                  <div className="text-[10px] text-gray-500">Revisions</div>
                </div>
                <div className="p-2 bg-background border border-surfaceBorder rounded-lg">
                  <div className="text-emerald-400 font-bold text-sm">{studentActivity.hypotheses_count}</div>
                  <div className="text-[10px] text-gray-500">Hypotheses</div>
                </div>
                <div className="p-2 bg-background border border-surfaceBorder rounded-lg">
                  <div className="text-purple-400 font-bold text-sm">{studentActivity.custom_tests_count}</div>
                  <div className="text-[10px] text-gray-500">Tests Run</div>
                </div>
                <div className="p-2 bg-background border border-surfaceBorder rounded-lg">
                  <div className="text-blue-400 font-bold text-sm">{studentActivity.total_turns}</div>
                  <div className="text-[10px] text-gray-500">Total Turns</div>
                </div>
              </div>
            )}

            {/* Socratic Inquiry Card (if prompt is pending) */}
            {activeSocraticPrompt && (
              <div className="p-4 rounded-xl bg-indigo-950/40 border-2 border-indigo-500/80 shadow-lg space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <HelpCircle className="w-4 h-4 text-indigo-400" />
                    <span className="font-semibold text-xs text-indigo-200">Reflective Inquiry from TRACE</span>
                  </div>
                  <span className="px-2 py-0.5 rounded bg-indigo-900/80 border border-indigo-600 text-[10px] font-mono text-indigo-300">
                    Focus: {activeSocraticPrompt.focus_area}
                  </span>
                </div>
                <p className="text-xs text-white leading-relaxed font-medium">
                  {activeSocraticPrompt.question_text}
                </p>

                {activeSocraticPrompt.suggested_options.length > 0 && (
                  <div className="flex flex-wrap gap-1.5 pt-1">
                    {activeSocraticPrompt.suggested_options.map((opt, idx) => (
                      <button
                        key={idx}
                        type="button"
                        onClick={() => setSocraticAnswer(opt)}
                        className="px-2 py-1 rounded bg-background hover:bg-surface border border-surfaceBorder text-[11px] text-gray-300 transition-colors"
                      >
                        {opt}
                      </button>
                    ))}
                  </div>
                )}

                <div className="space-y-2 pt-1">
                  <input
                    type="text"
                    value={socraticAnswer}
                    onChange={(e) => setSocraticAnswer(e.target.value)}
                    placeholder="Type your reflection or answer here..."
                    className="w-full px-3 py-1.5 bg-background border border-surfaceBorder rounded text-xs text-white placeholder:text-gray-600 focus:outline-none focus:border-indigo-500"
                  />
                  <div className="flex items-center justify-between gap-2">
                    <button
                      type="button"
                      onClick={() => handleSocraticSubmit(true)}
                      className="px-3 py-1.5 rounded bg-surfaceBorder hover:bg-surface text-gray-300 text-xs flex items-center gap-1 transition-colors"
                    >
                      <FastForward className="w-3.5 h-3.5" />
                      <span>Just Investigate (Bypass)</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => handleSocraticSubmit(false)}
                      disabled={!socraticAnswer.trim()}
                      className="px-4 py-1.5 rounded bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold flex items-center gap-1.5 transition-colors disabled:opacity-50"
                    >
                      <Send className="w-3.5 h-3.5" />
                      <span>Submit Answer</span>
                    </button>
                  </div>
                </div>
              </div>
            )}

            {/* Propose Student Hypothesis Form */}
            <form
              onSubmit={handleHypothesisSubmit}
              className="p-4 bg-background border border-surfaceBorder rounded-xl space-y-3"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <MessageSquare className="w-4 h-4 text-emerald-400" />
                  <h4 className="font-semibold text-xs text-white">Formulate Your Bug Hypothesis</h4>
                </div>
                <span className="text-[10px] text-emerald-400 font-mono">Student Action</span>
              </div>
              <p className="text-[11px] text-gray-400">
                What do you think is causing the bug? Articulating your mental model helps TRACE test your exact theory.
              </p>
              <div className="space-y-2">
                <input
                  type="text"
                  value={hypothesisText}
                  onChange={(e) => setHypothesisText(e.target.value)}
                  placeholder="e.g. The upper() method fails because user.get('name') returns None when the key is missing"
                  className="w-full px-3 py-1.5 bg-surface border border-surfaceBorder rounded-lg text-xs text-white placeholder:text-gray-600 focus:outline-none focus:border-emerald-500"
                />
                <div className="grid grid-cols-2 gap-2">
                  <input
                    type="text"
                    value={targetFunction}
                    onChange={(e) => setTargetFunction(e.target.value)}
                    placeholder="Target function/line (optional, e.g. get_user_profile)"
                    className="px-2.5 py-1.5 bg-surface border border-surfaceBorder rounded text-xs text-gray-200 placeholder:text-gray-600 focus:outline-none"
                  />
                  <div className="flex items-center gap-2 px-2 bg-surface border border-surfaceBorder rounded text-xs text-gray-300">
                    <span className="text-[10px] text-gray-500 font-mono">Confidence:</span>
                    <input
                      type="range"
                      min="0.1"
                      max="1.0"
                      step="0.05"
                      value={studentConfidence}
                      onChange={(e) => setStudentConfidence(parseFloat(e.target.value))}
                      className="w-full accent-emerald-500 h-1 bg-surfaceBorder rounded cursor-pointer"
                    />
                    <span className="font-mono text-emerald-400 font-bold text-[11px] w-8">
                      {Math.round(studentConfidence * 100)}%
                    </span>
                  </div>
                </div>
              </div>
              <button
                type="submit"
                disabled={!hypothesisText.trim()}
                className="w-full py-1.5 px-3 rounded bg-emerald-600 hover:bg-emerald-500 text-white font-medium text-xs flex items-center justify-center gap-1.5 transition-colors disabled:opacity-50"
              >
                <Sparkles className="w-3.5 h-3.5" />
                <span>Submit Hypothesis for Agent Verification</span>
              </button>
            </form>

            {/* Run Custom Test Input Form */}
            <form
              onSubmit={handleTestSubmit}
              className="p-4 bg-background border border-surfaceBorder rounded-xl space-y-3"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <FlaskConical className="w-4 h-4 text-purple-400" />
                  <h4 className="font-semibold text-xs text-white">Sandbox Custom Test Case</h4>
                </div>
                <span className="text-[10px] text-purple-400 font-mono">Real-time Sandbox</span>
              </div>
              <p className="text-[11px] text-gray-400">
                Execute a specific Python expression or edge case directly against the active source code.
              </p>
              <div className="space-y-2">
                <input
                  type="text"
                  value={testExpr}
                  onChange={(e) => setTestExpr(e.target.value)}
                  placeholder="e.g. get_user_profile({1: {}}, 1)"
                  className="w-full px-3 py-1.5 bg-surface border border-surfaceBorder rounded-lg font-mono text-xs text-purple-200 placeholder:text-gray-600 focus:outline-none focus:border-purple-500"
                />
                <div className="flex items-center justify-between gap-3">
                  <input
                    type="text"
                    value={testRationale}
                    onChange={(e) => setTestRationale(e.target.value)}
                    placeholder="Rationale (e.g. Testing empty dictionary entry)"
                    className="flex-1 px-2.5 py-1 bg-surface border border-surfaceBorder rounded text-xs text-gray-200 placeholder:text-gray-600 focus:outline-none"
                  />
                  <label className="flex items-center gap-1.5 text-xs text-gray-300 select-none cursor-pointer">
                    <input
                      type="checkbox"
                      checked={isBoundary}
                      onChange={(e) => setIsBoundary(e.target.checked)}
                      className="rounded accent-purple-500"
                    />
                    <span className="text-[11px]">Boundary Case</span>
                  </label>
                </div>
              </div>
              <button
                type="submit"
                disabled={!testExpr.trim()}
                className="w-full py-1.5 px-3 rounded bg-purple-600 hover:bg-purple-500 text-white font-medium text-xs flex items-center justify-center gap-1.5 transition-colors disabled:opacity-50"
              >
                <Play className="w-3.5 h-3.5 fill-current" />
                <span>Execute Test in Sandbox</span>
              </button>
            </form>

            {/* Collaborative Turn Interaction Timeline */}
            <div className="pt-2 border-t border-surfaceBorder">
              <InteractionTimeline
                studentHypotheses={studentHypotheses}
                studentTestInputs={studentTestInputs}
                revisions={revisions}
                activeSocraticPrompt={activeSocraticPrompt}
              />
            </div>
          </div>
        )}

        {/* TAB 3: EVIDENCE AUDIT CHAIN */}
        {activeTab === 'evidence' && (
          <div className="space-y-3">
            {evidence.length === 0 ? (
              <p className="text-xs text-gray-500 text-center py-6">No evidence items extracted yet.</p>
            ) : (
              evidence.map((item) => (
                <div
                  key={item.id}
                  className="p-3 bg-background border border-surfaceBorder rounded-lg text-xs space-y-2"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-blue-400 text-[11px] font-bold">{item.id}</span>
                      <span
                        className={`px-1.5 py-0.5 rounded text-[10px] font-mono font-semibold ${
                          item.evidence_type === 'DIRECT'
                            ? 'bg-emerald-950 text-emerald-400 border border-emerald-800'
                            : 'bg-blue-950 text-blue-400 border border-blue-800'
                        }`}
                      >
                        {item.evidence_type}
                      </span>
                    </div>
                    <div className="flex items-center gap-1.5 px-2 py-0.5 rounded bg-surface border border-surfaceBorder">
                      <span className="text-[10px] font-mono text-gray-400">
                        {item.relation === 'SUPPORTS' || item.relation === 'VERIFIES' ? 'Supports' : 'Refutes'}
                      </span>
                      <span className="text-[10px] text-gray-500">&rarr;</span>
                      <span
                        className={`text-[10px] font-mono font-bold ${
                          item.relation === 'SUPPORTS' || item.relation === 'VERIFIES'
                            ? 'text-emerald-400'
                            : 'text-red-400'
                        }`}
                      >
                        {item.target_hypothesis_id || 'Global'}
                      </span>
                    </div>
                  </div>
                  <p className="text-gray-200 text-xs">{item.statement}</p>
                  {item.observation_id && (
                    <div className="text-[10px] text-gray-500 font-mono">
                      Grounded in Tool Observation: <span className="text-gray-400">{item.observation_id}</span>
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        )}

        {/* TAB 4: COUNTERCHECK DISPROOF CARD */}
        {activeTab === 'countercheck' && (
          <div className="space-y-4">
            {counterchecks.length === 0 ? (
              <div className="p-6 text-center border border-dashed border-surfaceBorder rounded-xl space-y-2">
                <FlaskConical className="w-8 h-8 text-purple-400 mx-auto" />
                <h4 className="font-semibold text-xs text-gray-300">Automated Countercheck Pending</h4>
                <p className="text-[11px] text-gray-500 max-w-sm mx-auto">
                  TRACE will generate a targeted counterexample experiment to actively attempt to disprove the leading hypothesis.
                </p>
              </div>
            ) : (
              counterchecks.map((check) => (
                <div
                  key={check.id}
                  className={`p-5 rounded-xl border-2 space-y-4 relative overflow-hidden ${
                    check.disproved
                      ? 'bg-red-950/30 border-red-600 shadow-lg shadow-red-900/20'
                      : check.passed
                      ? 'bg-emerald-950/30 border-emerald-600 shadow-lg shadow-emerald-900/20'
                      : 'bg-background border-surfaceBorder'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <FlaskConical className="w-4 h-4 text-purple-400" />
                      <span className="font-mono text-xs font-bold text-white">{check.strategy}</span>
                    </div>
                    <span
                      className={`px-2.5 py-0.5 rounded text-xs font-mono font-bold ${
                        check.disproved
                          ? 'bg-red-500 text-white'
                          : check.passed
                          ? 'bg-emerald-500 text-black'
                          : 'bg-surfaceBorder text-gray-300'
                      }`}
                    >
                      {check.disproved ? 'DISPROVED HYPOTHESIS' : 'HYPOTHESIS VERIFIED'}
                    </span>
                  </div>

                  <p className="text-xs text-gray-200">{check.description}</p>

                  {check.harness_code && (
                    <div className="space-y-1">
                      <span className="text-[10px] text-gray-400 font-mono">Test Harness Input:</span>
                      <pre className="p-2.5 bg-black/60 rounded border border-surfaceBorder/80 font-mono text-[11px] text-emerald-300 overflow-x-auto">
                        {check.harness_code}
                      </pre>
                    </div>
                  )}

                  {check.actual_output && (
                    <div className="p-2 bg-surface/60 rounded border border-surfaceBorder/60 text-[11px] text-gray-300 space-y-1">
                      <span className="text-[10px] text-gray-400 font-mono">Execution Verdict:</span>
                      <p>{check.actual_output}</p>
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        )}
      </div>
    </div>
  );
};
