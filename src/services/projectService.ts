import { apiClient } from './api'
import type {
  Project,
  ProjectCreatePayload,
  ProjectDeleteResponse,
  ProjectDetailResponse,
  ProjectListResponse,
  ProjectStatus,
  ProjectUpdatePayload
} from '../types/project'

export interface ProjectListParams {
  order?: 'asc' | 'desc'
  sort?: string
  status?: ProjectStatus
}

function encodeProjectPath(projectId: string): string {
  return `/projects/${encodeURIComponent(projectId)}`
}

export const projectService = {
  list(params?: ProjectListParams): Promise<ProjectListResponse> {
    return apiClient.get<ProjectListResponse>('/projects', {
      params
    })
  },

  create(payload: ProjectCreatePayload): Promise<Project> {
    return apiClient.post<Project>('/projects', {
      body: payload
    })
  },

  getById(projectId: string): Promise<ProjectDetailResponse> {
    return apiClient.get<ProjectDetailResponse>(encodeProjectPath(projectId))
  },

  update(projectId: string, payload: ProjectUpdatePayload): Promise<Project> {
    return apiClient.patch<Project>(encodeProjectPath(projectId), {
      body: payload
    })
  },

  remove(projectId: string): Promise<ProjectDeleteResponse> {
    return apiClient.delete<ProjectDeleteResponse>(encodeProjectPath(projectId))
  }
}
