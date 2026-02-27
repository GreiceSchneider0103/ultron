'use client'

import { useState } from 'react'

import { createClient } from '@/utils/supabase/client'

type ApiConsoleProps = {
  title: string
  description: string
  workspaceId: string
  defaultPath: string
  defaultMethod?: 'GET' | 'POST' | 'PUT' | 'DELETE'
  defaultQuery?: Record<string, string | number | boolean>
  defaultBody?: unknown
  lockPath?: boolean
}

function safeStringify(value: unknown) {
  return JSON.stringify(value, null, 2)
}

export default function ApiConsole({
  title,
  description,
  workspaceId,
  defaultPath,
  defaultMethod = 'GET',
  defaultQuery = {},
  defaultBody = {},
  lockPath = true,
}: ApiConsoleProps) {
  const [method, setMethod] = useState<'GET' | 'POST' | 'PUT' | 'DELETE'>(defaultMethod)
  const [path, setPath] = useState(defaultPath)
  const [queryText, setQueryText] = useState(safeStringify(defaultQuery))
  const [bodyText, setBodyText] = useState(safeStringify(defaultBody))
  const [loading, setLoading] = useState(false)
  const [statusCode, setStatusCode] = useState<number | null>(null)
  const [result, setResult] = useState('')
  const [error, setError] = useState('')

  async function runRequest() {
    setLoading(true)
    setError('')
    setResult('')
    setStatusCode(null)

    try {
      const parsedQuery = queryText.trim() ? JSON.parse(queryText) : {}
      const parsedBody = bodyText.trim() ? JSON.parse(bodyText) : {}

      const supabase = createClient()
      const {
        data: { session },
      } = await supabase.auth.getSession()

      if (!session?.access_token) {
        throw new Error('Sessao expirada. Faca login novamente.')
      }

      const query = new URLSearchParams()
      Object.entries(parsedQuery as Record<string, unknown>).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== '') {
          query.set(key, String(value))
        }
      })

      const normalizedPath = path.startsWith('/') ? path : `/${path}`
      const url = `/api/proxy${normalizedPath}${query.toString() ? `?${query.toString()}` : ''}`

      const response = await fetch(url, {
        method,
        headers: {
          Authorization: `Bearer ${session.access_token}`,
          'X-Workspace-Id': workspaceId,
          ...(method !== 'GET' ? { 'Content-Type': 'application/json' } : {}),
        },
        body: method !== 'GET' ? JSON.stringify(parsedBody) : undefined,
      })

      setStatusCode(response.status)

      const text = await response.text()
      if (!response.ok) {
        try {
          const parsed = JSON.parse(text) as Record<string, unknown>
          throw new Error(
            String(parsed.message || parsed.error || `Falha no endpoint (${response.status})`)
          )
        } catch {
          throw new Error(text || `Falha no endpoint (${response.status})`)
        }
      }
      try {
        setResult(safeStringify(JSON.parse(text)))
      } catch {
        setResult(text)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Falha ao chamar endpoint')
    } finally {
      setLoading(false)
    }
  }

  return (
    <section className="rounded-2xl border border-slate-800 bg-slate-900 p-5">
      <div className="mb-4">
        <h2 className="text-xl font-semibold text-slate-100">{title}</h2>
        <p className="mt-1 text-sm text-slate-400">{description}</p>
      </div>

      <div className="grid gap-4">
        <div className="grid gap-3 md:grid-cols-[120px_1fr]">
          <select
            value={method}
            onChange={(e) => setMethod(e.target.value as 'GET' | 'POST' | 'PUT' | 'DELETE')}
            className="rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100"
          >
            <option>GET</option>
            <option>POST</option>
            <option>PUT</option>
            <option>DELETE</option>
          </select>
          <input
            value={path}
            onChange={(e) => setPath(e.target.value)}
            disabled={lockPath}
            className="rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100 disabled:cursor-not-allowed disabled:opacity-70"
          />
        </div>

        <label className="grid gap-2 text-sm text-slate-300">
          Query params (JSON)
          <textarea
            value={queryText}
            onChange={(e) => setQueryText(e.target.value)}
            rows={6}
            className="rounded-md border border-slate-700 bg-slate-950 px-3 py-2 font-mono text-xs text-slate-100"
          />
        </label>

        {method !== 'GET' && (
          <label className="grid gap-2 text-sm text-slate-300">
            Body (JSON)
            <textarea
              value={bodyText}
              onChange={(e) => setBodyText(e.target.value)}
              rows={8}
              className="rounded-md border border-slate-700 bg-slate-950 px-3 py-2 font-mono text-xs text-slate-100"
            />
          </label>
        )}

        <button
          type="button"
          onClick={runRequest}
          disabled={loading}
          className="w-fit rounded-md bg-cyan-500 px-4 py-2 text-sm font-semibold text-slate-950 hover:bg-cyan-400 disabled:opacity-60"
        >
          {loading ? 'Executando...' : 'Executar endpoint'}
        </button>

        {statusCode !== null && (
          <p className="text-sm text-slate-300">
            Status: <span className="font-semibold">{statusCode}</span>
          </p>
        )}

        {error && <p className="text-sm text-red-300">{error}</p>}

        {result && (
          <pre className="overflow-x-auto rounded-md border border-slate-800 bg-slate-950 p-3 text-xs text-slate-100">
            {result}
          </pre>
        )}
      </div>
    </section>
  )
}
