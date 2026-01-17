/**
 * useWebSocket Hook
 *
 * A reusable React hook for managing WebSocket connections with auto-reconnect,
 * event subscription, and connection state management.
 *
 * Features:
 * - Automatic connection management with cleanup
 * - Auto-reconnect with exponential backoff
 * - Event subscription system for motion_detected and status_update events
 * - Connection state tracking (connected, connecting, disconnected)
 * - TypeScript interfaces for type-safe event handling
 * - Comprehensive error handling and logging
 *
 * @example
 * ```tsx
 * import { useWebSocket } from '../hooks/useWebSocket';
 *
 * function MyComponent() {
 *   const { connected, subscribe } = useWebSocket();
 *
 *   useEffect(() => {
 *     const unsubscribe = subscribe('motion_detected', (data) => {
 *       console.log('Motion detected:', data);
 *     });
 *
 *     return unsubscribe;
 *   }, [subscribe]);
 *
 *   return <div>WebSocket: {connected ? 'Connected' : 'Disconnected'}</div>;
 * }
 * ```
 */

import { useState, useEffect, useCallback, useRef } from 'preact/hooks';
import { io, Socket } from 'socket.io-client';

// ============================================================================
// TypeScript Interfaces for WebSocket Events
// ============================================================================

/**
 * Motion detection event data
 */
export interface MotionEvent {
  detected: boolean;
  timestamp: string;
  real_motion?: boolean;
  confidence?: number;
  description?: string;
  detected_objects?: string[];
  threat_level?: string;
  recommended_action?: string;
  detailed_analysis?: string;
  processing_time?: number;
}

/**
 * System status update event data
 */
export interface StatusUpdateEvent {
  [key: string]: any;
}

/**
 * Connected event data
 */
export interface ConnectedEvent {
  message: string;
  sid: string;
}

/**
 * WebSocket event types
 */
export type WebSocketEventType = 'motion_detected' | 'status_update' | 'connected';

/**
 * WebSocket event handler function
 */
export type WebSocketEventHandler<T = any> = (data: T) => void;

/**
 * Connection state
 */
export type ConnectionState = 'connected' | 'connecting' | 'disconnected';

/**
 * State shape for the useWebSocket hook
 */
export interface UseWebSocketState {
  /** Whether the WebSocket is currently connected */
  connected: boolean;
  /** Current connection state */
  connectionState: ConnectionState;
  /** Subscribe to a WebSocket event */
  subscribe: <T = any>(event: WebSocketEventType, handler: WebSocketEventHandler<T>) => () => void;
  /** Manually disconnect the WebSocket */
  disconnect: () => void;
  /** Manually reconnect the WebSocket */
  reconnect: () => void;
}

// ============================================================================
// Hook Implementation
// ============================================================================

/**
 * Hook for managing WebSocket connections with auto-reconnect and event subscription.
 *
 * @param namespace - WebSocket namespace (default: '/events')
 * @returns Object containing connection state and subscription functions
 */
export function useWebSocket(namespace: string = '/events'): UseWebSocketState {
  const [connected, setConnected] = useState<boolean>(false);
  const [connectionState, setConnectionState] = useState<ConnectionState>('disconnected');

  // Socket reference
  const socketRef = useRef<Socket | null>(null);

  // Track if component is mounted to prevent state updates after unmount
  const isMountedRef = useRef<boolean>(true);

  // Reconnection state
  const reconnectAttemptsRef = useRef<number>(0);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const maxReconnectDelay = 30000; // Max 30 seconds
  const baseReconnectDelay = 2000; // Start with 2 seconds

  /**
   * Get the WebSocket URL based on environment
   */
  const getWebSocketUrl = useCallback((): string => {
    // In development, Vite proxy handles the connection
    // In production, Flask backend serves everything
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    return `${protocol}//${host}`;
  }, []);

  /**
   * Calculate reconnection delay with exponential backoff
   */
  const getReconnectDelay = useCallback((): number => {
    const delay = Math.min(
      baseReconnectDelay * Math.pow(2, reconnectAttemptsRef.current),
      maxReconnectDelay
    );
    return delay;
  }, []);

  /**
   * Connect to WebSocket server
   */
  const connect = useCallback(() => {
    if (socketRef.current?.connected) {
      return;
    }

    if (!isMountedRef.current) return;

    setConnectionState('connecting');

    const url = getWebSocketUrl();
    const socket = io(url + namespace, {
      transports: ['websocket', 'polling'],
      reconnection: false, // We handle reconnection manually
    });

    socketRef.current = socket;

    // Connection successful
    socket.on('connect', () => {
      if (!isMountedRef.current) return;

      console.log('[WebSocket] Connected to', namespace);
      setConnected(true);
      setConnectionState('connected');
      reconnectAttemptsRef.current = 0;

      // Clear any pending reconnection attempts
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }
    });

    // Connection failed or disconnected
    socket.on('disconnect', (reason: string) => {
      if (!isMountedRef.current) return;

      console.log('[WebSocket] Disconnected:', reason);
      setConnected(false);
      setConnectionState('disconnected');

      // Auto-reconnect unless disconnect was intentional
      if (reason !== 'io client disconnect') {
        const delay = getReconnectDelay();
        console.log(`[WebSocket] Reconnecting in ${delay}ms (attempt ${reconnectAttemptsRef.current + 1})`);

        reconnectTimeoutRef.current = setTimeout(() => {
          if (!isMountedRef.current) return;
          reconnectAttemptsRef.current++;
          connect();
        }, delay);
      }
    });

    // Connection error
    socket.on('connect_error', (error: Error) => {
      if (!isMountedRef.current) return;

      console.error('[WebSocket] Connection error:', error.message);
      setConnected(false);
      setConnectionState('disconnected');

      // Auto-reconnect on error
      const delay = getReconnectDelay();
      console.log(`[WebSocket] Reconnecting in ${delay}ms (attempt ${reconnectAttemptsRef.current + 1})`);

      reconnectTimeoutRef.current = setTimeout(() => {
        if (!isMountedRef.current) return;
        reconnectAttemptsRef.current++;
        connect();
      }, delay);
    });

    // Handle welcome message
    socket.on('connected', (data: ConnectedEvent) => {
      console.log('[WebSocket]', data.message);
    });
  }, [namespace, getWebSocketUrl, getReconnectDelay]);

  /**
   * Disconnect from WebSocket server
   */
  const disconnect = useCallback(() => {
    console.log('[WebSocket] Manually disconnecting');

    // Clear any pending reconnection attempts
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    // Disconnect socket
    if (socketRef.current) {
      socketRef.current.disconnect();
      socketRef.current = null;
    }

    if (isMountedRef.current) {
      setConnected(false);
      setConnectionState('disconnected');
      reconnectAttemptsRef.current = 0;
    }
  }, []);

  /**
   * Manually reconnect to WebSocket server
   */
  const reconnect = useCallback(() => {
    console.log('[WebSocket] Manually reconnecting');
    disconnect();
    setTimeout(() => {
      reconnectAttemptsRef.current = 0;
      connect();
    }, 100);
  }, [disconnect, connect]);

  /**
   * Subscribe to a WebSocket event
   *
   * @param event - Event name to subscribe to
   * @param handler - Event handler function
   * @returns Unsubscribe function
   */
  const subscribe = useCallback(
    <T = any>(event: WebSocketEventType, handler: WebSocketEventHandler<T>) => {
      if (!socketRef.current) {
        console.warn('[WebSocket] Cannot subscribe: socket not initialized');
        return () => {};
      }

      console.log('[WebSocket] Subscribing to event:', event);

      // Add event listener
      socketRef.current.on(event, handler);

      // Return unsubscribe function
      return () => {
        if (socketRef.current) {
          console.log('[WebSocket] Unsubscribing from event:', event);
          socketRef.current.off(event, handler);
        }
      };
    },
    []
  );

  // Connect on mount and cleanup on unmount
  useEffect(() => {
    isMountedRef.current = true;
    connect();

    return () => {
      isMountedRef.current = false;
      disconnect();
    };
  }, [connect, disconnect]);

  return {
    connected,
    connectionState,
    subscribe,
    disconnect,
    reconnect,
  };
}

export default useWebSocket;
