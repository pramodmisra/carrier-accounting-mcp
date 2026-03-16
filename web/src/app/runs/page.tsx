'use client'

import { useEffect, useState } from 'react'
import { api, RunSummary } from '@/lib/api'

export default function RunsPage() {
  const [runs, setRuns] = useState<RunSummary[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.getRunHistory(30)
      .then(setRuns)
      .catch(() => setRuns([]))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="text-gray-500">Loading run history...</div>

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Run History</h1>

      {runs.length === 0 ? (
        <div className="metric-card text-center py-12">
          <p className="text-gray-500">No runs yet. Upload a carrier statement to get started.</p>
          <a href="/upload" className="btn-primary inline-block mt-4">Upload Statement</a>
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-gray-500">Run ID</th>
                <th className="px-4 py-3 text-left font-medium text-gray-500">Carrier</th>
                <th className="px-4 py-3 text-left font-medium text-gray-500">File</th>
                <th className="px-4 py-3 text-center font-medium text-gray-500">Mode</th>
                <th className="px-4 py-3 text-right font-medium text-gray-500">Total</th>
                <th className="px-4 py-3 text-right font-medium text-gray-500">Auto</th>
                <th className="px-4 py-3 text-right font-medium text-gray-500">Review</th>
                <th className="px-4 py-3 text-right font-medium text-gray-500">Failed</th>
                <th className="px-4 py-3 text-left font-medium text-gray-500">Status</th>
                <th className="px-4 py-3 text-right font-medium text-gray-500">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {runs.map((run) => (
                <tr key={run.run_id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-mono text-xs">{run.run_id.slice(0, 8)}...</td>
                  <td className="px-4 py-3 font-medium">{run.carrier}</td>
                  <td className="px-4 py-3 text-xs text-gray-500 max-w-[200px] truncate">{run.source_file}</td>
                  <td className="px-4 py-3 text-center">
                    <span className={run.mode === 'trial' ? 'badge-success' : 'badge-danger'}>{run.mode}</span>
                  </td>
                  <td className="px-4 py-3 text-right">{run.total_transactions}</td>
                  <td className="px-4 py-3 text-right text-success-600">{run.auto_approved}</td>
                  <td className="px-4 py-3 text-right text-warning-600">{run.review_queue}</td>
                  <td className="px-4 py-3 text-right text-danger-600">{run.failed}</td>
                  <td className="px-4 py-3">
                    <span className={`badge-${run.status === 'completed' ? 'success' : 'warning'}`}>
                      {run.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button className="btn-outline text-xs py-1">Details</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
