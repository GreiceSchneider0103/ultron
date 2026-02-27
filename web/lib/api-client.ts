'use client'

import { createClient } from '@/utils/supabase/client'

import type { ApiError } from '@/lib/api-types'

type ApiRequestParams = {
  path: string
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE'
  query?: Record<string, string | number | boolean | null | undefined>
  body?: unknown
  workspaceId?: string
  timeoutMs?: number
}

function toQueryString(query?: ApiRequestParams['query']) {
  if (!query) return ''
  const qs = new URLSearchParams()
  for (const [key, value] of Object.entries(query)) {
    if (value === undefined || value === null || value === '') continue
    qs.set(key, String(value))
  }
  const result = qs.toString()
  return result ? `?${result}` : ''
}

export async function apiRequest<T>({
  path,
  method = 'GET',
  query,
  body,
  workspaceId,
  timeoutMs = 15000,
}: ApiRequestParams): Promise<T> {
  const supabase = createClient()
  const {
    data: { session },
  } = await supabase.auth.getSession()

  if (!session?.access_token) {
    const err: ApiError = { message: 'Sessao expirada. Faca login novamente.' }
    throw err
  }

  const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), timeoutMs)

  try {
    const response = await fetch(`${baseUrl}${path}${toQueryString(query)}`, {
      method,
      signal: controller.signal,
      headers: {
        Authorization: `Bearer ${session.access_token}`,
        ...(workspaceId ? { 'X-Workspace-Id': workspaceId } : {}),
        ...(method !== 'GET' ? { 'Content-Type': 'application/json' } : {}),
      },
      body: method !== 'GET' ? JSON.stringify(body ?? {}) : undefined,
    })

    const text = await response.text()
    let parsed: unknown = {}
    if (text) {
      try {
        parsed = JSON.parse(text)
      } catch {
        parsed = { raw: text }
      }
    }

    if (!response.ok) {
      const err: ApiError = {
        message: (parsed as { detail?: string })?.detail || `Falha na API (${response.status})`,
        status: response.status,
        detail: parsed,
      }
      throw err
    }

    return parsed as T
  } finally {
    clearTimeout(timer)
  }
}
