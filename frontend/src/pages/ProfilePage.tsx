import React, { useEffect, useState } from 'react';
import {
  Brain,
  CheckCircle2,
  AlertTriangle,
  Lightbulb,
  Scale,
  Sparkles,
  TrendingUp,
  RotateCcw,
  Zap,
  Activity,
} from 'lucide-react';
import { api } from '../api/client';
import { StudentProfile } from '../types';

export const ProfilePage: React.FC = () => {
  const [profile, setProfile] = useState<StudentProfile | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchProfile = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await api.getProfile();
      setProfile(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load debugging profile.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchProfile();
  }, []);

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] space-y-3">
        <div className="w-8 h-8 border-2 border-blue-400 border-t-transparent rounded-full animate-spin"></div>
        <p className="text-sm text-gray-400 font-mono">Aggregating telemetry & debugging habits...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 bg-red-950/40 border border-red-800 rounded-xl text-center space-y-3 max-w-lg mx-auto">
        <AlertTriangle className="w-8 h-8 text-red-400 mx-auto" />
        <h3 className="font-semibold text-sm text-white">Failed to Load Profile</h3>
        <p className="text-xs text-red-200">{error}</p>
        <button
          onClick={fetchProfile}
          className="px-4 py-1.5 rounded-lg bg-red-900/60 hover:bg-red-800 text-xs text-white transition-colors"
        >
          Try Again
        </button>
      </div>
    );
  }

  const habits = profile?.deterministic_habits;
  const pred = profile?.latest_prediction;

  const getArchetypeDisplay = (archetype?: string) => {
    switch (archetype) {
      case 'SYSTEMATIC_VERIFICATION':
        return {
          title: 'Systematic Verification',
          badge: 'bg-emerald-950 text-emerald-300 border-emerald-500/60',
          desc: 'High static analysis, explicit traceback inspection, and consistent countercheck disproof testing before confirming root causes.',
          icon: <CheckCircle2 className="w-5 h-5 text-emerald-400" />,
        };
      case 'RAPID_TRIAL_AND_ERROR':
        return {
          title: 'Rapid Trial-and-Error (Guess-and-Check)',
          badge: 'bg-yellow-950 text-yellow-300 border-yellow-500/60',
          desc: 'Frequent execution before static AST structure inspection, high hypothesis churn, and missing disproof experiments.',
          icon: <Zap className="w-5 h-5 text-yellow-400" />,
        };
      case 'UNFOCUSED_EXPLORATION':
        return {
          title: 'Unfocused Exploration',
          badge: 'bg-purple-950 text-purple-300 border-purple-500/60',
          desc: 'Higher tool error rate, frequent replanning, or difficulty isolating the failing stack frame.',
          icon: <Brain className="w-5 h-5 text-purple-400" />,
        };
      default:
        return {
          title: 'Awaiting Sufficient Telemetry',
          badge: 'bg-surfaceBorder text-gray-400',
          desc: 'Complete investigations in the Studio to establish your baseline debugging behavioral pattern.',
          icon: <Activity className="w-5 h-5 text-gray-400" />,
        };
    }
  };

  const archDisplay = getArchetypeDisplay(pred?.predicted_archetype);

  return (
    <div className="space-y-6">
      {/* Page Title & Refresh */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-surfaceBorder">
        <div>
          <h2 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
            <Brain className="w-5 h-5 text-blue-400" />
            Student Debugging Profile
          </h2>
          <p className="text-xs text-gray-400 mt-1">
            Continuous telemetry intelligence analyzing how you investigate, test, and verify Python bugs.
          </p>
        </div>
        <button
          onClick={fetchProfile}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-surface hover:bg-surfaceBorder border border-surfaceBorder text-xs text-gray-300 transition-colors self-start sm:self-auto"
        >
          <RotateCcw className="w-3.5 h-3.5" />
          Refresh Stats
        </button>
      </div>

      {/* Top Grid: Deterministic Habits vs AI-Detected Pattern */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left: Deterministic Debugging Habits (7 cols) */}
        <div className="lg:col-span-7 bg-surface border border-surfaceBorder rounded-xl p-5 space-y-5">
          <div className="flex items-center justify-between pb-3 border-b border-surfaceBorder">
            <div className="flex items-center gap-2">
              <Scale className="w-4 h-4 text-emerald-400" />
              <h3 className="font-semibold text-sm text-white">Observed Debugging Habits</h3>
            </div>
            <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-emerald-950 text-emerald-400 border border-emerald-800">
              100% DETERMINISTIC FACTS
            </span>
          </div>

          {/* Metric Bars */}
          <div className="space-y-4">
            {/* AST First Rate */}
            <div className="space-y-1.5">
              <div className="flex justify-between text-xs">
                <span className="text-gray-300 font-medium">Static AST Inspection Before Run</span>
                <span className="font-mono text-emerald-400 font-bold">{habits?.ast_first_rate || 0}%</span>
              </div>
              <div className="w-full h-2 rounded-full bg-background overflow-hidden border border-surfaceBorder/40">
                <div
                  className="h-full bg-emerald-500 rounded-full transition-all duration-500"
                  style={{ width: `${Math.max(2, habits?.ast_first_rate || 0)}%` }}
                ></div>
              </div>
              <span className="text-[10px] text-gray-500">
                Percentage of investigations where static syntax/AST analysis preceded code execution.
              </span>
            </div>

            {/* Traceback Framing Rate */}
            <div className="space-y-1.5">
              <div className="flex justify-between text-xs">
                <span className="text-gray-300 font-medium">Stack Trace Error Framing</span>
                <span className="font-mono text-blue-400 font-bold">{habits?.traceback_provided_rate || 0}%</span>
              </div>
              <div className="w-full h-2 rounded-full bg-background overflow-hidden border border-surfaceBorder/40">
                <div
                  className="h-full bg-blue-500 rounded-full transition-all duration-500"
                  style={{ width: `${Math.max(2, habits?.traceback_provided_rate || 0)}%` }}
                ></div>
              </div>
              <span className="text-[10px] text-gray-500">
                Percentage of sessions submitted with a concrete Python exception traceback.
              </span>
            </div>

            {/* Countercheck Disproof Rigor */}
            <div className="space-y-1.5">
              <div className="flex justify-between text-xs">
                <span className="text-gray-300 font-medium">Countercheck Disproof Rigor</span>
                <span className="font-mono text-purple-400 font-bold">{habits?.countercheck_rigor_rate || 0}%</span>
              </div>
              <div className="w-full h-2 rounded-full bg-background overflow-hidden border border-surfaceBorder/40">
                <div
                  className="h-full bg-purple-500 rounded-full transition-all duration-500"
                  style={{ width: `${Math.max(2, habits?.countercheck_rigor_rate || 0)}%` }}
                ></div>
              </div>
              <span className="text-[10px] text-gray-500">
                Rate of formulating targeted experiments to attempt disproving candidate hypotheses.
              </span>
            </div>
          </div>

          {/* Stat Cards Row */}
          <div className="grid grid-cols-3 gap-3 pt-2">
            <div className="p-3 bg-background border border-surfaceBorder rounded-lg text-center">
              <div className="text-lg font-bold font-mono text-white">{habits?.total_sessions || 0}</div>
              <div className="text-[10px] text-gray-400 mt-0.5">Sessions Analyzed</div>
            </div>
            <div className="p-3 bg-background border border-surfaceBorder rounded-lg text-center">
              <div className="text-lg font-bold font-mono text-white">{habits?.avg_investigation_steps || 0}</div>
              <div className="text-[10px] text-gray-400 mt-0.5">Avg Steps/Session</div>
            </div>
            <div className="p-3 bg-background border border-surfaceBorder rounded-lg text-center">
              <div className="text-lg font-bold font-mono text-white">{habits?.tool_failure_rate || 0}%</div>
              <div className="text-[10px] text-gray-400 mt-0.5">Tool Error Rate</div>
            </div>
          </div>
        </div>

        {/* Right: AI-Detected Pattern (5 cols) */}
        <div className="lg:col-span-5 bg-surface border border-surfaceBorder rounded-xl p-5 space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-surfaceBorder">
            <div className="flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-yellow-400" />
              <h3 className="font-semibold text-sm text-white">AI-Detected Behavior Pattern</h3>
            </div>
            <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-blue-950 text-blue-400 border border-blue-800">
              {pred?.model_type || 'RandomForest'}
            </span>
          </div>

          {/* Archetype Card */}
          <div className="p-4 bg-background border border-surfaceBorder rounded-xl space-y-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                {archDisplay.icon}
                <span className="text-xs font-bold text-white">{archDisplay.title}</span>
              </div>
              {pred && (
                <span className="text-xs font-mono font-bold text-emerald-400">
                  {Math.round(pred.confidence * 100)}% conf
                </span>
              )}
            </div>
            <p className="text-[11px] text-gray-400 leading-relaxed">{archDisplay.desc}</p>
          </div>

          {/* Contributing Factors */}
          {pred?.top_contributing_factors && pred.top_contributing_factors.length > 0 && (
            <div className="space-y-2">
              <span className="text-[10px] font-mono font-semibold text-gray-400 uppercase tracking-wider">
                Contributing Telemetry Signals
              </span>
              <div className="space-y-1.5">
                {pred.top_contributing_factors.map((factor, idx) => (
                  <div
                    key={idx}
                    className="p-2 bg-background/60 border border-surfaceBorder/60 rounded-lg text-[11px] flex items-start gap-2 text-gray-300"
                  >
                    <span
                      className={`w-1.5 h-1.5 rounded-full shrink-0 mt-1.5 ${
                        factor.contribution_weight >= 0 ? 'bg-emerald-400' : 'bg-red-400'
                      }`}
                    ></span>
                    <span>{factor.description}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Pedagogical Explanation */}
          {pred?.pedagogical_explanation && (
            <div className="p-3 bg-blue-950/20 border border-blue-800/40 rounded-xl space-y-1 text-xs">
              <span className="text-[10px] font-mono text-blue-400 font-bold flex items-center gap-1.5 uppercase">
                <Lightbulb className="w-3.5 h-3.5" />
                Pedagogical Analysis
              </span>
              <p className="text-gray-300 text-[11px] leading-relaxed">
                {pred.pedagogical_explanation}
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Bottom Grid: Strengths & Growth Areas */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Key Strengths */}
        <div className="bg-surface border border-surfaceBorder rounded-xl p-5 space-y-3">
          <div className="flex items-center gap-2 pb-2 border-b border-surfaceBorder">
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
            <h3 className="font-semibold text-sm text-white">Demonstrated Debugging Strengths</h3>
          </div>
          <div className="space-y-2">
            {profile?.key_strengths.map((strText, idx) => (
              <div
                key={idx}
                className="p-3 bg-background border border-surfaceBorder rounded-lg text-xs flex items-start gap-2.5 text-gray-200"
              >
                <span className="px-1.5 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-800 text-[10px] font-mono shrink-0">
                  VERIFIED
                </span>
                <span className="leading-relaxed">{strText}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Areas for Growth */}
        <div className="bg-surface border border-surfaceBorder rounded-xl p-5 space-y-3">
          <div className="flex items-center gap-2 pb-2 border-b border-surfaceBorder">
            <TrendingUp className="w-4 h-4 text-yellow-400" />
            <h3 className="font-semibold text-sm text-white">Recommended Growth Areas</h3>
          </div>
          <div className="space-y-2">
            {profile?.growth_areas.map((growthText, idx) => (
              <div
                key={idx}
                className="p-3 bg-background border border-surfaceBorder rounded-lg text-xs flex items-start gap-2.5 text-gray-200"
              >
                <span className="px-1.5 py-0.5 rounded bg-yellow-950 text-yellow-400 border border-yellow-800 text-[10px] font-mono shrink-0">
                  TARGET
                </span>
                <span className="leading-relaxed">{growthText}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
