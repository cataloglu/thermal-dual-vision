import { ReactNode, useEffect, useState } from 'react'
import { MdMenu } from 'react-icons/md'
import { Sidebar } from './Sidebar'
import { api } from '../services/api'

interface LayoutProps {
  children: ReactNode
}

export function Layout({ children }: LayoutProps) {
  const [systemStatus, setSystemStatus] = useState<'ok' | 'degraded' | 'down'>('ok')
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

  useEffect(() => {
    // Poll health status every 10 seconds
    const checkHealth = async () => {
      try {
        const health = await api.getHealth()
        setSystemStatus(health.status as 'ok' | 'degraded' | 'down')
      } catch (error) {
        setSystemStatus('down')
      }
    }

    checkHealth()
    const interval = setInterval(checkHealth, 30000)  // Optimized: 10s → 30s

    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    if (!mobileMenuOpen) return
    const prev = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.body.style.overflow = prev
    }
  }, [mobileMenuOpen])

  const statusDotClass = systemStatus === 'ok'
    ? 'bg-green-500'
    : systemStatus === 'degraded'
      ? 'bg-yellow-500'
      : 'bg-red-500'

  return (
    <div className="safe-area-shell flex h-screen bg-background overflow-x-hidden">
      {mobileMenuOpen && (
        <button
          type="button"
          aria-label="Close menu overlay"
          className="fixed inset-0 z-40 bg-black/60 md:hidden"
          onClick={() => setMobileMenuOpen(false)}
        />
      )}
      <Sidebar
        systemStatus={systemStatus}
        mobileOpen={mobileMenuOpen}
        onCloseMobile={() => setMobileMenuOpen(false)}
      />
      <main className="flex-1 min-w-0 flex flex-col min-h-0 overflow-auto relative">
        <div className="md:hidden sticky top-0 z-30 bg-surface1/95 backdrop-blur border-b border-border px-4 py-3 flex items-center justify-between">
          <button
            type="button"
            aria-label="Open menu"
            className="inline-flex items-center justify-center w-10 h-10 rounded-lg bg-surface2 border border-border text-text"
            onClick={() => setMobileMenuOpen(true)}
          >
            <MdMenu className="text-2xl" />
          </button>
          <div className="flex items-center gap-2 text-xs text-muted">
            <span className={`w-2.5 h-2.5 rounded-full ${statusDotClass}`} />
            <span>{systemStatus}</span>
          </div>
        </div>
        {children}
      </main>
    </div>
  )
}
