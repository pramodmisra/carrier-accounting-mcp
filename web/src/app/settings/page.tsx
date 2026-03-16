'use client'

import { useEffect, useState } from 'react'
import { api } from '@/lib/api'

export default function SettingsPage() {
  const [settings, setSettings] = useState<any>(null)

  useEffect(() => {
    api.getSettings().then(setSettings).catch(() => {})
  }, [])

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Settings</h1>

      <div className="grid grid-cols-2 gap-6">
        {/* Connection Settings */}
        <div className="metric-card">
          <h3 className="font-semibold mb-4">BigQuery Connection</h3>
          <div className="space-y-3 text-sm">
            <div>
              <label className="block text-gray-500 mb-1">GCP Project</label>
              <input type="text" value={settings?.gcp_project || ''} readOnly
                     className="w-full border border-gray-200 rounded-lg px-3 py-2 bg-gray-50" />
            </div>
            <div>
              <label className="block text-gray-500 mb-1">Dataset</label>
              <input type="text" value={settings?.bq_dataset || ''} readOnly
                     className="w-full border border-gray-200 rounded-lg px-3 py-2 bg-gray-50" />
            </div>
          </div>
        </div>

        <div className="metric-card">
          <h3 className="font-semibold mb-4">Applied Epic</h3>
          <div className="space-y-3 text-sm">
            <div>
              <label className="block text-gray-500 mb-1">Environment</label>
              <input type="text" value={settings?.epic_environment || ''} readOnly
                     className="w-full border border-gray-200 rounded-lg px-3 py-2 bg-gray-50" />
            </div>
            <div>
              <label className="block text-gray-500 mb-1">API Key</label>
              <input type="password" value="••••••••" readOnly
                     className="w-full border border-gray-200 rounded-lg px-3 py-2 bg-gray-50" />
            </div>
          </div>
        </div>

        {/* Thresholds */}
        <div className="metric-card">
          <h3 className="font-semibold mb-4">Confidence Thresholds</h3>
          <div className="space-y-3 text-sm">
            <div>
              <label className="block text-gray-500 mb-1">Auto-Post Threshold</label>
              <div className="flex items-center gap-2">
                <input type="range" min="0.80" max="1.0" step="0.01"
                       value={settings?.auto_post_threshold || 0.95}
                       className="flex-1" readOnly />
                <span className="font-mono w-12 text-right">{settings?.auto_post_threshold || 0.95}</span>
              </div>
            </div>
            <div>
              <label className="block text-gray-500 mb-1">Review Threshold</label>
              <div className="flex items-center gap-2">
                <input type="range" min="0.50" max="0.95" step="0.01"
                       value={settings?.review_threshold || 0.80}
                       className="flex-1" readOnly />
                <span className="font-mono w-12 text-right">{settings?.review_threshold || 0.80}</span>
              </div>
            </div>
          </div>
        </div>

        <div className="metric-card">
          <h3 className="font-semibold mb-4">Default Mode</h3>
          <div className="space-y-3 text-sm">
            <p className="text-gray-500">Current default: <strong>{settings?.default_mode || 'trial'}</strong></p>
            <div className="flex gap-3">
              <label className="flex items-center gap-2 px-4 py-2 rounded-lg border border-primary-500 bg-primary-50 text-primary-700 cursor-pointer">
                <input type="radio" name="mode" checked readOnly /> Trial (Safe)
              </label>
              <label className="flex items-center gap-2 px-4 py-2 rounded-lg border border-gray-300 cursor-pointer">
                <input type="radio" name="mode" readOnly /> Live
              </label>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
