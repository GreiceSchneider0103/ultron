'use client'

import { apiRequest } from '@/lib/api-client'

export async function analyzeImages(workspaceId: string, payload: { image_urls: string[] }) {
  return apiRequest<Record<string, unknown>>({
    path: '/api/v2/images/analyze',
    method: 'POST',
    workspaceId,
    body: payload,
  })
}

export async function layoutAudit(workspaceId: string, payload: { image_url: string }) {
  return apiRequest<Record<string, unknown>>({
    path: '/api/v2/images/layout-audit',
    method: 'POST',
    workspaceId,
    body: payload,
  })
}
