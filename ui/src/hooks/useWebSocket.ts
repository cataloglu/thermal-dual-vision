import { useEffect, useRef, useCallback, useState } from 'react'

interface WebSocketEventData {
  event_id?: string
  camera_id?: string
  event_type?: string
  [key: string]: unknown
}

interface WebSocketStatusData {
  camera_id?: string
  status?: string
  counts?: {
    online?: number
    retrying?: number
    down?: number
  }
  [key: string]: unknown
}

interface WebSocketMessage {
  type: 'event' | 'status'
  data: WebSocketEventData | WebSocketStatusData | Record<string, unknown>
}

interface UseWebSocketOptions {
  onEvent?: (data: WebSocketEventData) => void
  onStatus?: (data: WebSocketStatusData) => void
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
    reconnectInterval = 2000,
    maxReconnectAttempts = 999,
  } = options

  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const reconnectAttemptsRef = useRef(0)
  const shouldReconnectRef = useRef(true)
  const [isConnected, setIsConnected] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Store callbacks in refs so they never trigger reconnect on parent re-render
  const onEventRef = useRef(onEvent)
  const onStatusRef = useRef(onStatus)
  const onConnectRef = useRef(onConnect)
  const onDisconnectRef = useRef(onDisconnect)
  useEffect(() => { onEventRef.current = onEvent }, [onEvent])
  useEffect(() => { onStatusRef.current = onStatus }, [onStatus])
  useEffect(() => { onConnectRef.current = onConnect }, [onConnect])
  useEffect(() => { onDisconnectRef.current = onDisconnect }, [onDisconnect])

  const resolveWsUrl = useCallback(() => {
    // Development overrides
    const envWsBase = import.meta.env.VITE_WS_URL as string | undefined
    if (envWsBase) return `${envWsBase}${url}`

    // Production (Ingress aware)
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host
    
    // Get Ingress path
    const path = window.location.pathname
    // Remove trailing slash and /index.html if present
    const cleanPath = path.replace(/\/index\.html$/, '').replace(/\/+$/, '')
    
    // Ensure URL starts with / but not double slash
    const normalizedUrl = url.startsWith('/') ? url : `/${url}`
    
    // If we are at root, cleanPath is empty
    // If Ingress, cleanPath is /api/hassio_ingress/TOKEN
    // Result: wss://host/ingress_path/api/ws/events
    return `${protocol}//${host}${cleanPath}${normalizedUrl}`
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
        setIsConnected(true)
        setError(null)
        reconnectAttemptsRef.current = 0
        
        if (onConnectRef.current) {
          onConnectRef.current()
        }

        // Send ping every 15 seconds to keep connection alive (Ingress proxy timeout)
        const pingInterval = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send('ping')
          }
        }, 15000)

        ws.addEventListener('close', () => {
          clearInterval(pingInterval)
        })
      }

      ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data)

          if (message.type === 'event' && onEventRef.current) {
            onEventRef.current(message.data)
          } else if (message.type === 'status' && onStatusRef.current) {
            onStatusRef.current(message.data)
          }
        } catch (err) {
          // Silent
        }
      }

      ws.onerror = () => {
        setError('WebSocket connection error')
      }

      ws.onclose = () => {
        setIsConnected(false)
        
        if (onDisconnectRef.current) {
          onDisconnectRef.current()
        }

        // Attempt to reconnect
        if (!shouldReconnectRef.current) {
          return
        }

        if (reconnectAttemptsRef.current < maxReconnectAttempts) {
          reconnectAttemptsRef.current += 1
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
  }, [resolveWsUrl, reconnectInterval, maxReconnectAttempts])

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

  const send = useCallback((data: Record<string, unknown> | string) => {
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
