'use client'

import { useEffect, useState } from 'react'

import { apiRequest } from '@/lib/api-client'

export function ApiStatus() {
  const [status, setStatus] = useState<'online' | 'offline' | 'checking'>('checking')

  const checkHealth = async () => {
    try {
      // Calls /api/proxy/health (apiRequest prepends /api/proxy)
      await apiRequest({ path: '/health', timeoutMs: 3000 })
      setStatus('online')
    } catch {
      setStatus('offline')
    }
  }

  useEffect(() => {
    const timeoutId = setTimeout(() => {
      void checkHealth()
    }, 0)
    const interval = setInterval(checkHealth, 15000)
    return () => {
      clearTimeout(timeoutId)
      clearInterval(interval)
    }
  }, [])

  if (status === 'online') {
    return (
      <div className="flex items-center gap-2 rounded-full bg-green-100 px-3 py-1 text-xs font-medium text-green-800">
        <span className="relative flex h-2 w-2">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-green-400 opacity-75"></span>
          <span className="relative inline-flex h-2 w-2 rounded-full bg-green-500"></span>
        </span>
        Online
      </div>
    )
  }

  if (status === 'offline') {
    return (
      <button
        type="button"
        onClick={checkHealth}
        className="flex items-center gap-2 rounded-full bg-red-100 px-3 py-1 text-xs font-medium text-red-800 hover:bg-red-200"
      >
        <span className="h-2 w-2 rounded-full bg-red-500"></span>
        Offline (Recarregar)
      </button>
    )
  }

  return (
    <div className="flex items-center gap-2 rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-600">
      <span className="h-2 w-2 rounded-full bg-slate-400"></span>
      Checking...
    </div>
  )
}
