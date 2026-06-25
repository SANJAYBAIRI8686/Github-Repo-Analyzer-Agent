import { API_BASE_URL } from "./config";
import { getToken } from "./auth";

export type TokenResponse = {
  access_token: string;
  token_type: string;
  user: { id: number; email: string; created_at: string };
};

export type OverviewResponse = {
  repository_id: number;
  project_name: string | null;
  purpose: string | null;
  main_language: string | null;
  framework: string | null;
  file_count: number;
  dependencies: string[];
  architecture_summary: string | null;
  complexity: string | null;
  learning_difficulty: string | null;
  folder_explanations: Record<string, string>;
};

export type HealthResponse = {
  repository_id: number;
  overall_score: number;
  overall_stars: number;
  categories: Array<{ name: string; score: number; max_score: number; stars: number; rationale: string; signals: string[] }>;
};

export type ArchitectureResponse = { repository_id: number; diagram_format: string; diagram_source: string; explanation: string };
export type DocsBundleResponse = { repository_id: number; files: Array<{ filename: string; content: string }>; download_url: string };
export type SearchResponse = { repository_id: number; query: string; hits: Array<{ chunk_id: string; file_path: string | null; language: string | null; symbol_name: string | null; start_line: number | null; end_line: number | null; snippet: string; score: number | null; citation: string }> };
export type DependencyResponse = { repository_id: number; dependencies: Array<{ name: string; spec: string | null; description: string; why_used: string; source_file: string | null }> };
export type ExplainResponse = { purpose: string; inputs: string[]; outputs: string[]; complexity: string; improvements: string[]; citations: string[] };
export type AnalysisResponse = { repository_id: number; findings: Array<{ severity: string; title: string; details: string; file_path: string | null; line: number | null; kind: string }> };
export type OnboardingResponse = { repository_id: number; lessons: Array<{ slug: string; title: string; objective: string; summary: string; file_refs: string[]; checkpoint_question: string; checkpoint_hint: string }> };
export type ChatSession = { id: number; repository_id: number; user_id: number | null; title: string | null; created_at: string; updated_at: string };
export type ChatMessage = { id: number; chat_session_id: number; role: string; content: string; citations: Array<{ file_path: string; line_start?: number | null; line_end?: number | null; symbol_name?: string | null }> | null; created_at: string };

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers = new Headers(init.headers);
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  if (!(init.body instanceof FormData) && init.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const response = await fetch(`${API_BASE_URL}${path}`, { ...init, headers, cache: "no-store" });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return (await response.json()) as T;
}

export async function register(email: string, password: string) {
  return request<TokenResponse>("/auth/register", { method: "POST", body: JSON.stringify({ email, password }) });
}

export async function login(email: string, password: string) {
  return request<TokenResponse>("/auth/login", { method: "POST", body: JSON.stringify({ email, password }) });
}

export async function submitRepository(url: string, branch?: string, shallow_clone = true) {
  return request<{ repository: { id: number; url: string; status: string }; job_id: number }>("/repositories", {
    method: "POST",
    body: JSON.stringify({ url, branch: branch || null, shallow_clone }),
  });
}

export async function getJob(jobId: number) {
  return request<{ job: { id: number; repository_id: number; status: string; progress_pct: number; stage: string | null; error: string | null } }>(`/jobs/${jobId}`);
}

export async function getOverview(repositoryId: number) {
  return request<OverviewResponse>(`/repos/${repositoryId}/overview`);
}

export async function getHealth(repositoryId: number) {
  return request<HealthResponse>(`/repos/${repositoryId}/health`);
}

export async function getArchitecture(repositoryId: number) {
  return request<ArchitectureResponse>(`/repos/${repositoryId}/architecture`);
}

export async function generateDocs(repositoryId: number) {
  return request<DocsBundleResponse>(`/repos/${repositoryId}/docs/generate`, { method: "POST" });
}

export async function downloadDocsZip(repositoryId: number) {
  const response = await fetch(`${API_BASE_URL}/repos/${repositoryId}/docs/download`, { headers: getToken() ? { Authorization: `Bearer ${getToken()}` } : undefined });
  if (!response.ok) throw new Error(await response.text());
  return response.blob();
}

export async function getDependencies(repositoryId: number) {
  return request<DependencyResponse>(`/repos/${repositoryId}/deps`);
}

export async function searchRepository(repositoryId: number, query: string, file_path?: string, language?: string, symbol_name?: string) {
  return request<SearchResponse>(`/repos/${repositoryId}/search`, { method: "POST", body: JSON.stringify({ query, file_path, language, symbol_name }) });
}

export async function explainCode(payload: { repo_id?: number; code?: string; symbol_name?: string; file_path?: string; language?: string }) {
  return request<ExplainResponse>("/explain", { method: "POST", body: JSON.stringify(payload) });
}

export async function getFindings(repositoryId: number, kind: "bugs" | "security") {
  return request<AnalysisResponse>(`/repos/${repositoryId}/${kind}`, { method: "POST" });
}

export async function getOnboarding(repositoryId: number) {
  return request<OnboardingResponse>(`/repos/${repositoryId}/onboarding`);
}

export async function getOnboardingLesson(repositoryId: number, slug: string) {
  return request<{ repository_id: number; lesson: OnboardingResponse["lessons"][number] }>(`/repos/${repositoryId}/onboarding/${slug}`);
}

export async function createChatSession(repositoryId: number, title?: string) {
  return request<ChatSession>(`/repos/${repositoryId}/sessions`, { method: "POST", body: JSON.stringify({ title: title || null }) });
}

export async function getChatSessions(repositoryId: number) {
  return request<ChatSession[]>(`/repos/${repositoryId}/sessions`);
}

export async function getChatHistory(repositoryId: number, sessionId: number) {
  return request<ChatMessage[]>(`/repos/${repositoryId}/sessions/${sessionId}`);
}

export async function streamChat(repositoryId: number, payload: { message: string; session_id?: number; file_path?: string; language?: string; symbol_name?: string }, onChunk: (chunk: string) => void) {
  const token = getToken();
  const response = await fetch(`${API_BASE_URL}/repos/${repositoryId}/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(payload),
  });
  if (!response.ok || !response.body) throw new Error(await response.text());
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    onChunk(decoder.decode(value, { stream: true }));
  }
  return response.headers.get("X-Chat-Session-Id");
}
