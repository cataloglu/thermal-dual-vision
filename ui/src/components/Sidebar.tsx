import { NavLink } from 'react-router-dom'
import { 
  MdDashboard, 
  MdVideocam, 
  MdEvent, 
  MdSettings, 
  MdSearch 
} from 'react-icons/md'

interface SidebarProps {
  systemStatus?: 'ok' | 'degraded' | 'down'
}

export function Sidebar({ systemStatus = 'ok' }: SidebarProps) {
  const menuItems = [
    { path: '/', icon: MdDashboard, label: 'Kontrol Paneli' },
    { path: '/live', icon: MdVideocam, label: 'Canlı Görüntü' },
    { path: '/events', icon: MdEvent, label: 'Olaylar' },
    { path: '/settings', icon: MdSettings, label: 'Ayarlar' },
    { path: '/diagnostics', icon: MdSearch, label: 'Sistem Tanılama' },
  ]

  const statusColors = {
    ok: 'bg-green-500',
    degraded: 'bg-yellow-500',
    down: 'bg-red-500',
  }

  return (
    <aside className="w-60 bg-surface1 border-r border-border flex flex-col h-screen">
      {/* Logo & Title */}
      <div className="p-6 border-b border-border flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-text">Motion Detector</h1>
          <p className="text-xs text-muted mt-1">v2.0.0</p>
        </div>
        {/* System Status Dot */}
        <div className="relative">
          <div className={`w-3 h-3 rounded-full ${statusColors[systemStatus]}`}>
            {systemStatus === 'ok' && (
              <div className={`absolute inset-0 rounded-full ${statusColors[systemStatus]} animate-ping opacity-75`} />
            )}
          </div>
        </div>
      </div>

      {/* Navigation Menu */}
      <nav className="flex-1 p-4 space-y-1">
        {menuItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            end={item.path === '/'}
            className={({ isActive }) =>
              `flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${
                isActive
                  ? 'bg-accent text-white'
                  : 'text-muted hover:bg-surface2 hover:text-text'
              }`
            }
          >
            <item.icon className="text-xl" />
            <span className="font-medium">{item.label}</span>
          </NavLink>
        ))}
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-border">
        <p className="text-xs text-muted text-center">
          Akıllı Hareket Algılama
        </p>
      </div>
    </aside>
  )
}
