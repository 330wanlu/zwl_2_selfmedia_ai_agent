import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { ConfigProvider, App as AntApp, theme } from 'antd'
import zhCN from 'antd/locale/zh_CN'
import AppLayout from './layouts/AppLayout'
import TaskListPage from './pages/TaskList'
import TaskDetailPage from './pages/TaskDetail'
import ContentPackagePage from './pages/ContentPackage'

export default function App() {
  return (
    <ConfigProvider
      locale={zhCN}
      theme={{
        algorithm: theme.darkAlgorithm,
        token: {
          colorPrimary: '#00e5c8',
          colorInfo: '#00e5c8',
          colorSuccess: '#3dd68c',
          colorWarning: '#ffb020',
          colorError: '#ff5c7a',
          colorBgBase: '#05080f',
          colorBgContainer: '#0c1424',
          colorBgElevated: '#121e34',
          colorBorder: 'rgba(0, 229, 200, 0.18)',
          colorText: '#e8eef8',
          colorTextSecondary: '#8b9bb4',
          borderRadius: 12,
          fontFamily:
            '"Sora", "Noto Sans SC", "PingFang SC", "Microsoft YaHei", system-ui, sans-serif',
        },
        components: {
          Card: {
            headerBg: 'transparent',
          },
          Table: {
            headerBg: 'rgba(0, 229, 200, 0.06)',
            rowHoverBg: 'rgba(0, 229, 200, 0.05)',
          },
          Steps: {
            colorPrimary: '#00e5c8',
          },
        },
      }}
      button={{ autoInsertSpace: false }}
    >
      <AntApp>
        <BrowserRouter>
          <Routes>
            <Route element={<AppLayout />}>
              <Route path="/" element={<Navigate to="/tasks" replace />} />
              <Route path="/tasks" element={<TaskListPage />} />
              <Route path="/tasks/:taskId" element={<TaskDetailPage />} />
              <Route path="/tasks/:taskId/package" element={<ContentPackagePage />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </AntApp>
    </ConfigProvider>
  )
}
