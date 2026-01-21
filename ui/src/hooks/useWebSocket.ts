import { useEffect, useRef, useCallback, useState } from 'react'

interface WebSocketMessage {
  type: 'event' | 'status'
  data: any
}

interface UseWebSocketOptions {
  onEvent?: (data: any) => void
  onStatus?: (data: any) => void
  onConnect?: () => void
  onDisconnect?: () => void
  reconnectInterval?: number
  maxReconnectAttempts?: number
}

export function useWebSocket(url: string, options: UseWebSocketOptions = {}) {
  const {
    onEvent,
    onStatus,
    onConnect,
    onDisconnect,
    reconnectInterval = 3000,
    maxReconnectAttempts = 10,
  } = options

  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const reconnectAttemptsRef = useRef(0)
  const shouldReconnectRef = useRef(true)
  const [isConnected, setIsConnected] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const resolveWsUrl = useCallback(() => {
    const envWsBase = import.meta.env.VITE_WS_URL as string | undefined
    const envApiBase = import.meta.env.VITE_API_URL as string | undefined
    const wsBase =
      envWsBase ||
      (envApiBase && envApiBase.startsWith('http')
        ? envApiBase.replace(/^http/, 'ws')
        : '')

    const normalizedPath = url.startsWith('/') ? url : `/${url}`

    if (wsBase) {
      const base = wsBase.replace(/\/+$/, '')
      const path =
        base.endsWith('/api') && normalizedPath.startsWith('/api/')
          ? normalizedPath.slice(4)
          : normalizedPath
      return `${base}${path}`
    }

    return url.startsWith('ws://') || url.startsWith('wss://')
      ? url
      : `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}${normalizedPath}`
  }, [url])

  const connect = useCallback(() => {
    try {
      // Close existing connection
      if (wsRef.current) {
        wsRef.current.close()
      }

      const wsUrl = resolveWsUrl()

      // Create WebSocket connection
      const ws = new WebSocket(wsUrl)

      ws.onopen = () => {
        // console.log('WebSocket connected') // Removed: too verbose
        setIsConnected(true)
        setError(null)
        reconnectAttemptsRef.current = 0
        
        if (onConnect) {
          onConnect()
        }

        // Send ping every 30 seconds to keep connection alive
        const pingInterval = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send('ping')
          }
        }, 30000)

        ws.addEventListener('close', () => {
          clearInterval(pingInterval)
        })
      }

      ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data)

          if (message.type === 'event' && onEvent) {
            onEvent(message.data)
          } else if (message.type === 'status' && onStatus) {
            onStatus(message.data)
          }
        } catch (err) {
          // Silent: don't spam console
        }
      }

      ws.onerror = () => {
        // Silent: error is expected on first connection attempt
        setError('WebSocket connection error')
      }

      ws.onclose = () => {
        // console.log('WebSocket disconnected') // Removed: too verbose
        setIsConnected(false)
        
        if (onDisconnect) {
          onDisconnect()
        }

        // Attempt to reconnect
        if (!shouldReconnectRef.current) {
          return
        }

        if (reconnectAttemptsRef.current < maxReconnectAttempts) {
          reconnectAttemptsRef.current += 1
          // console.log(`Reconnecting... Attempt ${reconnectAttemptsRef.current}/${maxReconnectAttempts}`) // Removed
          
          reconnectTimeoutRef.current = setTimeout(() => {
            connect()
          }, reconnectInterval)
        } else {
          setError('Max reconnection attempts reached')
        }
      }

      wsRef.current = ws
    } catch (err) {
      console.error('Failed to create WebSocket:', err)
      setError('Failed to create WebSocket connection')
    }
  }, [
    resolveWsUrl,
    onEvent,
    onStatus,
    onConnect,
    onDisconnect,
    reconnectInterval,
    maxReconnectAttempts,
  ])

  useEffect(() => {
    shouldReconnectRef.current = true
    connect()

    return () => {
      // Cleanup
      shouldReconnectRef.current = false
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
      }
      
      if (wsRef.current) {
        wsRef.current.close()
      }
    }
  }, [connect])

  const send = useCallback((data: any) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data))
    } else {
      console.warn('WebSocket is not connected')
    }
  }, [])

  const reconnect = useCallback(() => {
    reconnectAttemptsRef.current = 0
    connect()
  }, [connect])

  return {
    isConnected,
    error,
    send,
    reconnect,
  }
}
