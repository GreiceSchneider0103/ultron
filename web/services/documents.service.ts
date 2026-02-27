'use client'

import { apiRequest, apiRequestMultipart } from '@/lib/api-client'

export async function parseDocument(workspaceId: string, file: File) {
  const form = new FormData()
  form.append('file', file)
  return apiRequestMultipart<Record<string, unknown>>({
    path: '/api/documents/upload',
    formData: form,
    workspaceId,
  })
}

export async function extractProductSpec(workspaceId: string, documentId: string) {
  return apiRequest<Record<string, unknown>>({
    path: `/api/documents/${documentId}/extract`,
    method: 'GET',
    workspaceId,
  })
}
