import {
  CheckCircle2,
  Lightbulb,
  ShieldCheck,
  Wrench,
  AlertTriangle,
  FileCheck2,
  FlaskConical,
  Scale,
} from 'lucide-react';
import { FinalDiagnosis, SessionStatus } from '../types';

interface DiagnosisPaneProps {
  diagnosis: FinalDiagnosis | null;
  status: SessionStatus;
  confidence: number;
}

export const DiagnosisPane: React.FC<DiagnosisPaneProps> = ({
  diagnosis,
  status: _status,
  confidence,
}) => {
  if (!diagnosis) {
    return (
      <div className="bg-surface border border-surfaceBorder rounded-xl p-8 flex flex-col items-center justify-center text-center h-full min-h-[450px] space-y-4">
        <div className={`w-14 h-14 rounded-2xl bg-background border border-surfaceBorder flex items-center justify-center text-purple-400 shadow-inner ${
          _status === 'RUNNING' ? 'border-purple-500/50 shadow-purple-900/20' : ''
        }`}>
          {_status === 'RUNNING' ? (
            <div className="w-6 h-6 border-2 border-purple-400 border-t-transparent rounded-full animate-spin"></div>
          ) : (
            <CheckCircle2 className="w-7 h-7" />
          )}
        </div>
        <div className="space-y-1 max-w-sm">
          <h3 className="font-semibold text-sm text-gray-200">
            {_status === 'RUNNING' ? 'Synthesizing Evidence...' : 'Diagnosis Awaiting Evidence'}
          </h3>
          <p className="text-xs text-gray-400 leading-relaxed">
            {_status === 'RUNNING'
              ? 'TRACE is actively collecting evidence and testing hypotheses to formulate a grounded diagnosis.'
              : 'As TRACE executes tools and verifies hypotheses, the grounded root cause, conceptual explanation, and fix guidance will appear here.'}
          </p>
        </div>
        <div className="p-3 bg-background/50 border border-surfaceBorder/60 rounded-lg text-left w-full max-w-xs space-y-1.5 text-[11px] text-gray-400">
          <div className="flex items-center gap-2 text-gray-300 font-medium">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
            <span>Zero-Hallucination Gate</span>
          </div>
          <p className="text-[10px] text-gray-500">
            Diagnoses are locked until supported by deterministic tool observations and disproof testing.
          </p>
        </div>
      </div>
    );
  }

  const confidencePct = Math.round((diagnosis.confidence || confidence || 0) * 100);

  const getVerificationBadge = () => {
    if (confidencePct >= 90) {
      return {
        label: 'VERIFIED ROOT CAUSE',
        bg: 'bg-emerald-950 text-emerald-300 border-emerald-500/60',
        bar: 'bg-emerald-400',
      };
    }
    if (confidencePct >= 70) {
      return {
        label: 'STRONGLY SUPPORTED',
        bg: 'bg-blue-950 text-blue-300 border-blue-500/60',
        bar: 'bg-blue-400',
      };
    }
    if (confidencePct >= 40) {
      return {
        label: 'PLAUSIBLE HYPOTHESIS',
        bg: 'bg-yellow-950 text-yellow-300 border-yellow-500/60',
        bar: 'bg-yellow-400',
      };
    }
    return {
      label: 'UNVERIFIED / BLOCKED',
      bg: 'bg-red-950 text-red-300 border-red-500/60',
      bar: 'bg-red-400',
    };
  };

  const badge = getVerificationBadge();

  return (
    <div className="bg-surface border border-surfaceBorder rounded-xl p-5 flex flex-col h-full space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-surfaceBorder">
        <div className="flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 text-purple-400" />
          <h2 className="font-semibold text-sm text-white">Diagnosis & Learning</h2>
        </div>
        <span
          className={`px-2.5 py-0.5 rounded text-[11px] font-mono font-bold border ${badge.bg}`}
        >
          {badge.label}
        </span>
      </div>

      {/* Content Area */}
      <div className="flex-1 overflow-y-auto space-y-4 max-h-[580px] pr-1">
        {/* 1. Root Cause Card */}
        <div className="p-4 bg-background border border-surfaceBorder rounded-xl space-y-2">
          <span className="text-[10px] font-mono uppercase tracking-wider text-emerald-400 font-bold flex items-center gap-1.5">
            <FileCheck2 className="w-3.5 h-3.5" />
            Likely Root Cause
          </span>
          <p className="text-xs font-semibold text-gray-100 leading-relaxed">
            {diagnosis.likely_root_cause || 'Root cause identified through evidence analysis.'}
          </p>
        </div>

        {/* 2. Confidence Calibration Bar */}
        <div className="p-3 bg-background border border-surfaceBorder rounded-xl space-y-2">
          <div className="flex items-center justify-between text-xs">
            <span className="text-gray-400 flex items-center gap-1.5">
              <Scale className="w-3.5 h-3.5 text-emerald-400" />
              Evidence Confidence
            </span>
            <span className="font-mono font-bold text-emerald-400 text-sm">{confidencePct}%</span>
          </div>
          <div className="w-full h-2 rounded-full bg-surfaceBorder overflow-hidden">
            <div
              className={`h-full transition-all duration-700 ${badge.bar}`}
              style={{ width: `${Math.max(5, confidencePct)}%` }}
            ></div>
          </div>
          <div className="p-2 bg-surface/50 border border-surfaceBorder/60 rounded-md flex items-start gap-2">
            <ShieldCheck className="w-3 h-3 text-emerald-500 shrink-0 mt-0.5" />
            <p className="text-[10px] text-gray-400 font-mono leading-relaxed">
              Confidence is <strong>NOT</strong> an LLM probability. It is a deterministic score calibrated strictly by the quantity of supporting observations and the success of disproof testing.
            </p>
          </div>
        </div>

        {/* 3. Countercheck Proof (if available) */}
        {diagnosis.countercheck_summary && (
          <div className="p-3 bg-purple-950/20 border border-purple-800/40 rounded-xl space-y-1 text-xs">
            <span className="text-[10px] font-mono text-purple-400 font-bold flex items-center gap-1.5 uppercase">
              <FlaskConical className="w-3.5 h-3.5" />
              Countercheck Verification Proof
            </span>
            <p className="text-gray-300 text-[11px] leading-relaxed">
              {diagnosis.countercheck_summary}
            </p>
          </div>
        )}

        {/* 4. Grounded Evidence Summary */}
        {diagnosis.evidence_summary && diagnosis.evidence_summary.length > 0 && (
          <div className="space-y-1.5">
            <span className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider">
              Verified Evidence Chain ({diagnosis.evidence_summary.length})
            </span>
            <div className="space-y-1.5">
              {diagnosis.evidence_summary.map((evText, idx) => (
                <div
                  key={idx}
                  className="p-2.5 bg-background border border-surfaceBorder/80 rounded-lg text-xs flex items-start gap-2 text-gray-300"
                >
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0 mt-0.5" />
                  <span className="text-[11px]">{evText}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* 5. Student Learning Takeaway */}
        {diagnosis.learning_point && (
          <div className="p-3.5 bg-blue-950/20 border border-blue-800/40 rounded-xl space-y-1.5 text-xs">
            <span className="text-[10px] font-mono text-blue-400 font-bold flex items-center gap-1.5 uppercase">
              <Lightbulb className="w-3.5 h-3.5" />
              Student Learning Takeaway
            </span>
            <p className="text-gray-200 text-xs leading-relaxed">{diagnosis.learning_point}</p>
          </div>
        )}

        {/* 6. Conceptual Fix Guidance */}
        {diagnosis.suggested_fix_guidance && (
          <div className="p-3.5 bg-emerald-950/20 border border-emerald-800/40 rounded-xl space-y-1.5 text-xs">
            <span className="text-[10px] font-mono text-emerald-400 font-bold flex items-center gap-1.5 uppercase">
              <Wrench className="w-3.5 h-3.5" />
              Conceptual Fix Guidance
            </span>
            <p className="text-gray-200 text-xs leading-relaxed">
              {diagnosis.suggested_fix_guidance}
            </p>
          </div>
        )}

        {/* 7. Remaining Uncertainty */}
        {diagnosis.what_remains_uncertain && diagnosis.what_remains_uncertain.length > 0 && (
          <div className="p-3 bg-background border border-surfaceBorder rounded-xl space-y-1.5 text-xs">
            <span className="text-[10px] font-mono text-yellow-400 font-semibold flex items-center gap-1.5 uppercase">
              <AlertTriangle className="w-3.5 h-3.5" />
              Remaining Uncertainties
            </span>
            <ul className="list-disc list-inside space-y-1 text-[11px] text-gray-400">
              {diagnosis.what_remains_uncertain.map((item, idx) => (
                <li key={idx}>{item}</li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
};
