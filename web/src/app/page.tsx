'use client'

import { useEffect, useState } from 'react'
import { api, DailyMetrics } from '@/lib/api'

function MetricCard({ label, value, subtitle, color = 'primary' }: {
  label: string; value: string; subtitle?: string; color?: string;
}) {
  return (
    <div className="metric-card">
      <p className="text-sm text-gray-500">{label}</p>
      <p className="text-3xl font-bold mt-1">{value}</p>
      {subtitle && <p className={`text-sm mt-1 text-${color}-600`}>{subtitle}</p>}
    </div>
  )
}

export default function Dashboard() {
  const [metrics, setMetrics] = useState<DailyMetrics | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.getDailyMetrics()
      .then(setMetrics)
      .catch(() => setMetrics(null))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="text-gray-500">Loading dashboard...</div>

  const total = metrics?.total_transactions || 0
  const autoRate = total > 0 ? ((metrics?.auto_approved || 0) / total * 100).toFixed(1) : '0'
  const avgConf = metrics?.avg_confidence ? (metrics.avg_confidence * 100).toFixed(1) : '0'

  return (
    <div>
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold">Daily Scorecard</h1>
          <p className="text-gray-500 text-sm mt-1">
            {new Date().toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}
          </p>
        </div>
        <div className="flex gap-2">
          <button className="btn-outline">Export Report</button>
          <a href="/upload" className="btn-primary">Upload Statement</a>
        </div>
      </div>

      {/* Metric Cards */}
      <div className="grid grid-cols-5 gap-4 mb-8">
        <MetricCard label="Total Transactions" value={total.toLocaleString()} />
        <MetricCard
          label="Auto-Approved"
          value={(metrics?.auto_approved || 0).toLocaleString()}
          subtitle={`${autoRate}%`}
          color="success"
        />
        <MetricCard
          label="Review Queue"
          value={(metrics?.review_queue || 0).toLocaleString()}
          subtitle={metrics?.review_queue ? 'Needs review' : 'Clear'}
          color="warning"
        />
        <MetricCard
          label="Posted to Epic"
          value={(metrics?.posted_to_epic || 0).toLocaleString()}
          color="success"
        />
        <MetricCard
          label="Avg Confidence"
          value={`${avgConf}%`}
        />
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-3 gap-6">
        <div className="metric-card">
          <h3 className="font-semibold mb-2">Exception Queue</h3>
          <p className="text-sm text-gray-500 mb-4">
            {metrics?.review_queue || 0} transactions need your review
          </p>
          <a href="/queue" className="btn-primary inline-block">Review Now</a>
        </div>
        <div className="metric-card">
          <h3 className="font-semibold mb-2">Run History</h3>
          <p className="text-sm text-gray-500 mb-4">
            View recent ingestion runs and their results
          </p>
          <a href="/runs" className="btn-outline inline-block">View Runs</a>
        </div>
        <div className="metric-card">
          <h3 className="font-semibold mb-2">Reconciliation</h3>
          <p className="text-sm text-gray-500 mb-4">
            Compare posted entries against Applied Epic
          </p>
          <a href="/reconciliation" className="btn-outline inline-block">Run Report</a>
        </div>
      </div>
    </div>
  )
}
