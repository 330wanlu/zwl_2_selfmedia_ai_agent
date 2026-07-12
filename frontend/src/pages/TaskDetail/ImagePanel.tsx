import { Button, Card, Checkbox, Col, Image, Input, Row, Space, Typography, message } from 'antd'
import { useMemo, useState } from 'react'
import { assetUrl } from '../../api/client'
import { decideImages } from '../../api/tasks'
import type { ImagePending } from '../../types/task'

type Props = {
  taskId: string
  pending: ImagePending
  disabled?: boolean
  onSubmitted: () => void
}

export default function ImagePanel({ taskId, pending, disabled, onSubmitted }: Props) {
  const [selected, setSelected] = useState<number[]>([])
  const [hints, setHints] = useState<Record<number, string>>({})
  const [submitting, setSubmitting] = useState(false)

  const images = useMemo(
    () => [...pending.images].sort((a, b) => a.sequence - b.sequence),
    [pending.images],
  )

  const toggle = (seq: number, checked: boolean) => {
    setSelected((prev) =>
      checked ? [...prev, seq] : prev.filter((s) => s !== seq),
    )
  }

  const approve = async () => {
    setSubmitting(true)
    try {
      await decideImages(taskId, { approved: true })
      message.success('图片已通过，正在生成小红书内容包')
      onSubmitted()
    } finally {
      setSubmitting(false)
    }
  }

  const redraw = async () => {
    if (selected.length === 0) {
      message.warning('请先勾选需要重绘的图片')
      return
    }
    setSubmitting(true)
    try {
      await decideImages(taskId, {
        approved: false,
        redraw: selected.map((sequence) => ({
          sequence,
          hint: hints[sequence]?.trim() || undefined,
        })),
      })
      message.success('已提交重绘，请稍候')
      setSelected([])
      onSubmitted()
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Card title="图片审核" size="small">
      <Row gutter={[16, 16]}>
        {images.map((img) => (
          <Col xs={24} sm={12} md={8} key={img.sequence}>
            <Card
              size="small"
              className={`image-tile${selected.includes(img.sequence) ? ' is-selected' : ''}`}
              cover={
                <Image
                  src={assetUrl(img.url)}
                  alt={`图 ${img.sequence}`}
                  style={{ objectFit: 'cover', height: 180 }}
                />
              }
            >
              <Checkbox
                checked={selected.includes(img.sequence)}
                disabled={disabled || submitting}
                onChange={(e) => toggle(img.sequence, e.target.checked)}
              >
                第 {img.sequence} 张
                {(img.retry_count ?? 0) > 0 ? `（已重绘 ${img.retry_count} 次）` : ''}
              </Checkbox>
              {selected.includes(img.sequence) && (
                <Input
                  size="small"
                  style={{ marginTop: 8 }}
                  placeholder="可选：重绘要求，如背景换成粉色"
                  value={hints[img.sequence] || ''}
                  onChange={(e) =>
                    setHints((h) => ({ ...h, [img.sequence]: e.target.value }))
                  }
                  disabled={disabled || submitting}
                />
              )}
            </Card>
          </Col>
        ))}
      </Row>

      <Typography.Paragraph type="secondary" style={{ marginTop: 12 }}>
        勾选后点「重绘选中」只重画勾选的图；其余保留。全部满意再点「全部通过」。
      </Typography.Paragraph>

      <Space wrap>
        <Button type="primary" loading={submitting} disabled={disabled} onClick={() => void approve()}>
          全部通过
        </Button>
        <Button loading={submitting} disabled={disabled} onClick={() => void redraw()}>
          重绘选中
        </Button>
      </Space>
    </Card>
  )
}
