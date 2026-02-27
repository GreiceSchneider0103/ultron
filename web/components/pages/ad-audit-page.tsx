'use client'

import { FormEvent, useState } from 'react'

import { JsonView } from '@/components/pages/json-view'
import { Card, ErrorState } from '@/components/ui/primitives'
import { useApiAction } from '@/hooks/use-api-action'
import { compareVsCompetitors, getListingDetails, searchMarketplaceListings } from '@/services/market.service'
import { auditListing } from '@/services/seo.service'

export function AdAuditPage({ workspaceId }: { workspaceId: string }) {
  const [listingId, setListingId] = useState('')
  const [keyword, setKeyword] = useState('tenis corrida')
  const [marketplace, setMarketplace] = useState('mercadolivre')

  const myListingAction = useApiAction<Record<string, unknown>>()
  const competitorsAction = useApiAction<Record<string, unknown>>()
  const auditAction = useApiAction<Record<string, unknown>>()
  const compareAction = useApiAction<Record<string, unknown>>()

  async function onLoadMyListing(e: FormEvent) {
    e.preventDefault()
    if (!listingId) return
    await myListingAction.run(() => getListingDetails(workspaceId, listingId, marketplace))
  }

  async function onLoadCompetitors() {
    await competitorsAction.run(() =>
      searchMarketplaceListings(workspaceId, { marketplace, query: keyword, limit: 10, offset: 0 })
    )
  }

  async function onAudit() {
    await auditAction.run(() => auditListing(workspaceId, { listing_id: listingId, marketplace, keyword }))
  }

  async function onCompare() {
    await compareAction.run(() =>
      compareVsCompetitors(workspaceId, { listing_id: listingId, marketplace, keyword })
    )
  }

  return (
    <div className="space-y-5">
      <h1 className="text-3xl font-semibold">Auditoria de Anuncio</h1>
      <p className="text-sm text-slate-500">Compare seu anuncio com concorrentes e gere plano de acao.</p>

      <Card>
        <form onSubmit={onLoadMyListing} className="grid gap-3 md:grid-cols-4">
          <select
            value={marketplace}
            onChange={(e) => setMarketplace(e.target.value)}
            className="rounded-lg border border-border px-3 py-2 text-sm"
          >
            <option value="mercadolivre">Mercado Livre</option>
            <option value="magalu">Magalu</option>
          </select>
          <input
            value={listingId}
            onChange={(e) => setListingId(e.target.value)}
            className="rounded-lg border border-border px-3 py-2 text-sm"
            placeholder="ID do meu anuncio"
          />
          <input
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            className="rounded-lg border border-border px-3 py-2 text-sm"
            placeholder="Keyword principal"
          />
          <button className="rounded-lg bg-primary px-3 py-2 text-sm font-semibold text-white">Carregar anuncio</button>
        </form>
        <div className="mt-3 flex flex-wrap gap-2">
          <button type="button" className="rounded-lg border border-border px-3 py-2 text-sm" onClick={onLoadCompetitors}>
            Buscar concorrentes
          </button>
          <button type="button" className="rounded-lg border border-border px-3 py-2 text-sm" onClick={onAudit}>
            Rodar auditoria
          </button>
          <button type="button" className="rounded-lg border border-border px-3 py-2 text-sm" onClick={onCompare}>
            Comparar vs concorrentes
          </button>
        </div>
      </Card>

      <section className="grid grid-cols-1 gap-3 md:grid-cols-4">
        {[
          ['SEO', '62'],
          ['Conversao', '48'],
          ['Competitividade', '71'],
          ['Diferencial', '55'],
        ].map(([label, score]) => (
          <Card key={label} className="py-3">
            <p className="text-sm text-slate-600">{label}</p>
            <p className="mt-2 text-2xl font-semibold">{score}</p>
          </Card>
        ))}
      </section>

      {myListingAction.error ? <ErrorState message={myListingAction.error} /> : null}
      {competitorsAction.error ? <ErrorState message={competitorsAction.error} /> : null}
      {auditAction.error ? <ErrorState message={auditAction.error} /> : null}
      {compareAction.error ? <ErrorState message={compareAction.error} /> : null}

      {myListingAction.data ? (
        <Card>
          <h3 className="text-lg font-semibold">Meu anuncio</h3>
          <div className="mt-3">
            <JsonView value={myListingAction.data} />
          </div>
        </Card>
      ) : null}

      {competitorsAction.data ? (
        <Card>
          <h3 className="text-lg font-semibold">Concorrentes</h3>
          <div className="mt-3">
            <JsonView value={competitorsAction.data} />
          </div>
        </Card>
      ) : null}

      {auditAction.data ? (
        <Card>
          <h3 className="text-lg font-semibold">Auditoria</h3>
          <div className="mt-3 rounded-lg border border-border bg-slate-50 p-3">
            <p className="text-sm font-semibold">Checklist de auditoria</p>
            <ul className="mt-2 space-y-1 text-sm text-slate-700">
              <li>Titulo com keyword principal</li>
              <li>Titulo dentro do limite de caracteres</li>
              <li>Minimo de fotos atendido</li>
              <li>Atributos obrigatorios preenchidos</li>
            </ul>
          </div>
          <div className="mt-3">
            <JsonView value={auditAction.data} />
          </div>
        </Card>
      ) : null}

      {compareAction.data ? (
        <Card>
          <h3 className="text-lg font-semibold">Comparativo</h3>
          <div className="mt-3">
            <JsonView value={compareAction.data} />
          </div>
        </Card>
      ) : null}
    </div>
  )
}
