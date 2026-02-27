import { NextRequest, NextResponse } from 'next/server'

const METHODS = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH'] as const

async function forward(req: NextRequest, path: string[], method: string) {
  const backendBase = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
  const query = req.nextUrl.search || ''
  const targetUrl = `${backendBase}/${path.join('/')}${query}`

  const headers = new Headers()
  const auth = req.headers.get('authorization')
  const workspace = req.headers.get('x-workspace-id')
  const contentType = req.headers.get('content-type')
  if (auth) headers.set('authorization', auth)
  if (workspace) headers.set('x-workspace-id', workspace)
  if (contentType) headers.set('content-type', contentType)

  try {
    const response = await fetch(targetUrl, {
      method,
      headers,
      body: method === 'GET' || method === 'DELETE' ? undefined : await req.arrayBuffer(),
      cache: 'no-store',
    })
    const raw = await response.arrayBuffer()
    return new NextResponse(raw, {
      status: response.status,
      headers: {
        'content-type': response.headers.get('content-type') || 'application/json; charset=utf-8',
      },
    })
  } catch (error) {
    return NextResponse.json(
      {
        detail: 'Backend API indisponivel. Confirme se o uvicorn esta rodando em http://localhost:8000.',
        error: String(error),
      },
      { status: 503 }
    )
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
