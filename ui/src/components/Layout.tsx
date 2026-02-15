import { ReactNode, useEffect, useState } from 'react'
import { Sidebar } from './Sidebar'
import { api } from '../services/api'

interface LayoutProps {
  children: ReactNode
}

export function Layout({ children }: LayoutProps) {
  const [systemStatus, setSystemStatus] = useState<'ok' | 'degraded' | 'down'>('ok')

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

  return (
    <div className="flex h-screen bg-background">
      <Sidebar systemStatus={systemStatus} />
      <main className="flex-1 flex flex-col min-h-0 overflow-auto relative">
        {children}
      </main>
    </div>
  )
}
