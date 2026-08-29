import React from 'react';
import {
  Sparkles,
  FlaskConical,
  GitCommit,
  HelpCircle,
  Clock,
} from 'lucide-react';
import { CodeRevision, SocraticPrompt, StudentHypothesis, StudentTestInput } from '../types';

export interface TimelineTurn {
  id: string;
  turn_number: number;
  speaker: 'STUDENT' | 'TRACE';
  action_type: 'HYPOTHESIS' | 'TEST_INPUT' | 'REVISION' | 'SOCRATIC_PROMPT' | 'SOCRATIC_ANSWER';
  title: string;
  content: string;
  details?: Record<string, any>;
  timestamp?: string;
  status?: string;
}

interface InteractionTimelineProps {
  studentHypotheses?: StudentHypothesis[];
  studentTestInputs?: StudentTestInput[];
  revisions?: CodeRevision[];
  activeSocraticPrompt?: SocraticPrompt | null;
}

export const InteractionTimeline: React.FC<InteractionTimelineProps> = ({
  studentHypotheses = [],
  studentTestInputs = [],
  revisions = [],
  activeSocraticPrompt,
}) => {
  // Aggregate all events into a unified chronological turn list
  const turns: TimelineTurn[] = [];

  studentHypotheses.forEach((sh) => {
    turns.push({
      id: sh.id,
      turn_number: sh.turn_number || 1,
      speaker: 'STUDENT',
      action_type: 'HYPOTHESIS',
      title: 'Student Hypothesis Articulated',
      content: sh.hypothesis_text,
      status: sh.status,
      details: {
        target: sh.target_function_or_line,
        confidence: sh.student_confidence ? `${Math.round(sh.student_confidence * 100)}%` : undefined,
      },
      timestamp: sh.created_at,
    });
  });

  studentTestInputs.forEach((st) => {
    turns.push({
      id: st.id,
      turn_number: st.turn_number || 1,
      speaker: 'STUDENT',
      action_type: 'TEST_INPUT',
      title: 'Sandbox Test Case Run',
      content: st.input_expression,
      status: st.execution_success ? 'PASSED' : st.exception_type || 'FAILED',
      details: {
        stdout: st.stdout,
        stderr: st.stderr,
        boundary: st.is_boundary_case ? 'Boundary Case' : undefined,
        rationale: st.student_rationale,
      },
      timestamp: st.created_at,
    });
  });

  revisions.forEach((rev) => {
    turns.push({
      id: rev.id,
      turn_number: rev.revision_number,
      speaker: 'STUDENT',
      action_type: 'REVISION',
      title: `Code Revision (v${rev.revision_number})`,
      content: rev.intent_notes || 'Student modified source code',
      status: rev.execution_success ? 'PASSED' : 'RUNTIME_ERROR',
      details: {
        lines_added: `+${rev.lines_added}`,
        lines_deleted: `-${rev.lines_deleted}`,
        complexity_delta: `CC Δ ${rev.cyclomatic_complexity_delta}`,
      },
      timestamp: rev.created_at,
    });
  });

  if (activeSocraticPrompt) {
    turns.push({
      id: activeSocraticPrompt.id,
      turn_number: turns.length + 1,
      speaker: 'TRACE',
      action_type: 'SOCRATIC_PROMPT',
      title: 'Reflective Question from TRACE',
      content: activeSocraticPrompt.question_text,
      status: 'AWAITING_RESPONSE',
      details: {
        focus: activeSocraticPrompt.focus_area,
      },
    });
  }

  // Sort by turn number and timestamp
  turns.sort((a, b) => a.turn_number - b.turn_number);

  if (turns.length === 0) {
    return (
      <div className="p-8 bg-background border border-surfaceBorder rounded-xl text-center space-y-2">
        <Clock className="w-6 h-6 text-gray-500 mx-auto" />
        <h4 className="text-xs font-semibold text-gray-300">No Student Turns Recorded</h4>
        <p className="text-[11px] text-gray-500">
          Formulate a hypothesis, execute a sandbox test, or revise code in Interactive Mode to see the live dialogue timeline.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between pb-1 border-b border-surfaceBorder text-xs text-gray-400">
        <span className="font-semibold uppercase tracking-wider text-[10px]">
          Collaborative Interaction Timeline ({turns.length} turns)
        </span>
      </div>

      <div className="relative pl-6 space-y-4 before:absolute before:left-2.5 before:top-2 before:bottom-2 before:w-0.5 before:bg-surfaceBorder">
        {turns.map((turn) => {
          const isStudent = turn.speaker === 'STUDENT';
          return (
            <div key={turn.id} className="relative group">
              {/* Timeline Dot */}
              <div
                className={`absolute -left-6 top-1.5 w-5 h-5 rounded-full border flex items-center justify-center text-[10px] font-bold ${
                  isStudent
                    ? 'bg-indigo-950 border-indigo-500 text-indigo-300'
                    : 'bg-yellow-950 border-yellow-500 text-yellow-300'
                }`}
              >
                {turn.speaker === 'STUDENT' ? 'S' : 'T'}
              </div>

              {/* Turn Card */}
              <div
                className={`p-3.5 rounded-xl border text-xs space-y-2 transition-all ${
                  isStudent
                    ? 'bg-background/90 border-surfaceBorder hover:border-indigo-500/50'
                    : 'bg-yellow-950/20 border-yellow-800/40 hover:border-yellow-600/50'
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    {turn.action_type === 'HYPOTHESIS' && <Sparkles className="w-3.5 h-3.5 text-emerald-400" />}
                    {turn.action_type === 'TEST_INPUT' && <FlaskConical className="w-3.5 h-3.5 text-purple-400" />}
                    {turn.action_type === 'REVISION' && <GitCommit className="w-3.5 h-3.5 text-blue-400" />}
                    {turn.action_type === 'SOCRATIC_PROMPT' && <HelpCircle className="w-3.5 h-3.5 text-yellow-400" />}
                    <span className="font-semibold text-white text-xs">{turn.title}</span>
                  </div>

                  {turn.status && (
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold ${
                        turn.status === 'PASSED' || turn.status === 'SUPPORTED'
                          ? 'bg-emerald-950 text-emerald-400 border border-emerald-800'
                          : turn.status === 'AWAITING_RESPONSE'
                          ? 'bg-yellow-950 text-yellow-400 border border-yellow-800'
                          : 'bg-surfaceBorder text-gray-300'
                      }`}
                    >
                      {turn.status}
                    </span>
                  )}
                </div>

                <p className="text-gray-200 text-xs leading-relaxed font-mono bg-surface/40 p-2 rounded border border-surfaceBorder/40">
                  {turn.content}
                </p>

                {/* Details list */}
                {turn.details && Object.keys(turn.details).length > 0 && (
                  <div className="flex flex-wrap gap-2 text-[10px] text-gray-400 pt-1">
                    {Object.entries(turn.details).map(([k, v]) =>
                      v ? (
                        <span key={k} className="px-1.5 py-0.5 rounded bg-surface border border-surfaceBorder font-mono">
                          <span className="text-gray-500">{k}:</span> {String(v)}
                        </span>
                      ) : null
                    )}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
