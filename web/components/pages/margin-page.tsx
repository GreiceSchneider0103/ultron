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
    if (result?.report_id) setReportId(result.report_id)
  }

  async function onStatus() {
    if (!reportId) return
    await status.run(() => getReportStatus(workspaceId, reportId))
  }

  return (
    <div className="space-y-5">
      <h1 className="text-3xl font-semibold">Margem & Estrategia</h1>
      <p className="text-sm text-slate-500">Calcule precos e estrategias de competicao</p>
      <section className="grid grid-cols-1 gap-3 md:grid-cols-3">
        {[
          ['Margem liquida', '17.3%'],
          ['Lucro por unidade', `R$ ${(targetPrice - cost).toFixed(2)}`],
          ['Custo total', `R$ ${(cost + 18 + 5).toFixed(2)}`],
        ].map(([label, value]) => (
          <Card key={label} className="py-3">
            <p className="text-sm text-slate-600">{label}</p>
            <p className="mt-2 text-3xl font-semibold">{value}</p>
          </Card>
        ))}
      </section>
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[1.2fr_1fr]">
        <Card>
          <h2 className="text-xl font-semibold">Estrutura de custos</h2>
          <form className="mt-3 grid gap-3 md:grid-cols-2" onSubmit={onSubmit}>
            <input type="number" value={targetPrice} onChange={(e) => setTargetPrice(Number(e.target.value))} className="rounded-md border border-border px-3 py-2 text-sm md:col-span-2" placeholder="Preco de venda alvo (R$)" />
            <input type="number" value={cost} onChange={(e) => setCost(Number(e.target.value))} className="rounded-md border border-border px-3 py-2 text-sm" placeholder="CMV (R$)" />
            <input type="number" defaultValue={18} className="rounded-md border border-border px-3 py-2 text-sm" placeholder="Frete (R$)" />
            <input type="number" defaultValue={5} className="rounded-md border border-border px-3 py-2 text-sm" placeholder="Embalagem (R$)" />
            <input type="number" defaultValue={13} className="rounded-md border border-border px-3 py-2 text-sm" placeholder="Comissao (%)" />
            <input type="number" defaultValue={12} className="rounded-md border border-border px-3 py-2 text-sm" placeholder="Impostos (%)" />
            <input type="number" defaultValue={8} className="rounded-md border border-border px-3 py-2 text-sm" placeholder="Ads/Giro (%)" />
            <button className="rounded-md bg-primary px-3 py-2 text-sm font-semibold text-white md:col-span-2">Calcular estrategia</button>
          </form>
        </Card>
        <div className="space-y-4">
          <Card>
            <h2 className="text-xl font-semibold">Sugestao do agente IA</h2>
            <div className="mt-3 space-y-2 text-sm">
              <div className="rounded-lg bg-emerald-50 p-3 text-emerald-800">Competir por valor (margem recomendada 15-20%)</div>
              <div className="rounded-lg bg-amber-50 p-3 text-amber-800">Competir por preco (alto risco de margem baixa)</div>
            </div>
          </Card>
          <Card>
            <button type="button" onClick={onStatus} className="rounded-md border border-border px-3 py-2 text-sm">
              Consultar ultimo report
            </button>
          </Card>
        </div>
      </div>
      {create.error ? <ErrorState message={create.error} /> : null}
      {status.error ? <ErrorState message={status.error} /> : null}
      {create.data ? <Card><JsonView value={create.data} /></Card> : null}
      {status.data ? <Card><JsonView value={status.data} /></Card> : null}
    </div>
  )
}
