import { useEffect, useMemo, useState } from 'react'
import {
  Alert,
  Button,
  Card,
  Image,
  Space,
  Tag,
  Typography,
  message,
} from 'antd'
import {
  ArrowLeftOutlined,
  CheckCircleOutlined,
  CopyOutlined,
  DownloadOutlined,
} from '@ant-design/icons'
import { Link, useParams } from 'react-router-dom'
import { assetUrl } from '../../api/client'
import {
  downloadImagesZip,
  exportJsonUrl,
  getPlatformContents,
  markPublished,
} from '../../api/tasks'
import type { PlatformContents } from '../../types/task'

function imageSrc(
  item: string | { sequence?: number; file_path?: string; url?: string },
): string {
  if (typeof item === 'string') {
    if (item.startsWith('/')) return assetUrl(item)
    if (item.startsWith('http')) return item
    return assetUrl(`/images/${item}`)
  }
  if (item.url) return assetUrl(item.url)
  if (item.file_path) return assetUrl(`/images/${item.file_path}`)
  return ''
}

export default function ContentPackagePage() {
  const { taskId } = useParams<{ taskId: string }>()
  const [data, setData] = useState<PlatformContents | null>(null)
  const [loading, setLoading] = useState(true)
  const [marking, setMarking] = useState(false)
  const [downloading, setDownloading] = useState(false)

  const load = async () => {
    if (!taskId) return
    setLoading(true)
    try {
      setData(await getPlatformContents(taskId))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void load()
  }, [taskId])

  const pkg = data?.content_package
  const copyText = useMemo(() => {
    if (!pkg) return ''
    const tags = (pkg.tags || []).map((t) => `#${t}`).join(' ')
    return `${pkg.title}\n\n${pkg.body}\n\n${tags}`
  }, [pkg])

  const copyAll = async () => {
    try {
      await navigator.clipboard.writeText(copyText)
      message.success('已复制标题+正文+话题标签')
    } catch {
      message.error('复制失败，请手动选择文本')
    }
  }

  const onDownloadZip = async () => {
    if (!taskId) return
    setDownloading(true)
    try {
      await downloadImagesZip(taskId)
      message.success('图片压缩包已开始下载')
    } finally {
      setDownloading(false)
    }
  }

  const onMark = async () => {
    if (!taskId) return
    setMarking(true)
    try {
      const res = await markPublished(taskId)
      setData({
        platform: res.platform,
        status: res.status,
        published_at: res.published_at,
        content_package: res.content_package || pkg!,
      })
      message.success('已标记为已发布')
    } finally {
      setMarking(false)
    }
  }

  if (loading) {
    return (
      <div className="loading-screen">
        <div className="loading-screen__orb" />
        <div>加载内容包…</div>
      </div>
    )
  }

  if (!data || !pkg) {
    return (
      <Space direction="vertical">
        <Link to={taskId ? `/tasks/${taskId}` : '/tasks'}>
          <Button icon={<ArrowLeftOutlined />}>返回</Button>
        </Link>
        <Alert type="warning" showIcon message="内容包尚未生成，请先完成任务流程" />
      </Space>
    )
  }

  const published = data.status === 'published'

  return (
    <div className="stack">
      <div className="row-between">
        <div className="row">
          <Link to={`/tasks/${taskId}`}>
            <Button icon={<ArrowLeftOutlined />}>返回详情</Button>
          </Link>
          <div>
            <div className="page-hero__eyebrow" style={{ marginBottom: 4 }}>
              Delivery Pack
            </div>
            <h1 className="page-hero__title" style={{ fontSize: 26, margin: 0 }}>
              小红书内容包
            </h1>
          </div>
          <Tag color={published ? 'success' : 'default'}>
            {published ? '已发布' : '待发布'}
          </Tag>
        </div>
        <Space wrap>
          <Button icon={<CopyOutlined />} type="primary" onClick={() => void copyAll()}>
            一键复制文字
          </Button>
          <Button
            icon={<DownloadOutlined />}
            loading={downloading}
            onClick={() => void onDownloadZip()}
          >
            批量下载图片
          </Button>
          <Button href={exportJsonUrl(taskId!)} target="_blank">
            导出 JSON
          </Button>
          <Button
            icon={<CheckCircleOutlined />}
            loading={marking}
            disabled={published}
            onClick={() => void onMark()}
          >
            {published ? '已标记发布' : '标记已发布'}
          </Button>
        </Space>
      </div>

      <Card title="标题" size="small">
        <h2 className="package-title">{pkg.title}</h2>
      </Card>

      <Card title="正文" size="small">
        <Typography.Paragraph className="content-preview" style={{ marginBottom: 0 }}>
          {pkg.body}
        </Typography.Paragraph>
      </Card>

      <Card title="话题标签" size="small">
        <Space wrap>
          {(pkg.tags || []).map((t) => (
            <Tag key={t} className="tag-chip">
              #{t}
            </Tag>
          ))}
        </Space>
      </Card>

      <Card title="图片组" size="small">
        <Image.PreviewGroup>
          <Space wrap size={12}>
            {(pkg.images || []).map((item, idx) => {
              const src = imageSrc(item)
              return (
                <Image
                  key={idx}
                  src={src}
                  width={160}
                  height={160}
                  style={{
                    objectFit: 'cover',
                    borderRadius: 10,
                    border: '1px solid rgba(0, 229, 200, 0.2)',
                  }}
                />
              )
            })}
          </Space>
        </Image.PreviewGroup>
      </Card>

      <Alert
        type="info"
        showIcon
        message="发布提示"
        description="复制文字后打开小红书创作者中心粘贴；图片用「批量下载」解压上传。发完后点「标记已发布」。"
      />
    </div>
  )
}
