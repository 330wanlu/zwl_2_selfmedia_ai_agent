import { UnorderedListOutlined } from '@ant-design/icons'
import { Link, Outlet, useLocation } from 'react-router-dom'

export default function AppLayout() {
  const location = useLocation()
  const isTasks = location.pathname.startsWith('/tasks')

  return (
    <div className="app-shell">
      <div className="app-shell__bg" aria-hidden />
      <div className="app-shell__grid" aria-hidden />
      <div className="app-shell__scan" aria-hidden />

      <div className="app-shell__content">
        <header className="tech-header">
          <Link to="/tasks" className="tech-brand">
            <div className="tech-brand__mark">
              <span className="tech-brand__glyph" />
            </div>
            <div className="tech-brand__text">
              <span className="tech-brand__name">Beauty Agent</span>
              <span className="tech-brand__sub">美妆内容流水线</span>
            </div>
          </Link>

          <Link
            to="/tasks"
            className={`tech-nav-link${isTasks ? ' is-active' : ''}`}
          >
            <UnorderedListOutlined />
            任务列表
          </Link>

          <div className="tech-header__status">
            <span className="tech-header__dot" />
            SYSTEM ONLINE
          </div>
        </header>

        <main className="tech-main">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
