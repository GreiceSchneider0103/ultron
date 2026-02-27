'use client'

import { apiRequest } from '@/lib/api-client'

export async function getMyListings(workspaceId: string, params: { marketplace: string; limit?: number; offset?: number }) {
  return apiRequest<{ items: Array<Record<string, unknown>>; count: number }>({
    path: '/api/market-research/my-listings',
    method: 'GET',
    workspaceId,
    query: params,
  })
}
