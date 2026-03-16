'use client'

import { useEffect, useState } from 'react'
import { api, Transaction } from '@/lib/api'

function ConfidenceBadge({ score }: { score: number }) {
  const pct = (score * 100).toFixed(1)
  if (score >= 0.95) return <span className="badge-success">{pct}%</span>
  if (score >= 0.80) return <span className="badge-warning">{pct}%</span>
  return <span className="badge-danger">{pct}%</span>
}

export default function QueuePage() {
  const [queue, setQueue] = useState<Transaction[]>([])
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [reviewer, setReviewer] = useState('')

  useEffect(() => {
    api.getExceptionQueue()
      .then(setQueue)
      .catch(() => setQueue([]))
      .finally(() => setLoading(false))
  }, [])

  async function handleApprove(id: string) {
    if (!reviewer) return alert('Enter your name as reviewer')
    await api.approveTransaction(id, reviewer)
    setQueue(queue.filter(t => t.transaction_id !== id))
  }

  async function handleReject(id: string) {
    if (!reviewer) return alert('Enter your name as reviewer')
    const reason = prompt('Rejection reason:')
    if (!reason) return
    await api.rejectTransaction(id, reviewer, reason)
    setQueue(queue.filter(t => t.transaction_id !== id))
  }

  if (loading) return <div className="text-gray-500">Loading review queue...</div>

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">Review Queue</h1>
          <p className="text-gray-500 text-sm mt-1">{queue.length} transactions need review</p>
        </div>
        <div className="flex items-center gap-3">
          <input
            type="text"
            placeholder="Your name"
            value={reviewer}
            onChange={(e) => setReviewer(e.target.value)}
            className="border border-gray-300 rounded-lg px-3 py-2 text-sm w-48"
          />
        </div>
      </div>

      {queue.length === 0 ? (
        <div className="metric-card text-center py-12">
          <p className="text-lg text-success-600 font-medium">All clear!</p>
          <p className="text-gray-500 mt-1">No transactions need review today.</p>
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-gray-500">Carrier</th>
                <th className="px-4 py-3 text-left font-medium text-gray-500">Policy #</th>
                <th className="px-4 py-3 text-left font-medium text-gray-500">Client</th>
                <th className="px-4 py-3 text-right font-medium text-gray-500">Amount</th>
                <th className="px-4 py-3 text-center font-medium text-gray-500">Confidence</th>
                <th className="px-4 py-3 text-left font-medium text-gray-500">Issues</th>
                <th className="px-4 py-3 text-right font-medium text-gray-500">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {queue.map((txn) => (
                <tr key={txn.transaction_id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium">{txn.carrier}</td>
                  <td className="px-4 py-3 font-mono text-xs">{txn.policy_number}</td>
                  <td className="px-4 py-3">{txn.client_name}</td>
                  <td className="px-4 py-3 text-right font-mono">${Number(txn.amount).toLocaleString()}</td>
                  <td className="px-4 py-3 text-center"><ConfidenceBadge score={txn.confidence_score} /></td>
                  <td className="px-4 py-3 text-xs text-gray-500 max-w-xs truncate">
                    {[...txn.validation_warnings, ...txn.validation_errors].join('; ') || '-'}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex gap-1 justify-end">
                      <button
                        onClick={() => handleApprove(txn.transaction_id)}
                        className="px-3 py-1 bg-success-50 text-success-600 rounded text-xs font-medium
                                   hover:bg-success-500 hover:text-white transition-colors"
                      >
                        Approve
                      </button>
                      <button
                        onClick={() => handleReject(txn.transaction_id)}
                        className="px-3 py-1 bg-danger-50 text-danger-600 rounded text-xs font-medium
                                   hover:bg-danger-500 hover:text-white transition-colors"
                      >
                        Reject
                      </button>
                    </div>
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
