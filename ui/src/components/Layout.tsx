import { ReactNode, useEffect, useState } from 'react'
import { Sidebar } from './Sidebar'
import { api } from '../services/api'
import { MdLanguage } from 'react-icons/md'
import { useTranslation } from 'react-i18next'

interface LayoutProps {
  children: ReactNode
}

export function Layout({ children }: LayoutProps) {
  const [systemStatus, setSystemStatus] = useState<'ok' | 'degraded' | 'down'>('ok')
  const { i18n } = useTranslation()

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
    const interval = setInterval(checkHealth, 10000)

    return () => clearInterval(interval)
  }, [])

  const toggleLanguage = () => {
    const newLang = i18n.language === 'tr' ? 'en' : 'tr'
    i18n.changeLanguage(newLang)
    localStorage.setItem('language', newLang)
  }

  return (
    <div className="flex h-screen bg-background">
      <Sidebar systemStatus={systemStatus} />
      <main className="flex-1 overflow-auto relative">
        {/* Language Toggle Button */}
        <button
          onClick={toggleLanguage}
          className="fixed top-4 right-4 z-20 flex items-center gap-2 px-3 py-2 bg-surface1 border border-border rounded-lg hover:bg-surface2 transition-colors text-text text-sm font-medium"
          title="Dil değiştir / Change language"
        >
          <MdLanguage className="text-lg" />
          {i18n.language === 'tr' ? 'TR' : 'EN'}
        </button>
        {children}
      </main>
    </div>
  )
}
