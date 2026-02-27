'use client'

import { apiRequest } from '@/lib/api-client'
import type { AlertEvent } from '@/lib/api-types'

export async function listAlerts(workspaceId: string) {
  return apiRequest<{ items: Array<Record<string, unknown>> }>({
    path: '/api/alerts',
    method: 'GET',
    workspaceId,
  })
}

export async function createAlert(workspaceId: string, payload: { name: string; condition: Record<string, unknown>; listing_id?: string; is_active?: boolean }) {
  return apiRequest<{ id: string }>({
    path: '/api/alerts',
    method: 'POST',
    workspaceId,
    body: payload,
  })
}

export async function listAlertEvents(workspaceId: string) {
  return apiRequest<{ items: AlertEvent[] }>({
    path: '/api/alerts/events',
    method: 'GET',
    workspaceId,
  })
}
