export const PROJECT_EXPORT_FORMAT_VALUES = ['pdf'] as const

export type ProjectExportFormat = (typeof PROJECT_EXPORT_FORMAT_VALUES)[number]

export const PROJECT_EXPORT_STATUS_VALUES = ['pending', 'running', 'completed', 'failed'] as const

export type ProjectExportStatus = (typeof PROJECT_EXPORT_STATUS_VALUES)[number]

export interface ProjectExportTask {
  artifact_name: string | null
  artifact_size_bytes: number | null
  completed_pages: number
  created_at: string
  current_page_number: number | null
  current_page_title: string | null
  download_url: string | null
  error: string | null
  format: ProjectExportFormat
  id: string
  progress: number
  project_id: string
  stage: string
  status: ProjectExportStatus
  total_pages: number
  updated_at: string
}
