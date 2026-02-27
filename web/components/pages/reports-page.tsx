'use client'

import { useState } from 'react'

import { JsonView } from '@/components/pages/json-view'
import { Card, ErrorState } from '@/components/ui/primitives'
import { useApiAction } from '@/hooks/use-api-action'
import { generateReport, getReportStatus } from '@/services/reports.service'

export function ReportsPage({ workspaceId }: { workspaceId: string }) {
  const [reportId, setReportId] = useState('')
  const create = useApiAction<{ report_id: string; status: string }>()
  const status = useApiAction<Record<string, unknown>>()

  async function onGenerate() {
    const payload = {
      cost: 100,
      min_margin_pct: 25,
      shipping_cost: 18,
      commission_pct: 14,
      lead_time_days: 7,
      target_price: 189,
      findings: { source: 'ui-report-generator' },
    }
    const result = await create.run(() => generateReport(workspaceId, payload))
    if (result?.report_id) setReportId(result.report_id)
  }

  async function onStatus() {
    if (!reportId) return
    await status.run(() => getReportStatus(workspaceId, reportId))
  }

  return (
    <div className="space-y-5">
      <h1 className="text-3xl font-semibold">Relatorios</h1>
      <p className="text-sm text-slate-500">Biblioteca de analises geradas</p>
      <Card>
        <h2 className="text-xl font-semibold">Modelos de relatorio</h2>
        <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-4">
          {['Auditoria completa', 'Pesquisa de mercado', 'Plano 10 acoes', 'Relatorio SEO'].map((item) => (
            <div key={item} className="rounded-lg border border-border bg-slate-50 p-3 text-sm text-slate-700">
              <p className="font-semibold">{item}</p>
              <p className="mt-1 text-xs text-slate-500">Template pronto para exportacao</p>
            </div>
          ))}
        </div>
      </Card>
      <Card>
        <h2 className="text-xl font-semibold">Gerar relatorio estrategico</h2>
        <div className="mt-3 flex flex-wrap gap-2">
          <button type="button" onClick={onGenerate} className="rounded-md bg-primary px-3 py-2 text-sm font-semibold text-white">
            Gerar relatorio
          </button>
          <input
            value={reportId}
            onChange={(e) => setReportId(e.target.value)}
            className="rounded-md border border-border px-3 py-2 text-sm"
            placeholder="Report ID"
          />
          <button type="button" onClick={onStatus} className="rounded-md border border-border px-3 py-2 text-sm">
            Consultar status
          </button>
        </div>
        {create.error ? <div className="mt-3"><ErrorState message={create.error} /></div> : null}
        {status.error ? <div className="mt-3"><ErrorState message={status.error} /></div> : null}
      </Card>
      {create.data ? (
        <Card>
          <h3 className="text-lg font-semibold">Criacao</h3>
          <div className="mt-3"><JsonView value={create.data} /></div>
        </Card>
      ) : null}
      {status.data ? (
        <Card>
          <h3 className="text-lg font-semibold">Status</h3>
          <div className="mt-3"><JsonView value={status.data} /></div>
        </Card>
      ) : null}
    </div>
  )
}
