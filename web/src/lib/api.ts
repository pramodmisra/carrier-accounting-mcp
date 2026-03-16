/**
 * Typed API client for the Carrier Accounting REST API.
 * All endpoints return JSON and require Authorization header.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || '';

class ApiClient {
  private token: string = '';

  setToken(token: string) {
    this.token = token;
  }

  private async request<T>(path: string, options: RequestInit = {}): Promise<T> {
    const res = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...(this.token ? { Authorization: `Bearer ${this.token}` } : {}),
        ...options.headers,
      },
    });

    if (!res.ok) {
      const error = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(error.detail || `API error: ${res.status}`);
    }

    return res.json();
  }

  // --- Monitoring ---
  getDailyMetrics(date?: string) {
    const params = date ? `?target_date=${date}` : '';
    return this.request<DailyMetrics>(`/api/metrics/daily${params}`);
  }

  getCarrierAccuracy(carrier: string, days = 30) {
    return this.request<CarrierAccuracy>(`/api/metrics/carrier/${carrier}?days=${days}`);
  }

  getRunHistory(days = 7) {
    return this.request<RunSummary[]>(`/api/runs?days=${days}`);
  }

  getRunDetail(runId: string) {
    return this.request<RunDetail>(`/api/runs/${runId}`);
  }

  // --- Ingestion ---
  async uploadFile(file: File): Promise<UploadResponse> {
    const form = new FormData();
    form.append('file', file);
    const res = await fetch(`${API_BASE}/api/upload`, {
      method: 'POST',
      headers: this.token ? { Authorization: `Bearer ${this.token}` } : {},
      body: form,
    });
    if (!res.ok) throw new Error('Upload failed');
    return res.json();
  }

  ingestStatement(filePath: string, carrier: string, mode = 'trial') {
    return this.request<IngestResponse>('/api/ingest', {
      method: 'POST',
      body: JSON.stringify({ file_path: filePath, carrier, mode }),
    });
  }

  // --- Review ---
  getExceptionQueue(date?: string, carrier?: string) {
    const params = new URLSearchParams();
    if (date) params.set('target_date', date);
    if (carrier) params.set('carrier', carrier);
    return this.request<Transaction[]>(`/api/queue?${params}`);
  }

  approveTransaction(id: string, reviewer: string, notes?: string) {
    return this.request(`/api/transactions/${id}/approve`, {
      method: 'POST',
      body: JSON.stringify({ reviewer, notes }),
    });
  }

  rejectTransaction(id: string, reviewer: string, reason: string) {
    return this.request(`/api/transactions/${id}/reject`, {
      method: 'POST',
      body: JSON.stringify({ reviewer, reason }),
    });
  }

  approveBatch(runId: string, reviewer: string) {
    return this.request(`/api/runs/${runId}/approve-batch`, {
      method: 'POST',
      body: JSON.stringify({ reviewer }),
    });
  }

  // --- Posting ---
  postToEpic(runId: string) {
    return this.request(`/api/runs/${runId}/post-to-epic`, { method: 'POST' });
  }

  generateImport(runId: string) {
    return this.request<GenerateImportResponse>(`/api/runs/${runId}/generate-import`, {
      method: 'POST',
    });
  }

  rollbackRun(runId: string, reason: string) {
    return this.request(`/api/runs/${runId}/rollback`, {
      method: 'POST',
      body: JSON.stringify({ reason }),
    });
  }

  // --- Reconciliation ---
  getReconciliation(params: { run_id?: string; carrier?: string; target_date?: string }) {
    const qs = new URLSearchParams(Object.entries(params).filter(([, v]) => v));
    return this.request(`/api/reconciliation?${qs}`);
  }

  getTrialDiff(params: { run_id?: string; carrier?: string; target_date?: string }) {
    const qs = new URLSearchParams(Object.entries(params).filter(([, v]) => v));
    return this.request(`/api/trial-diff?${qs}`);
  }

  scoreCheck(data: ScoreCheckRequest) {
    return this.request<ScoreCheckResponse>('/api/score-check', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  // --- Carriers ---
  getCarriers() {
    return this.request<CarrierListResponse>('/api/carriers');
  }

  addCarrier(config: CarrierConfig) {
    return this.request('/api/carriers', {
      method: 'POST',
      body: JSON.stringify(config),
    });
  }

  // --- Admin ---
  getSettings() {
    return this.request('/api/admin/settings');
  }
}

export const api = new ApiClient();

// --- Types ---
export interface DailyMetrics {
  total_transactions: number;
  auto_approved: number;
  review_queue: number;
  failed: number;
  posted_to_epic: number;
  rejected: number;
  avg_confidence: number | null;
  total_amount: number | null;
}

export interface Transaction {
  transaction_id: string;
  carrier: string;
  policy_number: string;
  client_name: string;
  amount: string;
  confidence_score: number;
  status: string;
  transaction_type: string;
  validation_warnings: string[];
  validation_errors: string[];
}

export interface RunSummary {
  run_id: string;
  source_file: string;
  carrier: string;
  mode: string;
  total_transactions: number;
  auto_approved: number;
  review_queue: number;
  failed: number;
  status: string;
  started_at: string;
}

export interface RunDetail {
  run: RunSummary;
  transactions: Transaction[];
  transaction_count: number;
}

export interface IngestResponse {
  run_id: string;
  carrier: string;
  mode: string;
  total_parsed: number;
  auto_approved: number;
  review_queue: number;
  rejected: number;
}

export interface UploadResponse {
  file_id: string;
  filename: string;
  file_path: string;
}

export interface GenerateImportResponse {
  status: string;
  file_path: string;
  row_count: number;
  total_amount: string;
}

export interface CarrierAccuracy {
  carrier: string;
  total: number;
  avg_confidence: number;
  post_rate: number;
  rejection_rate: number;
}

export interface CarrierConfig {
  carrier_slug: string;
  display_name: string;
  policy_number_field: string;
  premium_field: string;
  mode: string;
}

export interface CarrierListResponse {
  carriers: CarrierConfig[];
  total: number;
}

export interface ScoreCheckRequest {
  carrier: string;
  policy_number: string;
  client_name: string;
  amount: string;
  effective_date?: string;
}

export interface ScoreCheckResponse {
  confidence_score: number;
  classification: string;
  confidence_factors: Record<string, number>;
  policy_found: boolean;
  is_duplicate: boolean;
}
