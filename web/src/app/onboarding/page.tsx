'use client'

import { useState, useEffect } from 'react'

type Step = 'welcome' | 'epic' | 'bigquery' | 'review' | 'done';

export default function OnboardingPage() {
  const [step, setStep] = useState<Step>('welcome')
  const [epicUrl, setEpicUrl] = useState('')
  const [epicKey, setEpicKey] = useState('')
  const [epicAgency, setEpicAgency] = useState('')
  const [gcpProject, setGcpProject] = useState('')
  const [epicStatus, setEpicStatus] = useState<string>('')
  const [bqStatus, setBqStatus] = useState<string>('')
  const [testing, setTesting] = useState(false)

  async function testEpic() {
    setTesting(true)
    setEpicStatus('')
    try {
      const res = await fetch('/api/onboarding/test-epic', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ epic_sdk_url: epicUrl, epic_api_key: epicKey, epic_agency_id: epicAgency }),
      })
      const data = await res.json()
      setEpicStatus(data.status === 'connected' ? 'connected' : `failed: ${data.message}`)
    } catch {
      setEpicStatus('failed: Network error')
    }
    setTesting(false)
  }

  async function testBQ() {
    setTesting(true)
    setBqStatus('')
    try {
      const res = await fetch('/api/onboarding/test-bigquery', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ gcp_project: gcpProject }),
      })
      const data = await res.json()
      setBqStatus(data.status === 'connected' ? `connected (${data.datasets?.length || 0} datasets)` : `failed: ${data.message}`)
    } catch {
      setBqStatus('failed: Network error')
    }
    setTesting(false)
  }

  function goProduction() {
    localStorage.setItem('carrier_accounting_env_mode', 'production')
    window.location.href = '/'
  }

  return (
    <div className="max-w-3xl mx-auto">
      <h1 className="text-2xl font-bold mb-2">Connect to Production</h1>
      <p className="text-gray-500 mb-8">Set up your Applied Epic and BigQuery connections to go live.</p>

      {/* Progress Steps */}
      <div className="flex items-center gap-2 mb-8">
        {(['welcome', 'epic', 'bigquery', 'review', 'done'] as Step[]).map((s, i) => (
          <div key={s} className="flex items-center gap-2">
            <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold
              ${step === s ? 'bg-primary-600 text-white' :
                (['welcome','epic','bigquery','review','done'].indexOf(step) > i) ? 'bg-success-500 text-white' :
                'bg-gray-200 text-gray-500'}`}>
              {i + 1}
            </div>
            {i < 4 && <div className="w-12 h-0.5 bg-gray-200" />}
          </div>
        ))}
      </div>

      {/* Step Content */}
      {step === 'welcome' && (
        <div className="metric-card">
          <h2 className="text-xl font-semibold mb-4">Welcome to Production Setup</h2>
          <p className="text-gray-600 mb-4">
            You've been using the sandbox to explore carrier accounting automation.
            Now let's connect your real systems.
          </p>
          <div className="space-y-3 mb-6">
            <div className="flex items-start gap-3 p-3 bg-gray-50 rounded-lg">
              <span className="text-lg">1</span>
              <div>
                <p className="font-medium">Applied Epic SDK</p>
                <p className="text-sm text-gray-500">Connect your Epic API to post accounting entries automatically</p>
              </div>
            </div>
            <div className="flex items-start gap-3 p-3 bg-gray-50 rounded-lg">
              <span className="text-lg">2</span>
              <div>
                <p className="font-medium">BigQuery Data Lake</p>
                <p className="text-sm text-gray-500">Connect your policy data for validation and reconciliation</p>
              </div>
            </div>
            <div className="flex items-start gap-3 p-3 bg-gray-50 rounded-lg">
              <span className="text-lg">3</span>
              <div>
                <p className="font-medium">First Trial Run</p>
                <p className="text-sm text-gray-500">Upload a real statement in trial mode — zero Epic writes until you're ready</p>
              </div>
            </div>
          </div>
          <div className="flex gap-3">
            <button onClick={() => setStep('epic')} className="btn-primary">Get Started</button>
            <a href="/" className="btn-outline">Skip — Stay in Sandbox</a>
          </div>
        </div>
      )}

      {step === 'epic' && (
        <div className="metric-card">
          <h2 className="text-xl font-semibold mb-4">Step 1: Applied Epic SDK</h2>
          <p className="text-gray-500 mb-4 text-sm">
            Optional — you can skip this and use CSV batch imports instead.
            Your API key is encrypted at rest and never shared.
          </p>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Epic SDK URL</label>
              <input type="url" value={epicUrl} onChange={e => setEpicUrl(e.target.value)}
                placeholder="https://api.appliedepic.com/v1"
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">API Key</label>
              <input type="password" value={epicKey} onChange={e => setEpicKey(e.target.value)}
                placeholder="Your Applied Epic API key"
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Agency ID</label>
              <input type="text" value={epicAgency} onChange={e => setEpicAgency(e.target.value)}
                placeholder="Your Epic agency ID"
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
            </div>
            {epicUrl && epicKey && (
              <button onClick={testEpic} disabled={testing} className="btn-outline">
                {testing ? 'Testing...' : 'Test Connection'}
              </button>
            )}
            {epicStatus && (
              <div className={`p-3 rounded-lg text-sm ${epicStatus === 'connected' ? 'bg-success-50 text-success-600' : 'bg-danger-50 text-danger-600'}`}>
                {epicStatus === 'connected' ? 'Connected to Applied Epic!' : epicStatus}
              </div>
            )}
          </div>
          <div className="flex gap-3 mt-6">
            <button onClick={() => setStep('bigquery')} className="btn-primary">
              {epicUrl ? 'Next: BigQuery' : 'Skip — Set Up Later'}
            </button>
            <button onClick={() => setStep('welcome')} className="btn-outline">Back</button>
          </div>
        </div>
      )}

      {step === 'bigquery' && (
        <div className="metric-card">
          <h2 className="text-xl font-semibold mb-4">Step 2: BigQuery Data Lake</h2>
          <p className="text-gray-500 mb-4 text-sm">
            Optional — without BigQuery, the system still works but can't validate
            policies or check for duplicates. You can connect later.
          </p>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">GCP Project ID</label>
              <input type="text" value={gcpProject} onChange={e => setGcpProject(e.target.value)}
                placeholder="your-gcp-project-id"
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
            </div>
            {gcpProject && (
              <button onClick={testBQ} disabled={testing} className="btn-outline">
                {testing ? 'Testing...' : 'Test Connection'}
              </button>
            )}
            {bqStatus && (
              <div className={`p-3 rounded-lg text-sm ${bqStatus.startsWith('connected') ? 'bg-success-50 text-success-600' : 'bg-danger-50 text-danger-600'}`}>
                {bqStatus.startsWith('connected') ? `Connected! ${bqStatus}` : bqStatus}
              </div>
            )}
          </div>
          <div className="flex gap-3 mt-6">
            <button onClick={() => setStep('review')} className="btn-primary">
              {gcpProject ? 'Next: Review' : 'Skip — Set Up Later'}
            </button>
            <button onClick={() => setStep('epic')} className="btn-outline">Back</button>
          </div>
        </div>
      )}

      {step === 'review' && (
        <div className="metric-card">
          <h2 className="text-xl font-semibold mb-4">Step 3: Review & Activate</h2>
          <div className="space-y-3 mb-6">
            <div className={`flex items-center gap-3 p-3 rounded-lg ${epicUrl ? 'bg-success-50' : 'bg-gray-50'}`}>
              <span className={epicUrl ? 'text-success-600' : 'text-gray-400'}>{epicUrl ? 'OK' : '--'}</span>
              <div>
                <p className="font-medium">Applied Epic SDK</p>
                <p className="text-sm text-gray-500">{epicUrl || 'Not configured — will use CSV imports'}</p>
              </div>
            </div>
            <div className={`flex items-center gap-3 p-3 rounded-lg ${gcpProject ? 'bg-success-50' : 'bg-gray-50'}`}>
              <span className={gcpProject ? 'text-success-600' : 'text-gray-400'}>{gcpProject ? 'OK' : '--'}</span>
              <div>
                <p className="font-medium">BigQuery Data Lake</p>
                <p className="text-sm text-gray-500">{gcpProject || 'Not configured — no policy validation'}</p>
              </div>
            </div>
            <div className="flex items-center gap-3 p-3 bg-primary-50 rounded-lg">
              <span className="text-primary-600">i</span>
              <div>
                <p className="font-medium">Trial Mode Active</p>
                <p className="text-sm text-gray-500">All runs start in trial mode. Zero Epic writes until you explicitly enable live mode per carrier.</p>
              </div>
            </div>
          </div>
          <div className="flex gap-3">
            <button onClick={goProduction} className="btn-primary">Activate Production Mode</button>
            <button onClick={() => setStep('bigquery')} className="btn-outline">Back</button>
          </div>
        </div>
      )}
    </div>
  )
}
