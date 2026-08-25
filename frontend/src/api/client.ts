/**
 * Centralized Typed API Client for TRACE v0.3 Backend.
 */

import {
  CreateSessionPayload,
  HealthResponse,
  InvestigatePayload,
  SessionDetail,
  SessionListResponse,
  StudentProfile,
} from '../types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let errorMsg = `API Error: ${response.status} ${response.statusText}`;
    try {
      const errJson = await response.json();
      if (errJson.detail) {
        errorMsg = errJson.detail;
      }
    } catch {
      // Ignore JSON parse error
    }
    throw new Error(errorMsg);
  }
  return response.json();
}

export const api = {
  /**
   * Check backend server health status.
   */
  async getHealth(): Promise<HealthResponse> {
    const response = await fetch(`${API_BASE_URL}/api/health`);
    return handleResponse<HealthResponse>(response);
  },

  /**
   * Create a new debugging session from text payload.
   */
  async createSession(payload: CreateSessionPayload): Promise<SessionDetail> {
    const response = await fetch(`${API_BASE_URL}/api/sessions`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });
    return handleResponse<SessionDetail>(response);
  },

  /**
   * Create a new debugging session from uploaded Python file.
   */
  async uploadSession(
    file: File,
    userGoal: string,
    errorDescription?: string,
    tracebackInput?: string
  ): Promise<SessionDetail> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('user_goal', userGoal);
    if (errorDescription) formData.append('error_description', errorDescription);
    if (tracebackInput) formData.append('traceback_input', tracebackInput);

    const response = await fetch(`${API_BASE_URL}/api/sessions/upload`, {
      method: 'POST',
      body: formData,
    });
    return handleResponse<SessionDetail>(response);
  },

  /**
   * List historical debugging sessions with pagination.
   */
  async getSessions(limit = 50, offset = 0): Promise<SessionListResponse> {
    const response = await fetch(`${API_BASE_URL}/api/sessions?limit=${limit}&offset=${offset}`);
    return handleResponse<SessionListResponse>(response);
  },

  /**
   * Fetch complete session snapshot and investigation status.
   */
  async getSession(sessionId: string): Promise<SessionDetail> {
    const response = await fetch(`${API_BASE_URL}/api/sessions/${sessionId}`);
    return handleResponse<SessionDetail>(response);
  },

  /**
   * Start an automated background investigation.
   */
  async startInvestigation(
    sessionId: string,
    payload: InvestigatePayload = { provider: 'mock', max_iterations: 8 }
  ): Promise<{ session_id: string; status: string; message: string }> {
    const response = await fetch(`${API_BASE_URL}/api/sessions/${sessionId}/investigate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });
    return handleResponse<{ session_id: string; status: string; message: string }>(response);
  },

  /**
   * Delete a debugging session and associated data.
   */
  async deleteSession(sessionId: string): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/api/sessions/${sessionId}`, {
      method: 'DELETE',
    });
    if (!response.ok && response.status !== 204) {
      throw new Error(`Failed to delete session: ${response.status}`);
    }
  },

  /**
   * Get the aggregated student debugging profile.
   */
  async getProfile(): Promise<StudentProfile> {
    const response = await fetch(`${API_BASE_URL}/api/profile`);
    return handleResponse<StudentProfile>(response);
  },

  /**
   * Fetch 18-feature telemetry vector for a session.
   */
  async getSessionTelemetry(sessionId: string): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/api/sessions/${sessionId}/telemetry`);
    return handleResponse<any>(response);
  },
};
