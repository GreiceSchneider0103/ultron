'use client'

import Link from 'next/link'
import { useEffect } from 'react'

import { useApiAction } from '@/hooks/use-api-action'
import { getDashboardInsights } from '@/services/reports.service'
import { Badge, Card, EmptyState, ErrorState, Skeleton } from '@/components/ui/primitives'

export function DashboardHome({ workspaceId }: { workspaceId: string }) {
  const insights = useApiAction<Record<string, unknown>>()

  useEffect(() => {
    insights.run(() => getDashboardInsights(workspaceId)).catch(() => null)
  }, [insights, workspaceId])

  const metrics = (insights.data?.metrics as Array<{ label: string; value: number; delta?: number; tone?: string }>) || []
  const actions = (insights.data?.next_actions as Array<{ title: string; href: string }>) || []

  return (
    <div className="space-y-5">
      <h1 className="text-3xl font-semibold">Dashboard</h1>

      {insights.loading && (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Card key={i}>
              <Skeleton className="h-4 w-24" />
              <Skeleton className="mt-3 h-8 w-16" />
            </Card>
          ))}
        </div>
      )}

      {insights.error ? <ErrorState message={insights.error} onRetry={() => insights.run(() => getDashboardInsights(workspaceId)).catch(() => null)} /> : null}

      {!insights.loading && !insights.error && metrics.length === 0 ? (
        <EmptyState title="Sem indicadores ainda" description="Execute uma pesquisa ou auditoria para alimentar o dashboard." />
      ) : null}

      {metrics.length > 0 && (
        <section className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
          {metrics.map((m) => (
            <Card key={m.label}>
              <div className="flex items-start justify-between">
                <p className="text-sm text-muted-foreground">{m.label}</p>
                <Badge tone={(m.tone as 'neutral' | 'success' | 'warning' | 'danger') || 'neutral'}>
                  {m.delta ? `${m.delta > 0 ? '+' : ''}${m.delta}` : '0'}
                </Badge>
              </div>
              <p className="mt-2 text-3xl font-semibold">{m.value}</p>
            </Card>
          ))}
        </section>
      )}

      <section className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <Card>
          <h2 className="text-xl font-semibold">Proximas 10 acoes</h2>
          {actions.length === 0 ? (
            <p className="mt-3 text-sm text-muted-foreground">Nenhuma acao gerada ainda.</p>
          ) : (
            <ul className="mt-3 space-y-2">
              {actions.map((a, i) => (
                <li key={`${a.title}-${i}`} className="flex items-center justify-between rounded-lg border border-border bg-slate-50 px-3 py-2">
                  <span className="text-sm text-slate-700">{a.title}</span>
                  <Link href={a.href} className="text-sm font-semibold text-primary hover:underline">
                    Abrir
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card>
          <h2 className="text-xl font-semibold">Atalhos rapidos</h2>
          <div className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-2">
            {[
              { href: '/pesquisa', label: 'Pesquisar por link' },
              { href: '/auditoria', label: 'Rodar auditoria' },
              { href: '/gerar-anuncio', label: 'Gerar anuncio' },
              { href: '/monitoramento', label: 'Criar alerta' },
            ].map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className="rounded-lg border border-border bg-white px-3 py-2 text-sm text-slate-700 hover:border-primary hover:text-primary"
              >
                {item.label}
              </Link>
            ))}
          </div>
        </Card>
      </section>
    </div>
  )
}
