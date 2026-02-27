'use client'

import { createClient } from '@/utils/supabase/client'

export async function parseDocument(workspaceId: string, file: File) {
  const supabase = createClient()
  const {
    data: { session },
  } = await supabase.auth.getSession()
  if (!session?.access_token) {
    throw new Error('Sessao expirada.')
  }

  const form = new FormData()
  form.append('file', file)

  const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
  const response = await fetch(`${baseUrl}/api/documents/upload`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${session.access_token}`,
      'X-Workspace-Id': workspaceId,
    },
    body: form,
  })

  if (!response.ok) {
    const text = await response.text()
    throw new Error(text || `Falha no upload (${response.status})`)
  }

  return response.json()
}

export async function extractProductSpec(workspaceId: string, documentId: string) {
  const supabase = createClient()
  const {
    data: { session },
  } = await supabase.auth.getSession()
  if (!session?.access_token) {
    throw new Error('Sessao expirada.')
  }

  const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
  const response = await fetch(`${baseUrl}/api/documents/${documentId}/extract`, {
    headers: {
      Authorization: `Bearer ${session.access_token}`,
      'X-Workspace-Id': workspaceId,
    },
  })

  if (!response.ok) {
    const text = await response.text()
    throw new Error(text || `Falha no extract (${response.status})`)
  }

  return response.json()
}
