'use client'

import { apiRequest } from '@/lib/api-client'

export async function extractKeywordsFromTopListings(
  workspaceId: string,
  params: { marketplace: string; product_title: string; limit?: number; category?: string }
) {
  return apiRequest<{ keywords: string[] }>({
    path: '/api/seo/keywords',
    method: 'GET',
    workspaceId,
    query: params,
  })
}

export async function suggestTitleVariants(
  workspaceId: string,
  payload: { marketplace: string; product_title: string; limit?: number; category?: string }
) {
  return apiRequest<{ titles: string[] }>({
    path: '/api/seo/optimize-title',
    method: 'POST',
    workspaceId,
    body: payload,
  })
}

export async function validateTitle(workspaceId: string, payload: { marketplace: string; product_title: string; limit?: number }) {
  return apiRequest<Record<string, unknown>>({
    path: '/validate-title',
    method: 'POST',
    workspaceId,
    body: payload,
  })
}

export async function auditListing(
  workspaceId: string,
  payload: { listing_id: string; marketplace: string; keyword?: string }
) {
  return apiRequest<Record<string, unknown>>({
    path: '/api/seo/analyze-listing',
    method: 'POST',
    workspaceId,
    body: payload,
  })
}
