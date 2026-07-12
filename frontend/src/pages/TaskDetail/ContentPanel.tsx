import { Button, Card, Input, Space, Typography, message } from 'antd'
import { useState } from 'react'
import { decideContent } from '../../api/tasks'
import type { ContentPending } from '../../types/task'

type Props = {
  taskId: string
  pending: ContentPending
  disabled?: boolean
  onSubmitted: () => void
}

export default function ContentPanel({ taskId, pending, disabled, onSubmitted }: Props) {
  const [feedback, setFeedback] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const approve = async () => {
    setSubmitting(true)
    try {
      await decideContent(taskId, { approved: true })
      message.success('文案已通过，正在规划分镜与出图')
      onSubmitted()
    } finally {
      setSubmitting(false)
    }
  }

  const reject = async () => {
    if (!feedback.trim()) {
      message.warning('请填写修改意见')
      return
    }
    setSubmitting(true)
    try {
      await decideContent(taskId, { approved: false, feedback: feedback.trim() })
      message.success('已提交修改意见，正在重写文案')
      setFeedback('')
      onSubmitted()
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Card title={`文案审核（v${pending.version}）`} size="small">
      <Typography.Paragraph className="content-preview" style={{ marginBottom: 16 }}>
        {pending.content}
      </Typography.Paragraph>

      {pending.feedback_history?.length > 0 && (
        <div style={{ marginBottom: 12 }}>
          <Typography.Text type="secondary">历史修改意见：</Typography.Text>
          <ul style={{ margin: '8px 0 0', paddingLeft: 20, color: '#8b9bb4' }}>
            {pending.feedback_history.map((f, i) => (
              <li key={i}>{f}</li>
            ))}
          </ul>
        </div>
      )}

      <Input.TextArea
        rows={3}
        placeholder="不满意时填写修改意见，例如：更口语化，加 emoji，开头改成提问"
        value={feedback}
        onChange={(e) => setFeedback(e.target.value)}
        disabled={disabled || submitting}
        style={{ marginBottom: 12 }}
      />

      <Space wrap>
        <Button type="primary" loading={submitting} disabled={disabled} onClick={() => void approve()}>
          通过
        </Button>
        <Button danger loading={submitting} disabled={disabled} onClick={() => void reject()}>
          提交修改意见并重写
        </Button>
      </Space>
    </Card>
  )
}
