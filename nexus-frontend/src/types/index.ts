/**
 * TypeScript interfaces matching backend Pydantic schemas.
 *
 * These types mirror the backend response/request models to ensure
 * type safety across the API boundary.
 */

// ---------------------------------------------------------------------------
// Enums
// ---------------------------------------------------------------------------

export enum ProficiencyLevel {
  Beginner = "beginner",
  Intermediate = "intermediate",
  Advanced = "advanced",
  Expert = "expert",
}

export enum ProjectStatus {
  Planning = "planning",
  InProgress = "in_progress",
  Completed = "completed",
  Archived = "archived",
}

// ---------------------------------------------------------------------------
// Skill
// ---------------------------------------------------------------------------

export interface Skill {
  id: string;
  name: string;
  category: string;
  proficiency_level: string;
  created_at: string;
  updated_at: string;
}

export interface SkillCreate {
  name: string;
  category: string;
  proficiency_level?: ProficiencyLevel;
}

export interface SkillUpdate {
  name?: string;
  category?: string;
  proficiency_level?: ProficiencyLevel;
}

// ---------------------------------------------------------------------------
// Project
// ---------------------------------------------------------------------------

export interface Project {
  id: string;
  name: string;
  description: string | null;
  status: string;
  technology_tags: string[];
  created_at: string;
  updated_at: string;
}

export interface ProjectCreate {
  name: string;
  description?: string | null;
  status?: ProjectStatus;
  technology_tags?: string[];
}

export interface ProjectUpdate {
  name?: string;
  description?: string | null;
  status?: ProjectStatus;
  technology_tags?: string[];
}

// ---------------------------------------------------------------------------
// Learning Entry
// ---------------------------------------------------------------------------

export interface LearningEntry {
  id: string;
  skill_id: string | null;
  project_id: string | null;
  description: string;
  metadata: Record<string, unknown> | null;
  timestamp: string;
}

export interface EntryCreate {
  skill_id?: string | null;
  project_id?: string | null;
  description: string;
  metadata?: Record<string, unknown> | null;
}

// ---------------------------------------------------------------------------
// User Profile
// ---------------------------------------------------------------------------

export interface UserProfile {
  id: string;
  user_id: string;
  name: string | null;
  bio: string | null;
  contact_email: string | null;
  social_links: Record<string, string> | null;
  picture_url: string | null;
  updated_at: string;
}

export interface ProfileUpdate {
  name?: string | null;
  bio?: string | null;
  contact_email?: string | null;
  social_links?: Record<string, string> | null;
}

export interface PublicProfile {
  name: string | null;
  bio: string | null;
  contact_email: string | null;
  social_links: Record<string, string> | null;
  picture_url: string | null;
}

// ---------------------------------------------------------------------------
// API Response Wrappers
// ---------------------------------------------------------------------------

export interface ApiResponse<T> {
  data: T;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
  total_pages: number;
}

export interface FieldError {
  field: string;
  message: string;
}

export interface ApiError {
  error: string;
  details?: FieldError[];
}

// ---------------------------------------------------------------------------
// Search
// ---------------------------------------------------------------------------

export interface SearchResponse {
  skills: Skill[];
  projects: Project[];
}

// ---------------------------------------------------------------------------
// Auth
// ---------------------------------------------------------------------------

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface RegisterResponse {
  message: string;
  user_id: string;
}
