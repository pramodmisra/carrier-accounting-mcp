/**
 * Environment mode management — sandbox vs production.
 * Stored in localStorage so it persists across sessions.
 */

export type EnvMode = 'sandbox' | 'production';

const STORAGE_KEY = 'carrier_accounting_env_mode';

export function getEnvMode(): EnvMode {
  if (typeof window === 'undefined') return 'sandbox';
  return (localStorage.getItem(STORAGE_KEY) as EnvMode) || 'sandbox';
}

export function setEnvMode(mode: EnvMode) {
  localStorage.setItem(STORAGE_KEY, mode);
}

/**
 * Returns the correct API prefix based on current mode.
 * Sandbox: /api/sandbox/...
 * Production: /api/...
 */
export function apiPrefix(): string {
  return getEnvMode() === 'sandbox' ? '/api/sandbox' : '/api';
}
