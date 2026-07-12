/** 后端 current_stage → 运营可读标签 / 颜色 / 进度步 */

export type StageMeta = {
  label: string
  color: string
  /** Steps 当前步：0 选题 1 文案 2 出图 3 内容包；-1 失败 */
  step: number
  waiting: boolean
}

const STAGE_MAP: Record<string, StageMeta> = {
  topic_generating: { label: '生成选题中', color: 'processing', step: 0, waiting: false },
  waiting_topic_selection: { label: '待选题', color: 'orange', step: 0, waiting: true },
  content_generating: { label: '生成文案中', color: 'processing', step: 1, waiting: false },
  waiting_content_review: { label: '待审文案', color: 'orange', step: 1, waiting: true },
  storyboard_planning: { label: '规划分镜中', color: 'processing', step: 2, waiting: false },
  image_generating: { label: '生成图片中', color: 'processing', step: 2, waiting: false },
  waiting_image_review: { label: '待审图片', color: 'orange', step: 2, waiting: true },
  platform_adapting: { label: '生成内容包中', color: 'processing', step: 3, waiting: false },
  completed: { label: '已完成', color: 'success', step: 3, waiting: false },
  failed: { label: '失败', color: 'error', step: -1, waiting: false },
}

export function getStageMeta(stage: string, status?: string): StageMeta {
  if (status === 'cancelled' || stage === 'cancelled') {
    return { label: '已取消', color: 'default', step: -1, waiting: false }
  }
  if (status === 'failed' || stage === 'failed') {
    return STAGE_MAP.failed
  }
  return (
    STAGE_MAP[stage] || {
      label: stage || '未知',
      color: 'default',
      step: 0,
      waiting: false,
    }
  )
}

export const PIPELINE_STEPS = ['选题', '文案审核', '图片审核', '内容包'] as const
