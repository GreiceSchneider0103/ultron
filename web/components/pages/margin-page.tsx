'use client'

import { FormEvent, useState } from 'react'

import { JsonView } from '@/components/pages/json-view'
import { Card, ErrorState } from '@/components/ui/primitives'
import { useApiAction } from '@/hooks/use-api-action'
import { generateReport, getReportStatus } from '@/services/reports.service'

export function MarginPage({ workspaceId }: { workspaceId: string }) {
  const [cost, setCost] = useState(100)
  const [targetPrice, setTargetPrice] = useState(190)
  const [reportId, setReportId] = useState('')
  const create = useApiAction<{ report_id: string; status: string }>()
  const status = useApiAction<Record<string, unknown>>()

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    const result = await create.run(() =>
      generateReport(workspaceId, {
        cost,
        min_margin_pct: 25,
        shipping_cost: 18,
        commission_pct: 14,
        lead_time_days: 7,
        target_price: targetPrice,
        findings: { module: 'margem' },
      })
    )
    setReportId(result.report_id)
  }

  async function onStatus() {
    if (!reportId) return
    await status.run(() => getReportStatus(workspaceId, reportId))
  }

  return (
    <div className="space-y-5">
      <h1 className="text-3xl font-semibold">Margem & Estrategia</h1>
      <Card>
        <form className="grid gap-3 md:grid-cols-4" onSubmit={onSubmit}>
          <input type="number" value={cost} onChange={(e) => setCost(Number(e.target.value))} className="rounded-md border border-border px-3 py-2 text-sm" placeholder="Custo" />
          <input type="number" value={targetPrice} onChange={(e) => setTargetPrice(Number(e.target.value))} className="rounded-md border border-border px-3 py-2 text-sm" placeholder="Preco alvo" />
          <button className="rounded-md bg-primary px-3 py-2 text-sm font-semibold text-white">Calcular estrategia</button>
          <button type="button" onClick={onStatus} className="rounded-md border border-border px-3 py-2 text-sm">
            Consultar ultimo report
          </button>
        </form>
      </Card>
      {create.error ? <ErrorState message={create.error} /> : null}
      {status.error ? <ErrorState message={status.error} /> : null}
      {create.data ? <Card><JsonView value={create.data} /></Card> : null}
      {status.data ? <Card><JsonView value={status.data} /></Card> : null}
    </div>
  )
}
