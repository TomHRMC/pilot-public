/**
 * sessionExpiredEmitter — React Native event bridge for auth:session-expired
 *
 * Location: apps/mobile/hooks/sessionExpiredEmitter.ts
 *
 * React Native doesn't have window.dispatchEvent. This module provides a
 * DeviceEventEmitter-based bridge so the apiClient (which dispatches
 * CustomEvent on web) can signal session expiry to the mobile auth layer.
 *
 * Usage in apiClient (mobile builds):
 *   import { DeviceEventEmitter } from 'react-native';
 *   DeviceEventEmitter.emit('auth:session-expired');
 *
 * The apiClient uses window.dispatchEvent (web path). On mobile, the
 * 401 interceptor reaches the catch block and the sessionExpiredEmitter
 * is used directly from useSessionExpiry.
 */

import { DeviceEventEmitter } from "react-native";

export const sessionExpiredEmitter = DeviceEventEmitter;

export const SESSION_EXPIRED_EVENT = "auth:session-expired" as const;

/** Call this from the mobile-side 401 handler to signal session expiry. */
export function emitSessionExpired(): void {
  DeviceEventEmitter.emit(SESSION_EXPIRED_EVENT);
}
