import { Component, ErrorInfo, ReactNode } from 'react'

interface ErrorBoundaryProps {
  children: ReactNode
}

interface ErrorBoundaryState {
  hasError: boolean
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { hasError: false }

  static getDerivedStateFromError() {
    return { hasError: true }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('UI crashed:', error, info)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-background flex items-center justify-center p-6">
          <div className="bg-surface1 border border-border rounded-lg p-6 max-w-md w-full text-center">
            <h2 className="text-xl font-semibold text-text mb-2">Bir hata oluştu</h2>
            <p className="text-muted mb-4">Sayfa yüklenemedi. Lütfen tekrar deneyin.</p>
            <button
              onClick={() => window.location.reload()}
              className="px-4 py-2 bg-accent text-white rounded-lg hover:bg-accent/90 transition-colors"
            >
              Yeniden Dene
            </button>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}
