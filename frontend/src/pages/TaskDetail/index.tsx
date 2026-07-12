import { useState } from 'react'
import { Alert, Button, Card, Modal, Space, Steps, Tag, message } from 'antd'
import { ArrowLeftOutlined, GiftOutlined, StopOutlined } from '@ant-design/icons'
import { Link, useParams } from 'react-router-dom'
import { cancelTask } from '../../api/tasks'
import { useTaskPolling } from '../../hooks/useTaskPolling'
import { getStageMeta, PIPELINE_STEPS } from '../../utils/stage'
import type {
  ContentPending,
  ImagePending,
  TopicPending,
} from '../../types/task'
import TopicPanel from './TopicPanel'
import ContentPanel from './ContentPanel'
import ImagePanel from './ImagePanel'

export default function TaskDetailPage() {
  const { taskId } = useParams<{ taskId: string }>()
  const { task, loading, error, refresh } = useTaskPolling(taskId)
  const [cancelling, setCancelling] = useState(false)

  if (loading && !task) {
    return (
      <div className="loading-screen">
        <div className="loading-screen__orb" />
        <div>加载任务…</div>
      </div>
    )
  }

  if (error && !task) {
    return <Alert type="error" message={error} showIcon />
  }

  if (!task) {
    return <Alert type="warning" message="任务不存在" showIcon />
  }

  const meta = getStageMeta(task.current_stage, task.status)
  const pending = task.pending_decision
  const pendingType =
    pending && typeof pending === 'object' && 'type' in pending
      ? (pending as { type: string }).type
      : null

  const busy = task.running
  const stepStatus =
    task.status === 'failed'
      ? 'error'
      : task.status === 'completed'
        ? 'finish'
        : task.status === 'cancelled'
          ? 'error'
          : 'process'

  const onCancel = () => {
    Modal.confirm({
      title: '确认取消该任务？',
      content: '取消后不能继续选题/审文案/审图片，需重新创建任务。',
      okText: '确认取消',
      okButtonProps: { danger: true },
      cancelText: '返回',
      onOk: async () => {
        setCancelling(true)
        try {
          await cancelTask(task.id)
          message.success('任务已取消')
          await refresh()
        } finally {
          setCancelling(false)
        }
      },
    })
  }

  return (
    <div className="stack">
      <div className="row-between">
        <div className="row">
          <Link to="/tasks">
            <Button icon={<ArrowLeftOutlined />}>返回列表</Button>
          </Link>
          <div>
            <div className="page-hero__eyebrow" style={{ marginBottom: 4 }}>
              Task Control
            </div>
            <h1 className="page-hero__title" style={{ fontSize: 26, margin: 0 }}>
              任务详情
            </h1>
          </div>
          <Tag color={meta.color}>{meta.label}</Tag>
          {busy && (
            <Tag color="processing">
              <span className="busy-badge">
                <span className="busy-badge__ring" />
                执行中…
              </span>
            </Tag>
          )}
        </div>
        <Space>
          {task.status === 'running' && (
            <Button
              danger
              icon={<StopOutlined />}
              loading={cancelling}
              onClick={onCancel}
            >
              取消任务
            </Button>
          )}
          {task.status === 'completed' && (
            <Link to={`/tasks/${task.id}/package`}>
              <Button type="primary" icon={<GiftOutlined />}>
                查看内容包
              </Button>
            </Link>
          )}
        </Space>
      </div>

      <div className="glass-panel direction-banner">
        <div className="direction-banner__label">内容方向</div>
        <p className="direction-banner__text">{task.direction}</p>
      </div>

      <Card size="small" title="流水线进度">
        <Steps
          current={meta.step < 0 ? 0 : meta.step}
          status={stepStatus}
          items={PIPELINE_STEPS.map((title) => ({ title }))}
        />
        {busy && (
          <Alert
            style={{ marginTop: 16 }}
            type="info"
            showIcon
            message="AI 正在处理中，页面每 3 秒自动刷新状态，请稍候"
          />
        )}
        {task.status === 'failed' && (
          <Alert style={{ marginTop: 16 }} type="error" showIcon message="任务执行失败" />
        )}
        {task.status === 'cancelled' && (
          <Alert style={{ marginTop: 16 }} type="warning" showIcon message="任务已取消" />
        )}
      </Card>

      {task.status === 'running' && pendingType === 'topic_selection' && (
        <TopicPanel
          taskId={task.id}
          pending={pending as TopicPending}
          disabled={busy}
          onSubmitted={() => void refresh()}
        />
      )}

      {task.status === 'running' && pendingType === 'content_review' && (
        <ContentPanel
          taskId={task.id}
          pending={pending as ContentPending}
          disabled={busy}
          onSubmitted={() => void refresh()}
        />
      )}

      {task.status === 'running' && pendingType === 'image_review' && (
        <ImagePanel
          taskId={task.id}
          pending={pending as ImagePending}
          disabled={busy}
          onSubmitted={() => void refresh()}
        />
      )}

      {!busy && !pendingType && task.status === 'running' && (
        <Alert type="warning" showIcon message="等待工作流状态同步，请稍候自动刷新" />
      )}
    </div>
  )
}
