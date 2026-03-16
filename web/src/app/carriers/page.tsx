'use client'

import { useEffect, useState } from 'react'
import { api, CarrierConfig } from '@/lib/api'

export default function CarriersPage() {
  const [carriers, setCarriers] = useState<CarrierConfig[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.getCarriers()
      .then((data) => setCarriers(data.carriers))
      .catch(() => setCarriers([]))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="text-gray-500">Loading carriers...</div>

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Carrier Management</h1>
        <button className="btn-primary">Add Carrier</button>
      </div>

      <div className="grid grid-cols-3 gap-4">
        {carriers.map((c) => (
          <div key={c.carrier_slug} className="metric-card">
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-semibold">{c.display_name}</h3>
              <span className={c.mode === 'live' ? 'badge-success' : 'badge-warning'}>
                {c.mode}
              </span>
            </div>
            <div className="space-y-1 text-sm text-gray-500">
              <p>Policy field: <code className="text-xs">{c.policy_number_field}</code></p>
              <p>Premium field: <code className="text-xs">{c.premium_field}</code></p>
            </div>
            <div className="flex gap-2 mt-4">
              <button className="btn-outline text-xs py-1">Edit Mappings</button>
              <button className="btn-outline text-xs py-1">View Accuracy</button>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
