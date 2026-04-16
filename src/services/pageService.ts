import { apiClient } from './api'
import type { PageInsertAfterPayload, PageMutationResponse, PageReorderPayload, PageVersion, ProjectPage } from '@/types/project'

function encodeProjectPagesPath(projectId: string, pageNumber: number): string {
  return `/projects/${encodeURIComponent(projectId)}/pages/${pageNumber}`
}

export const pageService = {
  confirm(projectId: string, pageNumber: number): Promise<ProjectPage> {
    return apiClient.post<ProjectPage>(`${encodeProjectPagesPath(projectId, pageNumber)}/confirm`)
  },
  duplicate(projectId: string, pageNumber: number): Promise<ProjectPage> {
    return apiClient.post<ProjectPage>(`${encodeProjectPagesPath(projectId, pageNumber)}/duplicate`)
  },
  async insertAfter(projectId: string, pageNumber: number, payload: PageInsertAfterPayload): Promise<ProjectPage> {
    return apiClient.post<ProjectPage>(`${encodeProjectPagesPath(projectId, pageNumber)}/insert-after`, {
      body: payload,
      headers: {
        'x-ppt-studio-api-key': await resolveApiKey()
      }
    })
  },
  listVersions(projectId: string, pageNumber: number): Promise<PageVersion[]> {
    return apiClient.get<PageVersion[]>(`${encodeProjectPagesPath(projectId, pageNumber)}/versions`)
  },
  previewVersion(projectId: string, pageNumber: number, version: number): Promise<PageVersion> {
    return apiClient.post<PageVersion>(`${encodeProjectPagesPath(projectId, pageNumber)}/versions/${version}/preview`)
  },
  rollback(projectId: string, pageNumber: number, version: number): Promise<ProjectPage> {
    return apiClient.post<ProjectPage>(`${encodeProjectPagesPath(projectId, pageNumber)}/rollback`, {
      body: { version }
    })
  },
  remove(projectId: string, pageNumber: number): Promise<PageMutationResponse> {
    return apiClient.delete<PageMutationResponse>(encodeProjectPagesPath(projectId, pageNumber))
  },
  reorder(projectId: string, payload: PageReorderPayload): Promise<PageMutationResponse> {
    return apiClient.put<PageMutationResponse>(`/projects/${encodeURIComponent(projectId)}/pages/reorder`, {
      body: payload
    })
  }
}

async function resolveApiKey(): Promise<string> {
  if (typeof window === 'undefined' || !window.pptStudio) {
    throw new Error('PPT Studio Electron runtime is unavailable in the current context.')
  }

  const apiKey = (await window.pptStudio.getApiKey())?.trim() ?? ''
  if (!apiKey) {
    throw new Error('请先在设置页配置 API Key')
  }

  return apiKey
}
