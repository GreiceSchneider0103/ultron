'use client'

import { useCallback, useEffect, useState } from 'react'

import { JsonView } from '@/components/pages/json-view'
import { Card, ErrorState } from '@/components/ui/primitives'
import { useApiAction } from '@/hooks/use-api-action'
import { createAlert, listAlertEvents, listAlerts } from '@/services/alerts.service'

export function MonitoringPage({ workspaceId }: { workspaceId: string }) {
  const [alertName, setAlertName] = useState('Queda brusca de preco')

  const rules = useApiAction<{ items: Array<Record<string, unknown>> }>()
  const events = useApiAction<{ items: Array<Record<string, unknown>> }>()
  const create = useApiAction<{ id: string }>()
  const runRules = rules.run
  const runEvents = events.run

  const loadAll = useCallback(async () => {
    await Promise.all([runRules(() => listAlerts(workspaceId)), runEvents(() => listAlertEvents(workspaceId))])
  }, [runRules, runEvents, workspaceId])

  useEffect(() => {
    const timeoutId = setTimeout(() => {
      loadAll().catch(() => null)
    }, 0)
    return () => clearTimeout(timeoutId)
  }, [loadAll])

  async function onCreate() {
    await create.run(() =>
      createAlert(workspaceId, {
        name: alertName,
        condition: { field: 'price', op: 'lt', value: 99.9 },
        is_active: true,
      })
    )
    await loadAll()
  }

  return (
    <div className="space-y-5">
      <h1 className="text-3xl font-semibold">Monitoramento & Alertas</h1>
      <div className="flex flex-wrap gap-2">
        <button className="rounded-md border border-border bg-white px-3 py-2 text-sm">Configurar alertas</button>
        <button className="rounded-md bg-primary px-3 py-2 text-sm font-semibold text-white">Adicionar anuncio</button>
      </div>

      <section className="grid grid-cols-1 gap-3 md:grid-cols-4">
        {[
          ['Anuncios monitorados', String((rules.data?.items?.length ?? 0) + 16)],
          ['Alertas ativos', String(rules.data?.items?.length ?? 0)],
          ['Mudancas hoje', String(events.data?.items?.length ?? 0)],
          ['Concorrentes rastreados', '4'],
        ].map(([label, value]) => (
          <Card key={label} className="py-3">
            <p className="text-sm text-slate-600">{label}</p>
            <p className="mt-2 text-2xl font-semibold">{value}</p>
          </Card>
        ))}
      </section>

      <Card>
        <h2 className="text-xl font-semibold">Criar alerta</h2>
        <div className="mt-3 flex flex-wrap gap-2">
          <input
            value={alertName}
            onChange={(e) => setAlertName(e.target.value)}
            className="min-w-[280px] rounded-md border border-border px-3 py-2 text-sm"
          />
          <button type="button" onClick={onCreate} className="rounded-md bg-primary px-3 py-2 text-sm font-semibold text-white">
            Criar
          </button>
        </div>
        {create.error ? <div className="mt-3"><ErrorState message={create.error} /></div> : null}
      </Card>

      <Card>
        <h2 className="text-xl font-semibold">Regras ativas</h2>
        {rules.error ? <div className="mt-3"><ErrorState message={rules.error} onRetry={() => loadAll()} /></div> : null}
        <div className="mt-3">
          <JsonView value={rules.data ?? { items: [] }} />
        </div>
      </Card>

      <Card>
        <h2 className="text-xl font-semibold">Historico de eventos</h2>
        {events.error ? <div className="mt-3"><ErrorState message={events.error} onRetry={() => loadAll()} /></div> : null}
        <div className="mt-3">
          <JsonView value={events.data ?? { items: [] }} />
        </div>
      </Card>
    </div>
  )
}
