export interface TaskBrief {
  id: string
  direction: string
  status: string
  current_stage: string
  created_at: string
  updated_at: string
}

export interface TopicItem {
  id: string
  title: string
  angle: string
  target_audience: string
}

export interface ImageItem {
  sequence: number
  file_path?: string
  url: string
  retry_count?: number
  summary_text?: string
  status?: string
}

export interface TopicPending {
  type: 'topic_selection'
  topics: TopicItem[]
  batch?: number
}

export interface ContentPending {
  type: 'content_review'
  content: string
  version: number
  feedback_history: string[]
}

export interface ImagePending {
  type: 'image_review'
  images: ImageItem[]
}

export type PendingDecision = TopicPending | ContentPending | ImagePending | Record<string, unknown>

export interface TaskDetail extends TaskBrief {
  running: boolean
  pending_decision: PendingDecision | null
}

export interface ContentPackage {
  title: string
  body: string
  tags: string[]
  images: Array<string | { sequence?: number; file_path?: string; url?: string }>
}

export interface PlatformContents {
  platform: string
  status: string
  published_at: string | null
  content_package: ContentPackage
}
