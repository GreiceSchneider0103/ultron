'use client'

import { apiRequest } from '@/lib/api-client'
import type { ListingNormalized } from '@/lib/api-types'

export async function searchMarketplaceListings(workspaceId: string, params: { marketplace: string; query: string; limit?: number; offset?: number }) {
  return apiRequest<{ workspace_id: string; count: number; items: ListingNormalized[] }>({
    path: '/api/market-research/search',
    method: 'GET',
    workspaceId,
    query: params,
  })
}

export async function getListingDetails(workspaceId: string, productId: string, marketplace: string) {
  return apiRequest<{ workspace_id: string; normalized: ListingNormalized }>({
    path: `/api/market-research/product/${productId}`,
    method: 'GET',
    workspaceId,
    query: { marketplace },
  })
}

export async function compareVsCompetitors(workspaceId: string, payload: Record<string, unknown>) {
  return apiRequest<Record<string, unknown>>({
    path: '/compare',
    method: 'POST',
    workspaceId,
    body: payload,
  })
}

export async function analyzeMarket(workspaceId: string, payload: { keyword: string; marketplace: string; limit?: number }) {
  return apiRequest<Record<string, unknown>>({
    path: '/api/market-research/analyze',
    method: 'POST',
    workspaceId,
    body: payload,
  })
}
