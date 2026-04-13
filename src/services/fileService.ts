import { apiClient } from './api'
import type { UploadedFile, UploadedFileDeleteResponse, UploadedFileListResponse } from '@/types/file'

function encodeProjectFilesPath(projectId: string): string {
  return `/projects/${encodeURIComponent(projectId)}/files`
}

function encodeProjectFilePath(projectId: string, fileId: string): string {
  return `${encodeProjectFilesPath(projectId)}/${encodeURIComponent(fileId)}`
}

export const fileService = {
  list(projectId: string): Promise<UploadedFileListResponse> {
    return apiClient.get<UploadedFileListResponse>(encodeProjectFilesPath(projectId))
  },

  remove(projectId: string, fileId: string): Promise<UploadedFileDeleteResponse> {
    return apiClient.delete<UploadedFileDeleteResponse>(encodeProjectFilePath(projectId, fileId))
  },

  upload(projectId: string, file: File): Promise<UploadedFile> {
    const formData = new FormData()
    formData.append('file', file)

    return apiClient.post<UploadedFile>(encodeProjectFilesPath(projectId), {
      body: formData
    })
  }
}
