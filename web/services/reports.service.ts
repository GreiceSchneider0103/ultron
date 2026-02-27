'use client'

import { apiRequest } from '@/lib/api-client'

export async function generateReport(workspaceId: string, payload: Record<string, unknown>) {
  return apiRequest<{ report_id: string; status: string }>({
    path: '/api/reports/generate',
    method: 'POST',
    workspaceId,
    body: payload,
  })
}

export async function getReportStatus(workspaceId: string, reportId: string) {
  return apiRequest<Record<string, unknown>>({
    path: `/api/reports/${reportId}/status`,
    method: 'GET',
    workspaceId,
  })
}

export async function getDashboardInsights(workspaceId: string) {
  return apiRequest<Record<string, unknown>>({
    path: '/api/reports/v2/insights',
    method: 'GET',
    workspaceId,
  })
}
