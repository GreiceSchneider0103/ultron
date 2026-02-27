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
    setReportId(result.report_id)
  }

  async function onStatus() {
    if (!reportId) return
    await status.run(() => getReportStatus(workspaceId, reportId))
  }

  return (
    <div className="space-y-5">
      <h1 className="text-3xl font-semibold">Relatorios</h1>
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
