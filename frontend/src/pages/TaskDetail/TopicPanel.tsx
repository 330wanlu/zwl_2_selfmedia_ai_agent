import { Alert, Button, Card, Radio, Space, Typography, Input, message } from 'antd'
import { useState } from 'react'
import { decideTopic } from '../../api/tasks'
import type { TopicPending } from '../../types/task'

type Props = {
  taskId: string
  pending: TopicPending
  disabled?: boolean
  onSubmitted: () => void
}

export default function TopicPanel({ taskId, pending, disabled, onSubmitted }: Props) {
  const [selected, setSelected] = useState<string>()
  const [feedback, setFeedback] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const submitSelect = async () => {
    if (!selected) {
      message.warning('请先选择一个选题')
      return
    }
    setSubmitting(true)
    try {
      await decideTopic(taskId, { action: 'select', topic_id: selected })
      message.success('已提交选题，正在生成文案')
      onSubmitted()
    } finally {
      setSubmitting(false)
    }
  }

  const submitRegen = async () => {
    setSubmitting(true)
    try {
      await decideTopic(taskId, {
        action: 'regenerate',
        feedback: feedback.trim() || undefined,
      })
      message.success('正在重新生成选题')
      onSubmitted()
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Card title={`选题决策（第 ${pending.batch ?? 1} 批）`} size="small">
      <Radio.Group
        value={selected}
        onChange={(e) => setSelected(e.target.value)}
        style={{ width: '100%' }}
        disabled={disabled || submitting}
      >
        <Space direction="vertical" style={{ width: '100%' }} size={12}>
          {pending.topics.map((t) => (
            <Card
              key={t.id}
              size="small"
              style={{
                borderColor: selected === t.id ? '#1677ff' : undefined,
                background: selected === t.id ? '#f0f5ff' : undefined,
              }}
            >
              <Radio value={t.id} style={{ width: '100%', whiteSpace: 'normal' }}>
                <Typography.Text strong>{t.title}</Typography.Text>
                <div style={{ marginTop: 6, color: '#595959' }}>{t.angle}</div>
                <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                  人群：{t.target_audience}
                </Typography.Text>
              </Radio>
            </Card>
          ))}
        </Space>
      </Radio.Group>

      <Space style={{ marginTop: 16 }} wrap>
        <Button type="primary" loading={submitting} disabled={disabled} onClick={() => void submitSelect()}>
          确认选题
        </Button>
      </Space>

      <Alert
        style={{ marginTop: 16 }}
        type="info"
        showIcon
        message="不满意可以换一批"
        description={
          <Space direction="vertical" style={{ width: '100%' }}>
            <Input.TextArea
              rows={2}
              placeholder="可选：说明希望换什么角度"
              value={feedback}
              onChange={(e) => setFeedback(e.target.value)}
              disabled={disabled || submitting}
            />
            <Button loading={submitting} disabled={disabled} onClick={() => void submitRegen()}>
              换一批重新生成
            </Button>
          </Space>
        }
      />
    </Card>
  )
}
