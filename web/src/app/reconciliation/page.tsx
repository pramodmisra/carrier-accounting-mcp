'use client'

import { useState } from 'react'
import { api } from '@/lib/api'

export default function ReconciliationPage() {
  const [reportType, setReportType] = useState<'reconciliation' | 'trial-diff'>('trial-diff')
  const [runId, setRunId] = useState('')
  const [carrier, setCarrier] = useState('')
  const [result, setResult] = useState<any>(null)
  const [loading, setLoading] = useState(false)

  async function runReport() {
    setLoading(true)
    try {
      const params = {
        run_id: runId || undefined,
        carrier: carrier || undefined,
      }
      const data = reportType === 'reconciliation'
        ? await api.getReconciliation(params)
        : await api.getTrialDiff(params)
      setResult(data)
    } catch (err) {
      setResult({ error: 'Report failed' })
    }
    setLoading(false)
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Reconciliation Reports</h1>

      <div className="grid grid-cols-3 gap-6 mb-8">
        {/* Controls */}
        <div className="metric-card col-span-1">
          <h3 className="font-semibold mb-4">Report Settings</h3>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Report Type</label>
              <select
                value={reportType}
                onChange={(e) => setReportType(e.target.value as any)}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
              >
                <option value="trial-diff">Trial Diff (Shadow vs Epic)</option>
                <option value="reconciliation">Posted vs Epic</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Run ID (optional)</label>
              <input
                type="text"
                value={runId}
                onChange={(e) => setRunId(e.target.value)}
                placeholder="e.g. abc12345-..."
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Carrier (optional)</label>
              <select value={carrier} onChange={(e) => setCarrier(e.target.value)}
                      className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm">
                <option value="">All carriers</option>
                {['nationwide','travelers','hartford','liberty_mutual','chubb','zurich'].map(c => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </div>
            <button onClick={runReport} disabled={loading} className="btn-primary w-full">
              {loading ? 'Running...' : 'Generate Report'}
            </button>
          </div>
        </div>

        {/* Results */}
        <div className="metric-card col-span-2">
          <h3 className="font-semibold mb-4">Results</h3>
          {!result && <p className="text-gray-500">Configure and run a report to see results</p>}
          {result?.error && <p className="text-danger-600">{result.error}</p>}
          {result?.status === 'no_data' && <p className="text-gray-500">{result.message}</p>}
          {result?.summary && (
            <div>
              {/* Summary Cards */}
              <div className="grid grid-cols-3 gap-3 mb-6">
                <div className="p-3 bg-gray-50 rounded-lg text-center">
                  <p className="text-2xl font-bold">{result.summary.total_transactions || result.summary.total_checked}</p>
                  <p className="text-xs text-gray-500">Total Checked</p>
                </div>
                {result.summary.matched !== undefined && (
                  <div className="p-3 bg-success-50 rounded-lg text-center">
                    <p className="text-2xl font-bold text-success-600">{result.summary.matched}</p>
                    <p className="text-xs text-gray-500">Matched</p>
                  </div>
                )}
                {result.summary.would_auto_post !== undefined && (
                  <div className="p-3 bg-success-50 rounded-lg text-center">
                    <p className="text-2xl font-bold text-success-600">{result.summary.would_auto_post}</p>
                    <p className="text-xs text-gray-500">Would Auto-Post</p>
                  </div>
                )}
                {result.summary.mismatched !== undefined && (
                  <div className="p-3 bg-danger-50 rounded-lg text-center">
                    <p className="text-2xl font-bold text-danger-600">{result.summary.mismatched}</p>
                    <p className="text-xs text-gray-500">Mismatched</p>
                  </div>
                )}
                {result.summary.auto_post_rate_pct !== undefined && (
                  <div className="p-3 bg-primary-50 rounded-lg text-center">
                    <p className="text-2xl font-bold text-primary-600">{result.summary.auto_post_rate_pct}%</p>
                    <p className="text-xs text-gray-500">Auto-Post Rate</p>
                  </div>
                )}
              </div>

              {/* Recommendation */}
              {result.recommendation && (
                <div className="p-4 bg-primary-50 rounded-lg border border-primary-200 mb-4">
                  <p className="text-sm font-medium text-primary-700">{result.recommendation}</p>
                </div>
              )}

              {/* Comparison Detail */}
              {result.comparisons?.length > 0 && (
                <div className="text-sm">
                  <h4 className="font-medium mb-2">Transaction Details ({result.comparisons.length})</h4>
                  <div className="max-h-96 overflow-auto border rounded-lg">
                    <pre className="p-3 text-xs">{JSON.stringify(result.comparisons.slice(0, 10), null, 2)}</pre>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
