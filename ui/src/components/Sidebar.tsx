import { NavLink } from 'react-router-dom'
import { 
  MdDashboard, 
  MdVideocam, 
  MdEvent, 
  MdSettings, 
  MdSearch 
} from 'react-icons/md'
import { useWebSocket } from '../hooks/useWebSocket'

interface SidebarProps {
  systemStatus?: 'ok' | 'degraded' | 'down'
}

export function Sidebar({ systemStatus = 'ok' }: SidebarProps) {
  // WebSocket disabled temporarily (causing reconnect loop)
  const isConnected = false
  // const { isConnected } = useWebSocket('/api/ws/events', {})
  
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
      <div className="p-6 border-b border-border">
        <div className="flex items-center gap-3 mb-3">
          <img src="/logo.svg" alt="Logo" className="w-10 h-10" />
          <div className="flex-1">
            <h1 className="text-lg font-bold text-text">Motion Detector</h1>
            <p className="text-xs text-muted">v2.0.0</p>
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
      <div className="p-4 border-t border-border space-y-3">
        {/* WebSocket Status */}
        <div className="flex items-center gap-2 px-3 py-2 bg-surface2 border border-border rounded-lg">
          <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-success' : 'bg-error'} relative`}>
            {isConnected && (
              <div className="absolute inset-0 rounded-full bg-success animate-ping opacity-75" />
            )}
          </div>
          <span className="text-xs text-muted">
            {isConnected ? 'Canlı Bağlantı' : 'Bağlantı Kesildi'}
          </span>
        </div>
        
        {/* Language Toggle */}
        <button
          onClick={() => {
            const currentLang = localStorage.getItem('language') || 'tr';
            const newLang = currentLang === 'tr' ? 'en' : 'tr';
            localStorage.setItem('language', newLang);
            window.location.reload();
          }}
          className="w-full flex items-center justify-center gap-2 px-3 py-2 bg-surface2 border border-border rounded-lg hover:bg-accent hover:text-white transition-colors text-text text-sm font-medium"
          title="Dil değiştir / Change language"
        >
          🌐 {(localStorage.getItem('language') || 'tr') === 'tr' ? 'TR' : 'EN'}
        </button>
        
        <p className="text-xs text-muted text-center">
          Akıllı Hareket Algılama
        </p>
      </div>
    </aside>
  )
}
