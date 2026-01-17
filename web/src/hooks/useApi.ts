/**
 * useApi Hook
 *
 * A reusable React hook for managing API calls with loading, error, and data states.
 *
 * Features:
 * - Automatic loading state management
 * - Error handling with ApiRequestError support
 * - Manual execution control
 * - Automatic cleanup on unmount
 * - TypeScript generic support for type-safe API responses
 *
 * @example
 * ```tsx
 * import { useApi } from '../hooks/useApi';
 * import { getStatus } from '../utils/api';
 *
 * function MyComponent() {
 *   const { data, loading, error, execute } = useApi(getStatus);
 *
 *   useEffect(() => {
 *     execute();
 *   }, []);
 *
 *   if (loading) return <div>Loading...</div>;
 *   if (error) return <div>Error: {error}</div>;
 *   return <div>{JSON.stringify(data)}</div>;
 * }
 * ```
 */

import { useState, useCallback, useRef, useEffect } from 'preact/hooks';
import { ApiRequestError } from '../utils/api';

/**
 * State shape for the useApi hook
 */
export interface UseApiState<T> {
  /** The data returned from the API call */
  data: T | null;
  /** Whether an API call is in progress */
  loading: boolean;
  /** Error message if the API call failed */
  error: string | null;
  /** Function to manually execute the API call */
  execute: (...args: any[]) => Promise<void>;
}

/**
 * Hook for managing API calls with loading, error, and data states.
 *
 * @template T - The expected response type from the API call
 * @param apiFunction - The API function to call (e.g., api.getStatus)
 * @returns Object containing data, loading, error states and execute function
 */
export function useApi<T>(
  apiFunction: (...args: any[]) => Promise<T>
): UseApiState<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Track if component is mounted to prevent state updates after unmount
  const isMountedRef = useRef<boolean>(true);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      isMountedRef.current = false;
    };
  }, []);

  /**
   * Execute the API call with error handling and state management
   */
  const execute = useCallback(
    async (...args: any[]) => {
      // Only update state if component is still mounted
      if (!isMountedRef.current) return;

      try {
        setLoading(true);
        setError(null);

        const result = await apiFunction(...args);

        // Check if still mounted before updating state
        if (isMountedRef.current) {
          setData(result);
        }
      } catch (err) {
        // Check if still mounted before updating state
        if (isMountedRef.current) {
          if (err instanceof ApiRequestError) {
            // Use the error message from ApiRequestError
            setError(err.message);
          } else if (err instanceof Error) {
            setError(err.message);
          } else {
            setError('An unknown error occurred');
          }
        }
      } finally {
        // Check if still mounted before updating state
        if (isMountedRef.current) {
          setLoading(false);
        }
      }
    },
    [apiFunction]
  );

  return {
    data,
    loading,
    error,
    execute,
  };
}

export default useApi;
