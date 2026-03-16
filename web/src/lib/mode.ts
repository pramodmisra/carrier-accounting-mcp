/**
 * Environment mode management — sandbox vs production.
 * Sandbox mode uses /api/sandbox/* routes (no auth, no credentials).
 * Production mode uses /api/* routes (requires auth + connected systems).
 */

export type AppMode = 'sandbox' | 'production';

const MODE_KEY = 'carrier_accounting_mode';

export function getMode(): AppMode {
  if (typeof window === 'undefined') return 'sandbox';
  return (localStorage.getItem(MODE_KEY) as AppMode) || 'sandbox';
}

export function setMode(mode: AppMode) {
  localStorage.setItem(MODE_KEY, mode);
}

export function isSandbox(): boolean {
  return getMode() === 'sandbox';
}

/**
 * Returns the correct API prefix based on current mode.
 * Sandbox: /api/sandbox/...
 * Production: /api/...
 */
export function apiPrefix(): string {
  return isSandbox() ? '/api/sandbox' : '/api';
}
