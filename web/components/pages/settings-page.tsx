'use client'

import { FormEvent, useCallback, useEffect, useState } from 'react'

import { Card, ErrorState } from '@/components/ui/primitives'
import { getWorkspaceSettings, updateWorkspaceName } from '@/services/settings.service'

export function SettingsPage({ workspaceId }: { workspaceId: string }) {
  const [name, setName] = useState('')
  const [plan, setPlan] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const data = await getWorkspaceSettings(workspaceId)
      setName(data?.name ?? '')
      setPlan(data?.plan ?? '')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro ao carregar')
    } finally {
      setLoading(false)
    }
  }, [workspaceId])

  useEffect(() => {
    const timeoutId = setTimeout(() => {
      load().catch(() => null)
    }, 0)
    return () => clearTimeout(timeoutId)
  }, [load])

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setError('')
    try {
      const data = await updateWorkspaceName(workspaceId, name)
      setName(data.name ?? name)
      setPlan(data.plan ?? plan)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Falha ao salvar')
    }
  }

  return (
    <div className="space-y-5">
      <h1 className="text-3xl font-semibold">Configuracoes</h1>
      {error ? <ErrorState message={error} onRetry={() => load()} /> : null}
      <Card>
        {loading ? (
          <p className="text-sm text-muted-foreground">Carregando...</p>
        ) : (
          <form onSubmit={onSubmit} className="grid gap-3 md:max-w-xl">
            <label className="text-sm text-slate-600">Nome do workspace</label>
            <input value={name} onChange={(e) => setName(e.target.value)} className="rounded-md border border-border px-3 py-2 text-sm" />
            <label className="text-sm text-slate-600">Plano</label>
            <input value={plan} disabled className="rounded-md border border-border bg-slate-50 px-3 py-2 text-sm" />
            <button className="w-fit rounded-md bg-primary px-3 py-2 text-sm font-semibold text-white">Salvar</button>
          </form>
        )}
      </Card>
    </div>
  )
}
