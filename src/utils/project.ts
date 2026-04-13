import type { Project, ProjectStatus } from '@/types/project'

export interface ProjectStatusMeta {
  label: string
  tone: 'accent' | 'muted' | 'primary' | 'sage' | 'success' | 'warning'
}

export const PROJECT_STATUS_META: Record<ProjectStatus, ProjectStatusMeta> = {
  archived: { label: '已归档', tone: 'muted' },
  completed: { label: '已完成', tone: 'success' },
  draft: { label: '草稿', tone: 'accent' },
  editing: { label: '创作中', tone: 'primary' },
  generating: { label: '生成中', tone: 'warning' },
  planning: { label: '规划中', tone: 'sage' }
}

export function formatProjectPageCount(totalPages: number): string {
  const normalizedTotal = Number.isFinite(totalPages) ? Math.max(0, totalPages) : 0
  return `${normalizedTotal} 页`
}

export function formatProjectUpdatedAt(updatedAt: string): string {
  const date = new Date(updatedAt)

  if (Number.isNaN(date.getTime())) {
    return '时间未知'
  }

  const now = new Date()
  const diff = now.getTime() - date.getTime()
  const minute = 60 * 1000
  const hour = 60 * minute
  const day = 24 * hour

  if (diff >= 0 && diff < hour) {
    return `${Math.max(1, Math.round(diff / minute))} 分钟前`
  }

  if (diff >= hour && diff < day) {
    return `${Math.max(1, Math.round(diff / hour))} 小时前`
  }

  const yesterday = new Date(now)
  yesterday.setDate(now.getDate() - 1)

  if (
    date.getFullYear() === yesterday.getFullYear() &&
    date.getMonth() === yesterday.getMonth() &&
    date.getDate() === yesterday.getDate()
  ) {
    return '昨天'
  }

  if (date.getFullYear() === now.getFullYear()) {
    return new Intl.DateTimeFormat('zh-CN', {
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      month: '2-digit'
    }).format(date)
  }

  return new Intl.DateTimeFormat('zh-CN', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric'
  }).format(date)
}

export function getProjectInitial(name: string): string {
  const normalizedName = name.trim()

  if (!normalizedName) {
    return 'P'
  }

  return Array.from(normalizedName)[0]?.toUpperCase() ?? 'P'
}

export function matchesProjectStatusFilter(project: Project, status: ProjectStatus | 'all'): boolean {
  return status === 'all' || project.status === status
}

export function sortProjectsByUpdatedAt(projects: Project[]): Project[] {
  return [...projects].sort((left, right) => {
    const leftTimestamp = Date.parse(left.updated_at)
    const rightTimestamp = Date.parse(right.updated_at)

    if (!Number.isNaN(leftTimestamp) && !Number.isNaN(rightTimestamp) && leftTimestamp !== rightTimestamp) {
      return rightTimestamp - leftTimestamp
    }

    return right.id.localeCompare(left.id)
  })
}
