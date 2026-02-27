export type ApiError = {
  message: string
  status?: number
  detail?: unknown
}

export type ListingNormalized = {
  id?: string
  title?: string
  price?: number
  final_price_estimate?: number
  seller?: { id?: string; nickname?: string; reputation?: string }
  [key: string]: unknown
}

export type MarketDashboard = {
  [key: string]: unknown
}

export type AuditReport = {
  scores?: Record<string, number>
  recommendations?: Array<string | { title?: string; description?: string }>
  [key: string]: unknown
}

export type SeoInsights = {
  keywords?: string[]
  titles?: string[]
  [key: string]: unknown
}

export type AlertEvent = {
  id: string
  status?: string
  triggered_at?: string
  event_data?: Record<string, unknown>
}
