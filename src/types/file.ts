export const FILE_PARSE_STATUS_VALUES = ['pending', 'parsing', 'parsed', 'failed'] as const

export type FileParseStatus = (typeof FILE_PARSE_STATUS_VALUES)[number]

export const UPLOAD_FILE_EXTENSIONS = [
  'xlsx',
  'csv',
  'docx',
  'pdf',
  'pptx',
  'png',
  'jpg',
  'jpeg',
  'md',
  'json',
  'txt'
] as const

export const MAX_UPLOAD_FILE_SIZE_BYTES = 50 * 1024 * 1024
export const UPLOAD_FILE_ACCEPT_ATTRIBUTE = UPLOAD_FILE_EXTENSIONS.map((extension) => `.${extension}`).join(',')

export interface UploadedFile {
  created_at: string
  file_path: string
  file_size: number | null
  file_type: string
  id: string
  original_name: string
  parse_status: FileParseStatus
  parsed_content: Record<string, unknown> | null
  project_id: string
}

export interface UploadedFileListResponse {
  files: UploadedFile[]
}

export interface UploadedFileDeleteResponse {
  success: boolean
}
