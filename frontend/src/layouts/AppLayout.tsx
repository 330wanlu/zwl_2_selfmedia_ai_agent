import { Layout, Menu, Typography } from 'antd'
import { UnorderedListOutlined } from '@ant-design/icons'
import { Link, Outlet, useLocation } from 'react-router-dom'

const { Header, Content } = Layout

export default function AppLayout() {
  const location = useLocation()
  const selected = location.pathname.startsWith('/tasks') ? ['tasks'] : ['tasks']

  return (
    <Layout style={{ minHeight: '100vh', background: '#f5f6f8' }}>
      <Header
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 24,
          background: '#14181f',
          padding: '0 24px',
        }}
      >
        <Typography.Title level={4} style={{ color: '#fff', margin: 0, whiteSpace: 'nowrap' }}>
          美妆内容 Agent
        </Typography.Title>
        <Menu
          theme="dark"
          mode="horizontal"
          selectedKeys={selected}
          style={{ flex: 1, minWidth: 0, background: 'transparent' }}
          items={[
            {
              key: 'tasks',
              icon: <UnorderedListOutlined />,
              label: <Link to="/tasks">任务列表</Link>,
            },
          ]}
        />
      </Header>
      <Content style={{ padding: '24px 32px', maxWidth: 1100, margin: '0 auto', width: '100%' }}>
        <Outlet />
      </Content>
    </Layout>
  )
}
