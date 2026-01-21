import { NavLink, useLocation, useNavigate } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { 
  MdDashboard, 
  MdVideocam, 
  MdEvent, 
  MdSettings, 
  MdSearch,
  MdExpandMore,
  MdChevronRight,
  MdLanguage,
  MdRefresh
} from 'react-icons/md'
import { useWebSocket } from '../hooks/useWebSocket'

interface SidebarProps {
  systemStatus?: 'ok' | 'degraded' | 'down'
}

export function Sidebar({ systemStatus = 'ok' }: SidebarProps) {
  const { t, i18n } = useTranslation()
  // WebSocket for real-time status (use relative path for proxy)
  const [eventBadge, setEventBadge] = useState(0)
  const { isConnected, reconnect } = useWebSocket('/api/ws/events', {
    onEvent: () => setEventBadge((prev) => prev + 1),
  })
  const location = useLocation()
  const navigate = useNavigate()
  const [settingsExpanded, setSettingsExpanded] = useState(location.pathname.startsWith('/settings'))

  useEffect(() => {
    if (location.pathname.startsWith('/events') && eventBadge > 0) {
      setEventBadge(0)
    }
  }, [location.pathname, eventBadge])
  
  const menuItems = [
    { path: '/', icon: MdDashboard, label: t('dashboard') },
    { path: '/live', icon: MdVideocam, label: t('live') },
    { path: '/events', icon: MdEvent, label: t('events') },
    { path: '/diagnostics', icon: MdSearch, label: t('diagnostics') },
  ]

  const settingsSubItems = [
    { tab: 'cameras', label: t('cameras') },
    { tab: 'detection', label: t('detection') },
    { tab: 'thermal', label: t('thermal') },
    { tab: 'stream', label: 'Stream' },
    { tab: 'zones', label: t('zones') },
    { tab: 'live', label: t('live') },
    { tab: 'recording', label: t('recording') },
    { tab: 'events', label: t('events') },
    { tab: 'ai', label: t('ai') },
    { tab: 'telegram', label: t('telegram') },
    { tab: 'appearance', label: t('appearance') },
  ]

  const statusColors = {
    ok: 'bg-green-500',
    degraded: 'bg-yellow-500',
    down: 'bg-red-500',
  }

  return (
    <aside className="w-60 bg-surface1 border-r border-border flex flex-col h-screen min-h-0">
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
      <nav className="flex-1 min-h-0 p-4 space-y-1 overflow-y-auto">
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
            {item.path === '/events' && eventBadge > 0 && (
              <span className="ml-auto bg-error text-white text-xs px-2 py-0.5 rounded-full">
                {eventBadge}
              </span>
            )}
          </NavLink>
        ))}

        {/* Settings with submenu */}
        <div>
          <button
            onClick={() => {
              setSettingsExpanded(!settingsExpanded)
              if (!settingsExpanded) {
                navigate('/settings')
              }
            }}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${
              location.pathname.startsWith('/settings')
                ? 'bg-accent text-white'
                : 'text-muted hover:bg-surface2 hover:text-text'
            }`}
          >
            <MdSettings className="text-xl" />
            <span className="font-medium flex-1 text-left">{t('settings')}</span>
            {settingsExpanded ? <MdExpandMore className="text-xl" /> : <MdChevronRight className="text-xl" />}
          </button>

          {/* Settings Submenu */}
          {settingsExpanded && (
            <div className="ml-8 mt-1 space-y-1">
              {settingsSubItems.map((item) => (
                <button
                  key={item.tab}
                  onClick={() => navigate(`/settings?tab=${item.tab}`)}
                  className="w-full text-left px-4 py-2 text-sm rounded-lg text-muted hover:bg-surface2 hover:text-text transition-colors"
                >
                  {item.label}
                </button>
              ))}
            </div>
          )}
        </div>
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
            {isConnected ? t('liveConnection') : t('connectionLost')}
          </span>
          {!isConnected && (
            <button
              onClick={reconnect}
              className="ml-auto text-muted hover:text-text"
              title={t('reconnect')}
            >
              <MdRefresh />
            </button>
          )}
        </div>
        
        {/* Language Toggle */}
        <button
          onClick={() => {
            const currentLang = localStorage.getItem('language') || 'tr'
            const newLang = currentLang === 'tr' ? 'en' : 'tr'
            localStorage.setItem('language', newLang)
            i18n.changeLanguage(newLang)
          }}
          className="w-full flex items-center justify-center gap-2 px-3 py-2 bg-surface2 border border-border rounded-lg hover:bg-accent hover:text-white transition-colors text-text text-sm font-medium"
          title="Dil değiştir / Change language"
        >
          <MdLanguage />
          {(localStorage.getItem('language') || 'tr') === 'tr' ? 'TR' : 'EN'}
        </button>
        
        <p className="text-xs text-muted text-center">
          Smart Motion Detector
        </p>
      </div>
    </aside>
  )
}
