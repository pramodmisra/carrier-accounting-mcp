'use client'

import { useState } from 'react'
import { api, IngestResponse } from '@/lib/api'

export default function UploadPage() {
  const [file, setFile] = useState<File | null>(null)
  const [carrier, setCarrier] = useState('')
  const [mode, setMode] = useState('trial')
  const [status, setStatus] = useState<'idle' | 'uploading' | 'processing' | 'done' | 'error'>('idle')
  const [result, setResult] = useState<IngestResponse | null>(null)
  const [error, setError] = useState('')

  const carriers = ['nationwide', 'travelers', 'hartford', 'liberty_mutual', 'chubb', 'zurich']

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!file || !carrier) return

    try {
      setStatus('uploading')
      setError('')
      const upload = await api.uploadFile(file)

      setStatus('processing')
      const ingestResult = await api.ingestStatement(upload.file_path, carrier, mode)
      setResult(ingestResult)
      setStatus('done')
    } catch (err: any) {
      setError(err.message || 'Processing failed')
      setStatus('error')
    }
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Upload Carrier Statement</h1>

      <div className="grid grid-cols-2 gap-8">
        {/* Upload Form */}
        <div className="metric-card">
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* File Drop */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Statement File</label>
              <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center
                              hover:border-primary-500 transition-colors cursor-pointer"
                   onClick={() => document.getElementById('fileInput')?.click()}>
                <input
                  id="fileInput"
                  type="file"
                  className="hidden"
                  accept=".pdf,.xlsx,.xls,.csv"
                  onChange={(e) => setFile(e.target.files?.[0] || null)}
                />
                {file ? (
                  <div>
                    <p className="font-medium">{file.name}</p>
                    <p className="text-sm text-gray-500">{(file.size / 1024).toFixed(1)} KB</p>
                  </div>
                ) : (
                  <div>
                    <p className="text-gray-500">Drop PDF or Excel file here</p>
                    <p className="text-sm text-gray-400 mt-1">or click to browse</p>
                  </div>
                )}
              </div>
            </div>

            {/* Carrier Select */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Carrier</label>
              <select
                value={carrier}
                onChange={(e) => setCarrier(e.target.value)}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                required
              >
                <option value="">Select carrier...</option>
                {carriers.map((c) => (
                  <option key={c} value={c}>{c.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}</option>
                ))}
              </select>
            </div>

            {/* Mode Toggle */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Mode</label>
              <div className="flex gap-3">
                <label className={`flex items-center gap-2 px-4 py-2 rounded-lg border cursor-pointer
                  ${mode === 'trial' ? 'border-primary-500 bg-primary-50 text-primary-700' : 'border-gray-300'}`}>
                  <input type="radio" name="mode" value="trial" checked={mode === 'trial'}
                         onChange={() => setMode('trial')} className="hidden" />
                  Trial (Safe)
                </label>
                <label className={`flex items-center gap-2 px-4 py-2 rounded-lg border cursor-pointer
                  ${mode === 'live' ? 'border-danger-500 bg-danger-50 text-danger-600' : 'border-gray-300'}`}>
                  <input type="radio" name="mode" value="live" checked={mode === 'live'}
                         onChange={() => setMode('live')} className="hidden" />
                  Live (Posts to Epic)
                </label>
              </div>
            </div>

            <button
              type="submit"
              disabled={!file || !carrier || status === 'uploading' || status === 'processing'}
              className="btn-primary w-full"
            >
              {status === 'uploading' ? 'Uploading...' :
               status === 'processing' ? 'Processing...' :
               'Process Statement'}
            </button>
          </form>
        </div>

        {/* Results */}
        <div className="metric-card">
          <h3 className="font-semibold mb-4">Results</h3>
          {status === 'idle' && <p className="text-gray-500">Upload a file to see results</p>}
          {status === 'uploading' && <p className="text-primary-600">Uploading file...</p>}
          {status === 'processing' && <p className="text-primary-600">Running pipeline: parse, normalize, validate, stage...</p>}
          {status === 'error' && <p className="text-danger-600">{error}</p>}
          {status === 'done' && result && (
            <div className="space-y-4">
              <div className="p-3 bg-success-50 rounded-lg text-success-600 text-sm font-medium">
                Processing complete!
              </div>
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div><span className="text-gray-500">Run ID:</span> <code className="text-xs">{result.run_id.slice(0, 8)}...</code></div>
                <div><span className="text-gray-500">Mode:</span> <span className={result.mode === 'trial' ? 'badge-success' : 'badge-danger'}>{result.mode}</span></div>
                <div><span className="text-gray-500">Total Parsed:</span> <strong>{result.total_parsed}</strong></div>
                <div><span className="text-gray-500">Auto-Approved:</span> <strong className="text-success-600">{result.auto_approved}</strong></div>
                <div><span className="text-gray-500">Review Queue:</span> <strong className="text-warning-600">{result.review_queue}</strong></div>
                <div><span className="text-gray-500">Rejected:</span> <strong className="text-danger-600">{result.rejected}</strong></div>
              </div>
              <div className="flex gap-2 mt-4">
                {result.review_queue > 0 && (
                  <a href="/queue" className="btn-primary">Review Queue</a>
                )}
                <a href={`/runs`} className="btn-outline">View Run Details</a>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
