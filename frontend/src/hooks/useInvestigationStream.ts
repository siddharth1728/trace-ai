/**
 * React Hook managing real-time Server-Sent Events (SSE) stream for an active investigation.
 */

import { useEffect, useRef, useState, useCallback } from 'react';
import {
  Countercheck,
  Evidence,
  FinalDiagnosis,
  Hypothesis,
  Observation,
  PlanStep,
  SessionDetail,
  SessionStatus,
} from '../types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

export interface InvestigationStreamState {
  status: SessionStatus;
  confidence: number;
  planSteps: PlanStep[];
  observations: Observation[];
  evidence: Evidence[];
  hypotheses: Hypothesis[];
  counterchecks: Countercheck[];
  diagnosis: FinalDiagnosis | null;
  activeTool: string | null;
  currentStepIndex: number | null;
  isConnected: boolean;
  error: string | null;
}

export function useInvestigationStream(
  sessionId: string | null,
  initialData?: SessionDetail | null
) {
  const [streamState, setStreamState] = useState<InvestigationStreamState>({
    status: initialData?.status || 'CREATED',
    confidence: initialData?.confidence || 0,
    planSteps: initialData?.plan_steps || [],
    observations: initialData?.observations || [],
    evidence: initialData?.evidence || [],
    hypotheses: initialData?.hypotheses || [],
    counterchecks: initialData?.counterchecks || [],
    diagnosis: initialData?.diagnosis || null,
    activeTool: null,
    currentStepIndex: null,
    isConnected: false,
    error: null,
  });

  const eventSourceRef = useRef<EventSource | null>(null);

  // Sync initialData if sessionId changes
  useEffect(() => {
    if (initialData) {
      setStreamState({
        status: initialData.status,
        confidence: initialData.confidence,
        planSteps: initialData.plan_steps || [],
        observations: initialData.observations || [],
        evidence: initialData.evidence || [],
        hypotheses: initialData.hypotheses || [],
        counterchecks: initialData.counterchecks || [],
        diagnosis: initialData.diagnosis || null,
        activeTool: null,
        currentStepIndex: null,
        isConnected: false,
        error: null,
      });
    }
  }, [initialData]);

  const disconnect = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
      setStreamState((prev) => ({ ...prev, isConnected: false, activeTool: null }));
    }
  }, []);

  useEffect(() => {
    if (!sessionId) {
      disconnect();
      return;
    }

    // Do not open SSE if session is already completed or failed in initialData
    if (initialData && ['COMPLETED', 'FAILED', 'BLOCKED'].includes(initialData.status)) {
      return;
    }

    disconnect();

    const sseUrl = `${API_BASE_URL}/api/sessions/${sessionId}/events`;
    const es = new EventSource(sseUrl);
    eventSourceRef.current = es;

    es.onopen = () => {
      setStreamState((prev) => ({ ...prev, isConnected: true, error: null }));
    };

    es.onerror = () => {
      // EventSource reconnects automatically on network hiccups
      setStreamState((prev) => ({ ...prev, isConnected: false }));
    };

    // 1. Session Status
    es.addEventListener('session_status', (e) => {
      try {
        const data = JSON.parse(e.data);
        const payload = data.payload || data;
        if (payload.status) {
          setStreamState((prev) => ({ ...prev, status: payload.status }));
        }
      } catch (err) {
        console.error('Failed to parse session_status event:', err);
      }
    });

    // 2. State Transition
    es.addEventListener('STATE_TRANSITION', (e) => {
      try {
        const data = JSON.parse(e.data);
        const newStatus = data.payload?.new_state;
        if (newStatus) {
          setStreamState((prev) => ({
            ...prev,
            status: ['COMPLETED', 'FAILED', 'BLOCKED'].includes(newStatus) ? newStatus : 'RUNNING',
          }));
        }
      } catch (err) {
        console.error('Failed to parse STATE_TRANSITION event:', err);
      }
    });

    // 3. Plan Created
    es.addEventListener('PLAN_CREATED', (e) => {
      try {
        const data = JSON.parse(e.data);
        const rawSteps = data.payload?.steps || [];
        const planSteps: PlanStep[] = rawSteps.map((s: any) => ({
          id: s.id || `step_${s.step_id}`,
          step_index: s.step_id || 1,
          title: s.title || '',
          tool_name: s.tool_name || '',
          status: 'PENDING',
          expected_outcome: s.expected_outcome || '',
          observation_id: s.observation_id,
        }));
        setStreamState((prev) => ({ ...prev, planSteps }));
      } catch (err) {
        console.error('Failed to parse PLAN_CREATED event:', err);
      }
    });

    // 4. Step Started
    es.addEventListener('STEP_STARTED', (e) => {
      try {
        const data = JSON.parse(e.data);
        const stepId = data.payload?.step_id;
        const toolName = data.payload?.tool_name;
        setStreamState((prev) => ({
          ...prev,
          activeTool: toolName || prev.activeTool,
          currentStepIndex: stepId,
          planSteps: prev.planSteps.map((step) =>
            step.step_index === stepId ? { ...step, status: 'IN_PROGRESS' } : step
          ),
        }));
      } catch (err) {
        console.error('Failed to parse STEP_STARTED event:', err);
      }
    });

    // 5. Tool Completed
    es.addEventListener('TOOL_COMPLETED', (e) => {
      try {
        const data = JSON.parse(e.data);
        const stepId = data.payload?.step_id;
        const success = data.payload?.success;
        setStreamState((prev) => ({
          ...prev,
          activeTool: null,
          planSteps: prev.planSteps.map((step) =>
            step.step_index === stepId
              ? { ...step, status: success ? 'DONE' : 'FAILED' }
              : step
          ),
        }));
      } catch (err) {
        console.error('Failed to parse TOOL_COMPLETED event:', err);
      }
    });

    // 6. Observation Recorded
    es.addEventListener('OBSERVATION_RECORDED', (e) => {
      try {
        const data = JSON.parse(e.data);
        const payload = data.payload || {};
        const newObs: Observation = {
          id: payload.observation_id || `obs_${Date.now()}`,
          step_index: payload.step_id || 0,
          tool_name: payload.tool_name || '',
          summary: payload.summary || '',
          is_success: payload.is_success !== false,
          input_args: payload.input_args || {},
          output_data: payload.output_data || {},
          evidence_tags: payload.evidence_tags || [],
          created_at: new Date().toISOString(),
        };
        setStreamState((prev) => {
          if (prev.observations.some((o) => o.id === newObs.id)) return prev;
          return { ...prev, observations: [...prev.observations, newObs] };
        });
      } catch (err) {
        console.error('Failed to parse OBSERVATION_RECORDED event:', err);
      }
    });

    // 7. Evidence Extracted
    es.addEventListener('EVIDENCE_EXTRACTED', (e) => {
      try {
        const data = JSON.parse(e.data);
        const payload = data.payload || {};
        const newEv: Evidence = {
          id: payload.evidence_id || `evi_${Date.now()}`,
          observation_id: payload.observation_id,
          target_hypothesis_id: payload.target_hypothesis_id,
          evidence_type: payload.evidence_type || 'DIRECT',
          relation: payload.relation || 'SUPPORTS',
          statement: payload.statement || '',
          confidence_weight: payload.confidence_weight || 1.0,
          created_at: new Date().toISOString(),
        };
        setStreamState((prev) => {
          if (prev.evidence.some((ev) => ev.id === newEv.id)) return prev;
          return { ...prev, evidence: [...prev.evidence, newEv] };
        });
      } catch (err) {
        console.error('Failed to parse EVIDENCE_EXTRACTED event:', err);
      }
    });

    // 8. Hypothesis Proposed / Updated
    const handleHypothesisEvent = (e: MessageEvent) => {
      try {
        const data = JSON.parse(e.data);
        const payload = data.payload || {};
        const hypId = payload.hypothesis_id;
        if (!hypId) return;

        setStreamState((prev) => {
          const exists = prev.hypotheses.some((h) => h.id === hypId);
          if (exists) {
            return {
              ...prev,
              hypotheses: prev.hypotheses.map((h) =>
                h.id === hypId
                  ? {
                      ...h,
                      status: payload.status || h.status,
                      confidence: payload.confidence ?? h.confidence,
                      rationale: payload.rationale || h.rationale,
                    }
                  : h
              ),
            };
          } else {
            const newHyp: Hypothesis = {
              id: hypId,
              statement: payload.statement || '',
              status: payload.status || 'PROPOSED',
              confidence: payload.confidence || 0.2,
              rationale: payload.rationale || '',
              supporting_evidence_ids: [],
              counterexample_ids: [],
            };
            return { ...prev, hypotheses: [...prev.hypotheses, newHyp] };
          }
        });
      } catch (err) {
        console.error('Failed to parse hypothesis event:', err);
      }
    };
    es.addEventListener('HYPOTHESIS_PROPOSED', handleHypothesisEvent);
    es.addEventListener('HYPOTHESIS_UPDATED', handleHypothesisEvent);

    // 9. Countercheck Completed
    es.addEventListener('COUNTERCHECK_COMPLETED', (e) => {
      try {
        const data = JSON.parse(e.data);
        const payload = data.payload || {};
        const newCountercheck: Countercheck = {
          id: payload.experiment_id || `cexp_${Date.now()}`,
          hypothesis_id: payload.hypothesis_id || '',
          strategy: payload.strategy || 'TARGETED_CHECK',
          description: payload.description || '',
          harness_code: payload.harness_code || '',
          executed: true,
          passed: payload.passed === true,
          disproved: payload.disproved === true,
          actual_output: payload.actual_output || payload.evidence_statement || '',
        };
        setStreamState((prev) => {
          if (prev.counterchecks.some((c) => c.id === newCountercheck.id)) return prev;
          return { ...prev, counterchecks: [...prev.counterchecks, newCountercheck] };
        });
      } catch (err) {
        console.error('Failed to parse COUNTERCHECK_COMPLETED event:', err);
      }
    });

    // 10. Diagnosis Formed / Ready
    const handleDiagnosisReady = (e: MessageEvent) => {
      try {
        const data = JSON.parse(e.data);
        const payload = data.payload || data;
        if (payload) {
          const diag: FinalDiagnosis = {
            problem_statement: payload.problem_statement,
            likely_root_cause: payload.likely_root_cause,
            learning_point: payload.learning_point,
            suggested_fix_guidance: payload.suggested_fix_guidance,
            confidence: payload.confidence || 0.9,
            verified_hypothesis_id: payload.verified_hypothesis_id,
            countercheck_summary: payload.countercheck_summary,
            what_trace_checked: payload.what_trace_checked || [],
            what_remains_uncertain: payload.what_remains_uncertain || [],
            evidence_summary: payload.evidence_summary || [],
          };
          setStreamState((prev) => ({
            ...prev,
            diagnosis: diag,
            confidence: diag.confidence,
          }));
        }
      } catch (err) {
        console.error('Failed to parse diagnosis event:', err);
      }
    };
    es.addEventListener('DIAGNOSIS_FORMED', handleDiagnosisReady);
    es.addEventListener('diagnosis_ready', handleDiagnosisReady);

    // 11. Session Completed
    es.addEventListener('SESSION_COMPLETED', (e) => {
      try {
        const data = JSON.parse(e.data);
        const payload = data.payload || {};
        setStreamState((prev) => ({
          ...prev,
          status: 'COMPLETED',
          confidence: payload.confidence ?? prev.confidence,
          activeTool: null,
          currentStepIndex: null,
        }));
        disconnect();
      } catch (err) {
        console.error('Failed to parse SESSION_COMPLETED event:', err);
      }
    });
    es.addEventListener('session_completed', (e) => {
      try {
        const data = JSON.parse(e.data);
        setStreamState((prev) => ({
          ...prev,
          status: data.status || 'COMPLETED',
          confidence: data.confidence ?? prev.confidence,
          activeTool: null,
        }));
        disconnect();
      } catch (err) {
        console.error('Failed to parse session_completed event:', err);
      }
    });

    // 12. Session Failed
    es.addEventListener('SESSION_FAILED', (e) => {
      try {
        const data = JSON.parse(e.data);
        const payload = data.payload || {};
        setStreamState((prev) => ({
          ...prev,
          status: 'FAILED',
          error: payload.error || 'Investigation encountered an unrecoverable failure.',
          activeTool: null,
        }));
        disconnect();
      } catch (err) {
        console.error('Failed to parse SESSION_FAILED event:', err);
      }
    });

    return () => {
      disconnect();
    };
  }, [sessionId, initialData, disconnect]);

  return streamState;
}
