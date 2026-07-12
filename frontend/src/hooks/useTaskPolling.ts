import { useCallback, useEffect, useRef, useState } from 'react'
import { getTask } from '../api/tasks'
import type { TaskDetail } from '../types/task'

const POLL_MS = 3000

export function useTaskPolling(taskId: string | undefined) {
  const [task, setTask] = useState<TaskDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const timer = useRef<number | null>(null)

  const refresh = useCallback(async () => {
    if (!taskId) return
    try {
      const data = await getTask(taskId)
      setTask(data)
      setError(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : '加载失败')
    } finally {
      setLoading(false)
    }
  }, [taskId])

  useEffect(() => {
    setLoading(true)
    void refresh()
    timer.current = window.setInterval(() => {
      void refresh()
    }, POLL_MS)
    return () => {
      if (timer.current) window.clearInterval(timer.current)
    }
  }, [refresh])

  return { task, loading, error, refresh }
}
