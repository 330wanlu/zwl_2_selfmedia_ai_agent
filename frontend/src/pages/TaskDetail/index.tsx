import { Alert, Button, Card, Space, Spin, Steps, Tag, Typography } from 'antd'
import { ArrowLeftOutlined, GiftOutlined } from '@ant-design/icons'
import { Link, useParams } from 'react-router-dom'
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

  if (loading && !task) {
    return (
      <div style={{ textAlign: 'center', padding: 80 }}>
        <Spin size="large" tip="加载任务…" />
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
    task.status === 'failed' ? 'error' : task.status === 'completed' ? 'finish' : 'process'

  return (
    <Space direction="vertical" size={20} style={{ width: '100%' }}>
      <Space style={{ width: '100%', justifyContent: 'space-between' }} wrap>
        <Space>
          <Link to="/tasks">
            <Button icon={<ArrowLeftOutlined />}>返回列表</Button>
          </Link>
          <Typography.Title level={3} style={{ margin: 0 }}>
            任务详情
          </Typography.Title>
          <Tag color={meta.color}>{meta.label}</Tag>
          {busy && <Tag color="blue">执行中…</Tag>}
        </Space>
        {task.status === 'completed' && (
          <Link to={`/tasks/${task.id}/package`}>
            <Button type="primary" icon={<GiftOutlined />}>
              查看内容包
            </Button>
          </Link>
        )}
      </Space>

      <Card size="small">
        <Typography.Text type="secondary">内容方向</Typography.Text>
        <Typography.Paragraph style={{ marginBottom: 0, fontSize: 16 }}>
          {task.direction}
        </Typography.Paragraph>
      </Card>

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
      </Card>

      {pendingType === 'topic_selection' && (
        <TopicPanel
          taskId={task.id}
          pending={pending as TopicPending}
          disabled={busy}
          onSubmitted={() => void refresh()}
        />
      )}

      {pendingType === 'content_review' && (
        <ContentPanel
          taskId={task.id}
          pending={pending as ContentPending}
          disabled={busy}
          onSubmitted={() => void refresh()}
        />
      )}

      {pendingType === 'image_review' && (
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
    </Space>
  )
}
