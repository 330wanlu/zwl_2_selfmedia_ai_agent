import { api, assetUrl } from './client'
import type {
  PlatformContents,
  TaskBrief,
  TaskDetail,
} from '../types/task'

export async function listTasks(): Promise<TaskBrief[]> {
  const { data } = await api.get<TaskBrief[]>('/api/v1/tasks')
  return data
}

export async function createTask(direction: string): Promise<TaskBrief> {
  const { data } = await api.post<TaskBrief>('/api/v1/tasks', { direction })
  return data
}

export async function cancelTask(taskId: string): Promise<TaskBrief> {
  const { data } = await api.post<TaskBrief>(`/api/v1/tasks/${taskId}/cancel`)
  return data
}

export async function getTask(taskId: string): Promise<TaskDetail> {
  const { data } = await api.get<TaskDetail>(`/api/v1/tasks/${taskId}`)
  return data
}

export async function decideTopic(
  taskId: string,
  body: { action: 'select' | 'regenerate'; topic_id?: string; feedback?: string },
): Promise<void> {
  await api.post(`/api/v1/tasks/${taskId}/decisions/topic`, body)
}

export async function decideContent(
  taskId: string,
  body: { approved: boolean; feedback?: string },
): Promise<void> {
  await api.post(`/api/v1/tasks/${taskId}/decisions/content`, body)
}

export async function decideImages(
  taskId: string,
  body: {
    approved: boolean
    redraw?: Array<{ sequence: number; hint?: string }>
  },
): Promise<void> {
  await api.post(`/api/v1/tasks/${taskId}/decisions/images`, body)
}

export async function getPlatformContents(taskId: string): Promise<PlatformContents> {
  const { data } = await api.get<PlatformContents>(
    `/api/v1/tasks/${taskId}/platform-contents`,
  )
  return data
}

export async function markPublished(taskId: string): Promise<PlatformContents & { task_id: string }> {
  const { data } = await api.post(`/api/v1/tasks/${taskId}/publish/mark`)
  return data
}

export function exportJsonUrl(taskId: string): string {
  return assetUrl(`/api/v1/tasks/${taskId}/export`)
}

export function exportImagesZipUrl(taskId: string): string {
  return assetUrl(`/api/v1/tasks/${taskId}/export/images.zip`)
}

export async function downloadImagesZip(taskId: string): Promise<void> {
  const { data } = await api.get(`/api/v1/tasks/${taskId}/export/images.zip`, {
    responseType: 'blob',
  })
  const url = URL.createObjectURL(data)
  const a = document.createElement('a')
  a.href = url
  a.download = `task_${taskId}_images.zip`
  a.click()
  URL.revokeObjectURL(url)
}
