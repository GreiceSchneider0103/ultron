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
