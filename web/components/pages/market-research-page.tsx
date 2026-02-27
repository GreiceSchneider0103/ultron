'use client'

import { FormEvent, useMemo, useState } from 'react'

import { Card, EmptyState, ErrorState } from '@/components/ui/primitives'
import { useApiAction } from '@/hooks/use-api-action'
import { analyzeMarket, getListingDetails, searchMarketplaceListings } from '@/services/market.service'
import { extractKeywordsFromTopListings } from '@/services/seo.service'
import { JsonView } from '@/components/pages/json-view'
import { RetryButton } from '@/components/ui/retry-button'

export function MarketResearchPage({ workspaceId }: { workspaceId: string }) {
  const [mode, setMode] = useState<'link' | 'keyword' | 'manual'>('keyword')
  const [query, setQuery] = useState('tenis running masculino')
  const [linkInput, setLinkInput] = useState('')
  const [manualTitle, setManualTitle] = useState('')
  const [condition, setCondition] = useState('novo')
  const [category, setCategory] = useState('Esportes e Fitness')
  const [region, setRegion] = useState('nacional')
  const [minPrice, setMinPrice] = useState('')
  const [maxPrice, setMaxPrice] = useState('')
  const [freteEmbutido, setFreteEmbutido] = useState(true)
  const [apenasFull, setApenasFull] = useState(false)
  const [marketplace, setMarketplace] = useState('mercadolivre')
  const [selectedId, setSelectedId] = useState('')

  const searchAction = useApiAction<{ count: number; items: Array<Record<string, unknown>> }>()
  const detailAction = useApiAction<Record<string, unknown>>()
  const keywordsAction = useApiAction<Record<string, unknown>>()
  const analyzeAction = useApiAction<Record<string, unknown>>()

  const effectiveQuery = useMemo(() => {
    if (mode === 'link') return linkInput.trim()
    if (mode === 'manual') return manualTitle.trim()
    return query.trim()
  }, [linkInput, manualTitle, mode, query])

  async function performSearch() {
    if (!effectiveQuery) {
      searchAction.setError('Informe um link, keyword ou dados do produto.')
      return
    }

    await searchAction.run(async () => {
      const data = await searchMarketplaceListings(workspaceId, {
        marketplace,
        query: effectiveQuery,
        limit: 20,
        offset: 0,
      })
      if (data.items?.[0]?.id) setSelectedId(String(data.items[0].id))
      return { count: data.count, items: data.items as Array<Record<string, unknown>> }
    })
  }

  async function onSearch(e: FormEvent) {
    e.preventDefault()
    await performSearch()
  }

  async function onLoadDetails() {
    if (!selectedId) return
    await detailAction.run(() => getListingDetails(workspaceId, selectedId, marketplace))
  }

  async function onKeywords() {
    await keywordsAction.run(() =>
      extractKeywordsFromTopListings(workspaceId, {
        marketplace,
        product_title: effectiveQuery,
        limit: 15,
      })
    )
  }

  async function onAnalyze() {
    await analyzeAction.run(() => analyzeMarket(workspaceId, { keyword: effectiveQuery, marketplace, limit: 20 }))
  }

  return (
    <div className="space-y-5">
      <h1 className="text-3xl font-semibold">Pesquisa de Mercado</h1>
      <p className="text-sm text-slate-500">Analise a concorrencia e descubra oportunidades</p>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[2fr_1fr]">
        <Card>
          <form onSubmit={onSearch} className="space-y-3">
            <div className="grid grid-cols-1 gap-2 rounded-lg bg-slate-100 p-1 sm:grid-cols-3">
              {[
                ['link', 'Por link'],
                ['keyword', 'Por keyword'],
                ['manual', 'Dados manuais'],
              ].map(([value, label]) => (
                <button
                  key={value}
                  type="button"
                  onClick={() => setMode(value as 'link' | 'keyword' | 'manual')}
                  className={`rounded-md px-3 py-2 text-sm ${
                    mode === value ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-600'
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>

            <div className="grid gap-3 sm:grid-cols-2">
              <div>
                <label className="text-sm text-slate-600">Marketplace</label>
                <select
                  value={marketplace}
                  onChange={(e) => setMarketplace(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-border bg-white px-3 py-2 text-sm"
                >
                  <option value="mercadolivre">Mercado Livre</option>
                  <option value="magalu">Magalu</option>
                </select>
              </div>
              <div>
                <label className="text-sm text-slate-600">Condicao</label>
                <select
                  value={condition}
                  onChange={(e) => setCondition(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-border bg-white px-3 py-2 text-sm"
                >
                  <option value="novo">Novo</option>
                  <option value="usado">Usado</option>
                </select>
              </div>
            </div>

            {mode === 'link' ? (
              <div>
                <label className="text-sm text-slate-600">Link do anuncio</label>
                <input
                  value={linkInput}
                  onChange={(e) => setLinkInput(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-border bg-white px-3 py-2 text-sm"
                  placeholder="https://..."
                />
              </div>
            ) : null}

            {mode === 'keyword' ? (
              <div>
                <label className="text-sm text-slate-600">Palavra-chave</label>
                <input
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-border bg-white px-3 py-2 text-sm"
                  placeholder="tenis running masculino"
                />
              </div>
            ) : null}

            {mode === 'manual' ? (
              <div>
                <label className="text-sm text-slate-600">Dados do produto</label>
                <input
                  value={manualTitle}
                  onChange={(e) => setManualTitle(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-border bg-white px-3 py-2 text-sm"
                  placeholder="Nome/titulo do produto"
                />
              </div>
            ) : null}

            <div>
              <label className="text-sm text-slate-600">Categoria</label>
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="mt-1 w-full rounded-lg border border-border bg-white px-3 py-2 text-sm"
              >
                <option>Esportes e Fitness</option>
                <option>Eletronicos</option>
                <option>Casa e Decoracao</option>
                <option>Moda</option>
              </select>
            </div>

            <div className="grid gap-3 sm:grid-cols-[1fr_1fr_1fr]">
              <input
                value={minPrice}
                onChange={(e) => setMinPrice(e.target.value)}
                className="rounded-lg border border-border bg-white px-3 py-2 text-sm"
                placeholder="Preco min"
              />
              <input
                value={maxPrice}
                onChange={(e) => setMaxPrice(e.target.value)}
                className="rounded-lg border border-border bg-white px-3 py-2 text-sm"
                placeholder="Preco max"
              />
              <select
                value={region}
                onChange={(e) => setRegion(e.target.value)}
                className="rounded-lg border border-border bg-white px-3 py-2 text-sm"
              >
                <option value="nacional">Nacional</option>
                <option value="sudeste">Sudeste</option>
                <option value="sul">Sul</option>
                <option value="nordeste">Nordeste</option>
              </select>
            </div>

            <div className="flex flex-wrap gap-3 text-sm text-slate-700">
              <label className="inline-flex items-center gap-2">
                <input type="checkbox" checked={freteEmbutido} onChange={(e) => setFreteEmbutido(e.target.checked)} />
                Frete embutido
              </label>
              <label className="inline-flex items-center gap-2">
                <input type="checkbox" checked={apenasFull} onChange={(e) => setApenasFull(e.target.checked)} />
                Apenas Full
              </label>
            </div>

            <button
              className="w-full rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground"
              disabled={searchAction.loading}
            >
              {searchAction.loading ? 'Rodando analise...' : 'Rodar analise'}
            </button>
          </form>
        </Card>

        <Card>
          <h3 className="text-xl font-semibold">O que sera gerado</h3>
          <ul className="mt-3 space-y-2 text-sm text-slate-600">
            <li>Faixa de preco por seller</li>
            <li>Top 10 anuncios ranqueados</li>
            <li>Mapa de keywords</li>
            <li>Gaps de mercado</li>
            <li>Estruturas de titulo vencedoras</li>
            <li>Mapa de atributos</li>
            <li>Analise de frete</li>
            <li>Plano de acao SEO</li>
          </ul>
          <div className="mt-4 rounded-lg bg-blue-50 p-3 text-xs text-blue-800">
            Tempo estimado: 45-90 segundos dependendo da complexidade.
          </div>
        </Card>
      </div>

      {searchAction.error ? (
        <div className="space-y-2">
          <ErrorState message={searchAction.error} />
          <RetryButton onRetry={performSearch} loading={searchAction.loading} />
        </div>
      ) : null}

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
