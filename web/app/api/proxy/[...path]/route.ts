import { NextRequest, NextResponse } from 'next/server'

const METHODS = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH'] as const

async function forward(req: NextRequest, path: string[], method: string) {
  // Check for custom API base in header (from settings)
  const customBase = req.headers.get('x-ultron-api-base')
  let validCustomBase = null
  if (customBase && (customBase.startsWith('http://') || customBase.startsWith('https://'))) {
    validCustomBase = customBase.replace(/\/$/, '')
  }

  // Seleção de base URL (ordem de prioridade)
  const candidates = [
    validCustomBase,
    process.env.API_URL,
    process.env.NEXT_PUBLIC_API_URL,
    'http://127.0.0.1:8000',
    'http://localhost:8000',
  ].filter(Boolean) as string[]

  const target = candidates[0] // primeiro válido

  const query = req.nextUrl.search || ''
  const targetUrl = `${target.replace(/\/$/, '')}/${path.join('/')}${query}`

  const headers = new Headers()
  const auth = req.headers.get('authorization')
  const workspace = req.headers.get('x-workspace-id')
  const contentType = req.headers.get('content-type')

  // copiar apenas headers seguros
  if (auth) headers.set('authorization', auth)
  if (workspace) headers.set('x-workspace-id', workspace)
  if (contentType) headers.set('content-type', contentType)

  const controller = new AbortController()
  const timeoutMs = 15000
  const timeout = setTimeout(() => controller.abort(), timeoutMs)

  try {
    const response = await fetch(targetUrl, {
      method,
      headers,
      body: method === 'GET' || method === 'DELETE' ? undefined : await req.arrayBuffer(),
      cache: 'no-store',
      signal: controller.signal,
    })

    const raw = await response.arrayBuffer()
    const contentTypeResp = response.headers.get('content-type') || 'application/json; charset=utf-8'

    // repassa resposta original
    const headersOut: Record<string, string> = {
      'content-type': contentTypeResp,
    }
    // Include any cache-control or other safe headers if present
    const cacheControl = response.headers.get('cache-control')
    if (cacheControl) headersOut['cache-control'] = cacheControl

    return new NextResponse(raw, {
      status: response.status,
      headers: headersOut,
    })
  } catch (err: unknown) {
    // Normalize error message
    const reason = err instanceof Error ? err.message : String(err)
    const proxyPath = `/${path.join('/')}`
    console.error('[api-proxy] forward error', { target, path: proxyPath, reason, candidates })

    const message =
      reason.indexOf('ECONNREFUSED') !== -1
        ? `Connection refused to backend ${target}`
        : reason === 'The operation was aborted.' || reason === 'AbortError'
        ? `Timeout (${timeoutMs}ms) contacting backend ${target}`
        : `Failed to contact backend ${target}: ${reason}`

    const body = {
      error: 'backend_unavailable',
      message,
      target,
      path: proxyPath,
      method,
      candidates,
      reason,
      hint: 'Set API_URL (or NEXT_PUBLIC_API_URL) to the backend origin, e.g. http://127.0.0.1:8000',
    }

    return NextResponse.json(body, { status: 503 })
  } finally {
    clearTimeout(timeout)
  }
}

export async function GET(req: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  const { path } = await context.params
  return forward(req, path, METHODS[0])
}

export async function POST(req: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  const { path } = await context.params
  return forward(req, path, METHODS[1])
}

export async function PUT(req: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  const { path } = await context.params
  return forward(req, path, METHODS[2])
}

export async function DELETE(req: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  const { path } = await context.params
  return forward(req, path, METHODS[3])
}

export async function PATCH(req: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  const { path } = await context.params
  return forward(req, path, METHODS[4])
}
