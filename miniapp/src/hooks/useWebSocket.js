import { useEffect } from 'react';
import { subscribeToWebSockets } from '../api';

/**
 * Hook to manage WebSocket connections and event handlers.
 * @param {Object} handlers - Dictionary of message types to callback functions.
 *                            Example: { REQUEST_APPROVED: () => {...} }
 */
export function useWebSocket(handlers) {
  useEffect(() => {
    // Only subscribe to web sockets if the app is not running in pure mock mode
    // (mock mode has no backend to connect to, api will handle fallback if needed)
    const unsubscribe = subscribeToWebSockets(handlers);
    
    // Cleanup on unmount
    return () => {
      unsubscribe();
    };
  }, [handlers]);
}
