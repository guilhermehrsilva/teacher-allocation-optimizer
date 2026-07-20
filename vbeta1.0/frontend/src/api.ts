import type {
  AllocationPage,
  DashboardData,
  DashboardFilters,
  InsightsData,
  Job,
  Scenario,
  ScenarioCatalog,
  ScenarioChange,
  ScenarioPolicy,
  ScenarioComparison,
  Summary,
  UploadResult,
} from "./types";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, init);
  if (!response.ok) {
    let message = `Erro ${response.status}`;
    try {
      const payload = await response.json();
      message = payload.detail ?? message;
    } catch {
      // Mantém a mensagem HTTP quando a resposta não é JSON.
    }
    throw new Error(message);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export async function validateUpload(file: File, module: number): Promise<UploadResult> {
  const form = new FormData();
  form.append("file", file);
  form.append("module", String(module));
  return request<UploadResult>("/api/uploads", { method: "POST", body: form });
}

export async function createJob(
  uploadId: string,
  confirmWarnings: boolean,
): Promise<Job> {
  return request<Job>("/api/jobs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      upload_id: uploadId,
      confirm_warnings: confirmWarnings,
      require_optimal: true,
      time_limit_seconds: null,
    }),
  });
}

export const listJobs = () => request<Job[]>("/api/jobs");
export const resetPrimaryJobs = (scope: "latest" | "all") =>
  request<{ deleted_rounds: number; deleted_scenarios: number }>(`/api/jobs/primary?scope=${scope}`, { method: "DELETE" });
export const listAnalysisJobs = () => request<Job[]>("/api/analysis-jobs");
export const getJob = (jobId: string) => request<Job>(`/api/jobs/${jobId}`);
export const getSummary = (jobId: string) =>
  request<Summary>(`/api/jobs/${jobId}/summary`);
export const getDashboard = (jobId: string, filters?: DashboardFilters) => {
  const query = new URLSearchParams();
  if (filters) {
    Object.entries(filters).forEach(([key, values]) => {
      values.forEach((value) => query.append(key, value));
    });
  }
  const suffix = query.size ? `?${query}` : "";
  return request<DashboardData>(`/api/dashboard/${jobId}${suffix}`);
};
export const getInsights = (jobId: string) =>
  request<InsightsData>(`/api/insights/${jobId}`);

export const listScenarios = () => request<Scenario[]>("/api/scenarios");
export const resetSavedScenarios = (scope: "latest" | "all") =>
  request<{ deleted_scenarios: number }>(`/api/scenarios?scope=${scope}`, { method: "DELETE" });
export const getScenario = (scenarioId: string) =>
  request<Scenario>(`/api/scenarios/${scenarioId}`);
export const createScenario = (
  baselineJobId: string,
  name: string,
  description: string,
) => request<Scenario>("/api/scenarios", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ baseline_job_id: baselineJobId, name, description }),
});
export const getScenarioCatalog = (scenarioId: string) =>
  request<ScenarioCatalog>(`/api/scenarios/${scenarioId}/catalog`);
export const addScenarioChange = (
  scenarioId: string,
  payload: {
    change_type: string;
    entity_type: string;
    row_number: number;
    field_name: string;
    new_value: string | number;
  },
) => request<ScenarioChange>(`/api/scenarios/${scenarioId}/changes`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(payload),
});
export const deleteScenarioChange = (scenarioId: string, changeId: string) =>
  request<void>(`/api/scenarios/${scenarioId}/changes/${changeId}`, { method: "DELETE" });
export const addScenarioPolicy = (
  scenarioId: string,
  payload: {
    policy_type: string;
    target_type: string;
    target_value: string;
    configuration?: Record<string, string | number | boolean>;
  },
) => request<ScenarioPolicy>(`/api/scenarios/${scenarioId}/policies`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(payload),
});
export const deleteScenarioPolicy = (scenarioId: string, policyId: string) =>
  request<void>(`/api/scenarios/${scenarioId}/policies/${policyId}`, { method: "DELETE" });
export const runScenario = (scenarioId: string) =>
  request<Job>(`/api/scenarios/${scenarioId}/runs`, { method: "POST" });
export const getScenarioComparison = (scenarioId: string) =>
  request<ScenarioComparison>(`/api/scenarios/${scenarioId}/comparison`);
export const promoteScenario = (scenarioId: string) =>
  request<Scenario>(`/api/scenarios/${scenarioId}/promote`, { method: "POST" });

export function getAllocations(
  jobId: string,
  page: number,
  status = "",
  search = "",
): Promise<AllocationPage> {
  const query = new URLSearchParams({ page: String(page), page_size: "25" });
  if (status) query.set("status", status);
  if (search) query.set("search", search);
  return request<AllocationPage>(`/api/jobs/${jobId}/allocations?${query}`);
}

export const artifactUrl = (jobId: string, key: string) =>
  `/api/jobs/${jobId}/artifacts/${key}`;
