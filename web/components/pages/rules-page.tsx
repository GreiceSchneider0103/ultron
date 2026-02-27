'use client'

import { useCallback, useEffect, useState } from 'react'

import { Card, EmptyState, ErrorState } from '@/components/ui/primitives'
import { createClient } from '@/utils/supabase/client'

type RulesetRow = {
  id: string
  platform: string
  category_id: string | null
  version: number | null
  updated_at: string | null
}

export function RulesPage() {
  const [items, setItems] = useState<RulesetRow[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    const supabase = createClient()
    const { data, error } = await supabase
      .from('marketplace_rulesets')
      .select('id,platform,category_id,version,updated_at')
      .order('updated_at', { ascending: false })
      .limit(50)
    if (error) {
      setError(error.message)
    } else {
      setItems((data as RulesetRow[]) ?? [])
    }
    setLoading(false)
  }, [])

  useEffect(() => {
    const timeoutId = setTimeout(() => {
      load().catch(() => null)
    }, 0)
    return () => clearTimeout(timeoutId)
  }, [load])

  return (
    <div className="space-y-5">
      <h1 className="text-3xl font-semibold">Regras por Marketplace</h1>
      <p className="text-sm text-slate-500">Configuracao e validacao em tempo real</p>
      <Card>
        <div className="grid gap-3 md:grid-cols-3">
          <div className="flex gap-2">
            <button className="rounded-md border border-yellow-300 bg-yellow-100 px-3 py-2 text-sm">Mercado Livre</button>
            <button className="rounded-md border border-border bg-white px-3 py-2 text-sm">Magazine Luiza</button>
          </div>
          <select className="rounded-md border border-border px-3 py-2 text-sm">
            <option>Tenis Esportivos</option>
            <option>Eletronicos</option>
            <option>Casa e Decoracao</option>
          </select>
        </div>
      </Card>
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <Card>
          <h2 className="text-xl font-semibold">Regras - Mercado Livre</h2>
          <div className="mt-3 space-y-2 text-sm text-slate-700">
            <p>Limite de titulo: 60 caracteres</p>
            <p>Palavras proibidas: gratis, promocao, desconto, barato</p>
            <p>Atributos obrigatorios: marca, modelo, cor, material, tamanho</p>
            <p>Fotos minimas: 6</p>
          </div>
        </Card>
        <Card>
          <h2 className="text-xl font-semibold">Validacao em tempo real</h2>
          <div className="mt-3 space-y-2 text-sm">
            <div className="rounded-md bg-red-50 p-2 text-red-700">Comprimento do titulo: Critico</div>
            <div className="rounded-md bg-emerald-50 p-2 text-emerald-700">Palavras proibidas: OK</div>
            <div className="rounded-md bg-amber-50 p-2 text-amber-700">Atributos obrigatorios: Atencao</div>
            <div className="rounded-md bg-amber-50 p-2 text-amber-700">Quantidade de fotos: Atencao</div>
            <div className="rounded-md bg-emerald-50 p-2 text-emerald-700">Descricao: OK</div>
          </div>
        </Card>
      </div>
      {error ? <ErrorState message={error} onRetry={() => load()} /> : null}
      {loading ? <Card><p className="text-sm text-muted-foreground">Carregando regras...</p></Card> : null}
      {!loading && !error && items.length === 0 ? (
        <EmptyState title="Sem regras cadastradas" description="Adicione regras no painel Supabase ou via seed." />
      ) : null}
      {items.length > 0 ? (
        <Card>
          <table className="min-w-full text-left text-sm">
            <thead className="text-slate-500">
              <tr>
                <th className="py-2 pr-3">Platform</th>
                <th className="py-2 pr-3">Category</th>
                <th className="py-2 pr-3">Version</th>
                <th className="py-2 pr-3">Updated</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.id} className="border-t border-border">
                  <td className="py-2 pr-3">{item.platform}</td>
                  <td className="py-2 pr-3">{item.category_id ?? '-'}</td>
                  <td className="py-2 pr-3">{item.version ?? '-'}</td>
                  <td className="py-2 pr-3">{item.updated_at ? new Date(item.updated_at).toLocaleString('pt-BR') : '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      ) : null}
    </div>
  )
}
