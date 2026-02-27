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

async function getAccessToken() {
  const supabase = createClient()
  const {
    data: { session },
  } = await supabase.auth.getSession()
  return session?.access_token ?? null
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
  const token = await getAccessToken()
  if (!token) {
    const err: ApiError = { message: 'Sessao expirada. Faca login novamente.' }
    throw err
  }

  // sempre usar proxy relativo para evitar CORS
  const baseUrl = '/api/proxy'
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), timeoutMs)

  // Check for custom API URL in localStorage (client-side only)
  let customApiBase = ''
  if (typeof window !== 'undefined') {
    customApiBase = localStorage.getItem('ultron_api_base_url') || ''
  }

  try {
    const response = await fetch(`${baseUrl}${path}${toQueryString(query)}`, {
      method,
      signal: controller.signal,
      headers: {
        Authorization: `Bearer ${token}`,
        ...(customApiBase ? { 'X-Ultron-Api-Base': customApiBase } : {}),
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
      // Se o proxy retornou um erro padronizado, propaga-lo
      const err: ApiError = {
        message: (parsed as { message?: string })?.message || `Falha na API (${response.status})`,
        status: response.status,
        detail: parsed,
      }
      throw err
    }

    return parsed as T
  } catch (err) {
    // Normaliza e relança ApiError com message
    if (typeof err === 'object' && err !== null && 'message' in err) {
      throw err as ApiError
    }
    const message =
      err instanceof DOMException && err.name === 'AbortError'
        ? 'Tempo limite excedido ao chamar API.'
        : err instanceof Error
          ? `Falha de conexao com a API: ${err.message}`
          : 'Falha de conexao com a API.'
    throw { message } as ApiError
  } finally {
    clearTimeout(timer)
  }
}

export async function apiRequestMultipart<T>({
  path,
  formData,
  workspaceId,
  timeoutMs = 20000,
}: {
  path: string
  formData: FormData
  workspaceId?: string
  timeoutMs?: number
}): Promise<T> {
  const token = await getAccessToken()
  if (!token) {
    throw { message: 'Sessao expirada. Faca login novamente.' } as ApiError
  }

  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), timeoutMs)
  try {
    const response = await fetch(`/api/proxy${path}`, {
      method: 'POST',
      signal: controller.signal,
      headers: {
        Authorization: `Bearer ${token}`,
        ...(workspaceId ? { 'X-Workspace-Id': workspaceId } : {}),
      },
      body: formData,
    })
    const text = await response.text()
    const parsed = text ? JSON.parse(text) : {}
    if (!response.ok) {
      throw { message: (parsed as { message?: string })?.message || `Falha na API (${response.status})`, detail: parsed } as ApiError
    }
    return parsed as T
  } catch (err) {
    if (typeof err === 'object' && err !== null && 'message' in err) {
      throw err as ApiError
    }
    const message = err instanceof Error ? err.message : 'Falha de conexao com a API.'
    throw { message } as ApiError
  } finally {
    clearTimeout(timer)
  }
}
