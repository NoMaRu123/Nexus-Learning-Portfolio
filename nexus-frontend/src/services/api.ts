/**
 * Axios-based API client for the Nexus backend.
 *
 * - Base URL sourced from VITE_API_URL env var
 * - JWT injected automatically via request interceptor
 * - Consistent error extraction via response interceptor
 */

import axios, { AxiosError } from "axios";
import type {
  ApiError,
  ApiResponse,
  EntryCreate,
  LearningEntry,
  PaginatedResponse,
  ProfileUpdate,
  Project,
  ProjectCreate,
  ProjectUpdate,
  PublicProfile,
  SearchResponse,
  Skill,
  SkillCreate,
  SkillUpdate,
  TokenResponse,
  RegisterResponse,
  UserProfile,
} from "@/types";

// ---------------------------------------------------------------------------
// Axios instance
// ---------------------------------------------------------------------------

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? "http://localhost:8000",
  headers: { "Content-Type": "application/json" },
});

// ---------------------------------------------------------------------------
// Request interceptor — inject JWT
// ---------------------------------------------------------------------------

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("nexus_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// ---------------------------------------------------------------------------
// Response interceptor — extract error message
// ---------------------------------------------------------------------------

api.interceptors.response.use(
  (response) => response,
  (error: AxiosError<ApiError>) => {
    const message =
      error.response?.data?.error ??
      error.message ??
      "An unexpected error occurred";
    return Promise.reject(new Error(message));
  },
);

// ---------------------------------------------------------------------------
// Auth
// ---------------------------------------------------------------------------

export async function login(
  email: string,
  password: string,
): Promise<TokenResponse> {
  const { data } = await api.post<TokenResponse>("/api/auth/login", {
    email,
    password,
  });
  return data;
}

export async function register(
  email: string,
  password: string,
): Promise<RegisterResponse> {
  const { data } = await api.post<RegisterResponse>("/api/auth/register", {
    email,
    password,
  });
  return data;
}

// ---------------------------------------------------------------------------
// Skills
// ---------------------------------------------------------------------------

export async function getSkills(): Promise<Skill[]> {
  const { data } = await api.get<ApiResponse<Skill[]>>("/api/skills");
  return data.data;
}

export async function createSkill(payload: SkillCreate): Promise<Skill> {
  const { data } = await api.post<ApiResponse<Skill>>("/api/skills", payload);
  return data.data;
}

export async function updateSkill(
  id: string,
  payload: SkillUpdate,
): Promise<Skill> {
  const { data } = await api.put<ApiResponse<Skill>>(
    `/api/skills/${id}`,
    payload,
  );
  return data.data;
}

export async function deleteSkill(id: string): Promise<void> {
  await api.delete(`/api/skills/${id}`);
}

// ---------------------------------------------------------------------------
// Projects
// ---------------------------------------------------------------------------

export async function getProjects(): Promise<Project[]> {
  const { data } = await api.get<ApiResponse<Project[]>>("/api/projects");
  return data.data;
}

export async function createProject(payload: ProjectCreate): Promise<Project> {
  const { data } = await api.post<ApiResponse<Project>>(
    "/api/projects",
    payload,
  );
  return data.data;
}

export async function updateProject(
  id: string,
  payload: ProjectUpdate,
): Promise<Project> {
  const { data } = await api.put<ApiResponse<Project>>(
    `/api/projects/${id}`,
    payload,
  );
  return data.data;
}

export async function deleteProject(id: string): Promise<void> {
  await api.delete(`/api/projects/${id}`);
}

// ---------------------------------------------------------------------------
// Learning Entries
// ---------------------------------------------------------------------------

export async function getEntries(params: {
  skill_id?: string;
  project_id?: string;
  page?: number;
  size?: number;
}): Promise<PaginatedResponse<LearningEntry>> {
  const { data } = await api.get<PaginatedResponse<LearningEntry>>(
    "/api/entries",
    { params },
  );
  return data;
}

export async function createEntry(
  payload: EntryCreate,
): Promise<LearningEntry> {
  const { data } = await api.post<ApiResponse<LearningEntry>>(
    "/api/entries",
    payload,
  );
  return data.data;
}

// ---------------------------------------------------------------------------
// Search
// ---------------------------------------------------------------------------

export async function search(params: {
  q?: string;
  category?: string;
}): Promise<SearchResponse> {
  const { data } = await api.get<ApiResponse<SearchResponse>>("/api/search", {
    params,
  });
  return data.data;
}

// ---------------------------------------------------------------------------
// Profile
// ---------------------------------------------------------------------------

export async function getProfile(): Promise<UserProfile> {
  const { data } = await api.get<ApiResponse<UserProfile>>("/api/profile");
  return data.data;
}

/**
 * Fetch the public profile without requiring authentication.
 *
 * Used in Portfolio Mode to display the owner's name, bio, contact
 * info, and profile picture to unauthenticated visitors.
 */
export async function getPublicProfile(): Promise<PublicProfile> {
  const { data } = await api.get<ApiResponse<PublicProfile>>("/api/profile");
  return data.data;
}

export async function updateProfile(
  payload: ProfileUpdate,
): Promise<UserProfile> {
  const { data } = await api.put<ApiResponse<UserProfile>>(
    "/api/profile",
    payload,
  );
  return data.data;
}

export async function uploadPicture(file: Blob): Promise<UserProfile> {
  const formData = new FormData();
  formData.append("file", file);
  const { data } = await api.post<ApiResponse<UserProfile>>(
    "/api/profile/picture",
    formData,
    { headers: { "Content-Type": "multipart/form-data" } },
  );
  return data.data;
}

// ---------------------------------------------------------------------------
// Bot
// ---------------------------------------------------------------------------

export async function chatWithBot(
  query: string,
  sessionHistory: { role: string; content: string }[],
): Promise<{ response: string }> {
  const { data } = await api.post<{ response: string }>("/api/bot/chat", {
    query,
    session_history: sessionHistory,
  });
  return data;
}

export default api;
