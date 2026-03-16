'use client'

import './globals.css'
import { useState, useEffect } from 'react'

const navItems = [
  { href: '/', label: 'Dashboard' },
  { href: '/upload', label: 'Upload Statement' },
  { href: '/queue', label: 'Review Queue' },
  { href: '/runs', label: 'Run History' },
  { href: '/reconciliation', label: 'Reconciliation' },
  { href: '/carriers', label: 'Carriers' },
  { href: '/onboarding', label: 'Setup / Connect' },
  { href: '/settings', label: 'Settings' },
]

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const [mode, setModeState] = useState<'sandbox' | 'production'>('sandbox')

  useEffect(() => {
    const stored = localStorage.getItem('carrier_accounting_mode') as any
    if (stored === 'production') setModeState('production')
  }, [])

  function toggleMode() {
    const next = mode === 'sandbox' ? 'production' : 'sandbox'
    localStorage.setItem('carrier_accounting_mode', next)
    setModeState(next)
    window.location.reload()
  }

  return (
    <html lang="en">
      <body className="bg-gray-50 text-gray-900 antialiased">
        <div className="flex h-screen">
          {/* Sidebar */}
          <aside className="w-64 bg-white border-r border-gray-200 flex flex-col">
            <div className="p-6 border-b border-gray-200">
              <h1 className="text-lg font-bold text-blue-700">Carrier Accounting</h1>
              <p className="text-xs text-gray-500 mt-1">Applied Epic Integration</p>
            </div>

            {/* Mode Toggle */}
            <div className="px-4 py-3 border-b border-gray-100">
              <button
                onClick={toggleMode}
                className={`w-full flex items-center justify-between px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                  mode === 'sandbox'
                    ? 'bg-amber-50 text-amber-700 border border-amber-200'
                    : 'bg-green-50 text-green-700 border border-green-200'
                }`}
              >
                <span>{mode === 'sandbox' ? 'Sandbox Mode' : 'Production Mode'}</span>
                <span className={`w-2 h-2 rounded-full ${mode === 'sandbox' ? 'bg-amber-500' : 'bg-green-500'}`} />
              </button>
              <p className="text-xs text-gray-400 mt-1 px-1">
                {mode === 'sandbox' ? 'Demo data — no credentials needed' : 'Connected to Epic + BigQuery'}
              </p>
            </div>

            <nav className="flex-1 p-4 space-y-1">
              {navItems.map((item) => (
                <a
                  key={item.href}
                  href={item.href}
                  className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm
                             text-gray-700 hover:bg-blue-50 hover:text-blue-700
                             transition-colors"
                >
                  {item.label}
                </a>
              ))}
            </nav>

            <div className="p-4 border-t border-gray-200">
              <p className="text-xs text-gray-400">agency.5gvector.com</p>
              <p className="text-xs text-gray-400">v0.1.0</p>
            </div>
          </aside>

          {/* Main content */}
          <main className="flex-1 overflow-auto">
            {/* Sandbox Banner */}
            {mode === 'sandbox' && (
              <div className="bg-amber-50 border-b border-amber-200 px-8 py-2 flex items-center justify-between">
                <p className="text-sm text-amber-700">
                  <strong>Sandbox Mode</strong> — Exploring with demo data. No credentials needed.
                </p>
                <a href="/onboarding" className="text-sm font-medium text-amber-700 underline hover:text-amber-900">
                  Connect your systems to go live
                </a>
              </div>
            )}
            <div className="max-w-7xl mx-auto p-8">
              {children}
            </div>
          </main>
        </div>
      </body>
    </html>
  )
}
