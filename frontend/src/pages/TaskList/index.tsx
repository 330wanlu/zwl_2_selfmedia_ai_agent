import { useEffect, useState } from 'react'
import {
  Button,
  Card,
  Form,
  Input,
  Space,
  Table,
  Tag,
  message,
} from 'antd'
import { PlusOutlined, ReloadOutlined, ThunderboltOutlined } from '@ant-design/icons'
import { Link, useNavigate } from 'react-router-dom'
import dayjs from 'dayjs'
import { createTask, listTasks } from '../../api/tasks'
import { useUiStore } from '../../stores/ui'
import type { TaskBrief } from '../../types/task'
import { getStageMeta } from '../../utils/stage'

export default function TaskListPage() {
  const navigate = useNavigate()
  const listVersion = useUiStore((s) => s.listVersion)
  const bumpList = useUiStore((s) => s.bumpList)
  const [tasks, setTasks] = useState<TaskBrief[]>([])
  const [loading, setLoading] = useState(false)
  const [creating, setCreating] = useState(false)
  const [form] = Form.useForm()

  const load = async () => {
    setLoading(true)
    try {
      setTasks(await listTasks())
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void load()
    const t = window.setInterval(() => void load(), 5000)
    return () => window.clearInterval(t)
  }, [listVersion])

  const onCreate = async (values: { direction: string }) => {
    setCreating(true)
    try {
      const task = await createTask(values.direction.trim())
      message.success('任务已创建，正在生成选题')
      form.resetFields()
      bumpList()
      navigate(`/tasks/${task.id}`)
    } finally {
      setCreating(false)
    }
  }

  return (
    <div className="stack">
      <div className="page-hero">
        <div className="page-hero__eyebrow">Content Pipeline</div>
        <h1 className="page-hero__title">任务列表</h1>
        <p className="page-hero__desc">
          输入内容方向，AI 自动走完选题 → 文案 → 出图 → 小红书内容包，人工在关键节点拍板。
        </p>
      </div>

      <Card
        title={
          <span>
            <ThunderboltOutlined style={{ marginRight: 8, color: '#00e5c8' }} />
            创建任务
          </span>
        }
        size="small"
      >
        <Form form={form} layout="vertical" onFinish={onCreate}>
          <Form.Item
            name="direction"
            label="内容方向"
            rules={[{ required: true, message: '请输入内容方向' }, { max: 500 }]}
          >
            <Input.TextArea
              rows={2}
              placeholder="例如：敏感肌夏季防晒推荐、秋冬干皮粉底液"
              maxLength={500}
              showCount
            />
          </Form.Item>
          <Button type="primary" htmlType="submit" icon={<PlusOutlined />} loading={creating}>
            创建并开始
          </Button>
        </Form>
      </Card>

      <Card
        title="全部任务"
        size="small"
        extra={
          <Button icon={<ReloadOutlined />} onClick={() => void load()} loading={loading}>
            刷新
          </Button>
        }
      >
        <Table
          rowKey="id"
          loading={loading}
          dataSource={tasks}
          pagination={{ pageSize: 10 }}
          columns={[
            {
              title: '方向',
              dataIndex: 'direction',
              ellipsis: true,
              render: (text: string, row) => (
                <Link to={`/tasks/${row.id}`}>{text}</Link>
              ),
            },
            {
              title: '状态',
              dataIndex: 'current_stage',
              width: 140,
              render: (stage: string, row) => {
                const meta = getStageMeta(stage, row.status)
                return <Tag color={meta.color}>{meta.label}</Tag>
              },
            },
            {
              title: '更新时间',
              dataIndex: 'updated_at',
              width: 180,
              render: (v: string) => dayjs(v).format('YYYY-MM-DD HH:mm:ss'),
            },
            {
              title: '操作',
              width: 160,
              render: (_, row) => (
                <Space>
                  <Link to={`/tasks/${row.id}`}>详情</Link>
                  {row.status === 'completed' && (
                    <Link to={`/tasks/${row.id}/package`}>内容包</Link>
                  )}
                </Space>
              ),
            },
          ]}
        />
      </Card>
    </div>
  )
}
