'use client'

import { FormEvent, useState } from 'react'

import { Card, EmptyState, ErrorState } from '@/components/ui/primitives'
import { useApiAction } from '@/hooks/use-api-action'
import { analyzeMarket, getListingDetails, searchMarketplaceListings } from '@/services/market.service'
import { extractKeywordsFromTopListings } from '@/services/seo.service'
import { JsonView } from '@/components/pages/json-view'

export function MarketResearchPage({ workspaceId }: { workspaceId: string }) {
  const [query, setQuery] = useState('tenis corrida')
  const [marketplace, setMarketplace] = useState('mercadolivre')
  const [selectedId, setSelectedId] = useState('')

  const searchAction = useApiAction<{ count: number; items: Array<Record<string, unknown>> }>()
  const detailAction = useApiAction<Record<string, unknown>>()
  const keywordsAction = useApiAction<Record<string, unknown>>()
  const analyzeAction = useApiAction<Record<string, unknown>>()

  async function onSearch(e: FormEvent) {
    e.preventDefault()
    await searchAction.run(async () => {
      const data = await searchMarketplaceListings(workspaceId, { marketplace, query, limit: 20, offset: 0 })
      if (data.items?.[0]?.id) setSelectedId(String(data.items[0].id))
      return { count: data.count, items: data.items as Array<Record<string, unknown>> }
    })
  }

  async function onLoadDetails() {
    if (!selectedId) return
    await detailAction.run(() => getListingDetails(workspaceId, selectedId, marketplace))
  }

  async function onKeywords() {
    await keywordsAction.run(() =>
      extractKeywordsFromTopListings(workspaceId, {
        marketplace,
        product_title: query,
        limit: 15,
      })
    )
  }

  async function onAnalyze() {
    await analyzeAction.run(() => analyzeMarket(workspaceId, { keyword: query, marketplace, limit: 20 }))
  }

  return (
    <div className="space-y-5">
      <h1 className="text-3xl font-semibold">Pesquisa de Mercado</h1>

      <Card>
        <form onSubmit={onSearch} className="grid gap-3 md:grid-cols-[160px_1fr_auto]">
          <select
            value={marketplace}
            onChange={(e) => setMarketplace(e.target.value)}
            className="rounded-lg border border-border bg-white px-3 py-2 text-sm"
          >
            <option value="mercadolivre">Mercado Livre</option>
            <option value="magalu">Magalu</option>
          </select>
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="rounded-lg border border-border bg-white px-3 py-2 text-sm"
            placeholder="Cole o link ou descreva o produto"
          />
          <button className="rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground" disabled={searchAction.loading}>
            {searchAction.loading ? 'Pesquisando...' : 'Pesquisar'}
          </button>
        </form>
      </Card>

      {searchAction.error ? <ErrorState message={searchAction.error} /> : null}

      {!searchAction.loading && (searchAction.data?.items?.length ?? 0) === 0 ? (
        <EmptyState title="Sem resultados" description="Ajuste os filtros e tente novamente." />
      ) : null}

      {searchAction.data?.items?.length ? (
        <Card>
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-semibold">Top anuncios ({searchAction.data.count})</h2>
            <div className="flex flex-wrap gap-2">
              <button type="button" className="rounded-md border border-border bg-white px-3 py-2 text-sm" onClick={onLoadDetails}>
                Detalhar anuncio
              </button>
              <button type="button" className="rounded-md border border-border bg-white px-3 py-2 text-sm" onClick={onKeywords}>
                Extrair keywords
              </button>
              <button type="button" className="rounded-md bg-primary px-3 py-2 text-sm font-semibold text-white" onClick={onAnalyze}>
                Insights e gaps
              </button>
            </div>
          </div>
          <div className="mt-3 overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead className="text-slate-500">
                <tr>
                  <th className="py-2 pr-3">ID</th>
                  <th className="py-2 pr-3">Titulo</th>
                  <th className="py-2 pr-3">Preco</th>
                </tr>
              </thead>
              <tbody>
                {searchAction.data.items.map((item, i) => (
                  <tr
                    key={`${String(item.id ?? i)}-${i}`}
                    className={`cursor-pointer border-t border-border ${selectedId === String(item.id ?? '') ? 'bg-slate-50' : ''}`}
                    onClick={() => setSelectedId(String(item.id ?? ''))}
                  >
                    <td className="py-2 pr-3">{String(item.id ?? '-')}</td>
                    <td className="py-2 pr-3">{String(item.title ?? '-')}</td>
                    <td className="py-2 pr-3">{String(item.price ?? '-')}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      ) : null}

      {detailAction.data ? (
        <Card>
          <h3 className="text-lg font-semibold">Detalhe do anuncio</h3>
          <div className="mt-3">
            <JsonView value={detailAction.data} />
          </div>
        </Card>
      ) : null}

      {keywordsAction.data ? (
        <Card>
          <h3 className="text-lg font-semibold">Keywords extraidas</h3>
          <div className="mt-3">
            <JsonView value={keywordsAction.data} />
          </div>
        </Card>
      ) : null}

      {analyzeAction.data ? (
        <Card>
          <h3 className="text-lg font-semibold">Analise e insights</h3>
          <div className="mt-3">
            <JsonView value={analyzeAction.data} />
          </div>
        </Card>
      ) : null}
    </div>
  )
}
