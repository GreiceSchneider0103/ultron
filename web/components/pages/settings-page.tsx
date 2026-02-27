'use client'

import { FormEvent, useCallback, useEffect, useState } from 'react'

import { Card, ErrorState } from '@/components/ui/primitives'
import { getWorkspaceSettings, updateWorkspaceName } from '@/services/settings.service'
import { useToast } from '@/components/ui/toast/use-toast'
import { apiRequest } from '@/lib/api-client'

export function SettingsPage({ workspaceId }: { workspaceId: string }) {
  const [name, setName] = useState('')
  const [plan, setPlan] = useState('')
  const [apiUrl, setApiUrl] = useState('')
  const [testStatus, setTestStatus] = useState<'idle' | 'testing' | 'success' | 'error'>('idle')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const toast = useToast()

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const data = await getWorkspaceSettings(workspaceId)
      setName(data?.name ?? '')
      setPlan(data?.plan ?? '')
      const storedUrl = localStorage.getItem('ultron_api_base_url')
      if (storedUrl) setApiUrl(storedUrl)
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
      toast.success('Configuracoes salvas com sucesso')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Falha ao salvar')
      toast.error('Erro ao salvar configuracoes')
    }
  }

  function onSaveApiUrl() {
    if (!apiUrl) {
      localStorage.removeItem('ultron_api_base_url')
      toast.info('URL da API restaurada para o padrao')
      return
    }
    let cleanUrl = apiUrl.trim().replace(/\/$/, '')
    if (!cleanUrl.startsWith('http')) {
      cleanUrl = `http://${cleanUrl}`
    }
    setApiUrl(cleanUrl)
    localStorage.setItem('ultron_api_base_url', cleanUrl)
    toast.success('URL da API atualizada')
  }

  async function onTestConnection() {
    setTestStatus('testing')
    try {
      // We can't easily force the header in apiRequest without saving, 
      // so we save temporarily or rely on the user saving first.
      // Better UX: Save first then test, or just test the saved value.
      // Let's assume user saved or we use the saved value.
      if (apiUrl !== localStorage.getItem('ultron_api_base_url')) {
        onSaveApiUrl()
      }
      
      await apiRequest({ path: '/health', timeoutMs: 3000 })
      setTestStatus('success')
      toast.success('Conexao com API estabelecida!')
    } catch {
      setTestStatus('error')
      toast.error('Falha ao conectar com a API')
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

      <Card>
        <h2 className="text-xl font-semibold">Conexao com Backend</h2>
        <p className="text-sm text-slate-500">Configure o endereco da API (ex: http://127.0.0.1:8000)</p>
        <div className="mt-3 grid gap-3 md:max-w-xl">
          <label className="text-sm text-slate-600">API Endpoint (Base URL)</label>
          <div className="flex gap-2">
            <input 
              value={apiUrl} 
              onChange={(e) => setApiUrl(e.target.value)} 
              className="flex-1 rounded-md border border-border px-3 py-2 text-sm" 
              placeholder="http://127.0.0.1:8000"
            />
            <button 
              type="button" 
              onClick={onSaveApiUrl}
              className="rounded-md border border-border bg-slate-50 px-3 py-2 text-sm font-medium hover:bg-slate-100"
            >
              Definir
            </button>
          </div>
          <div className="flex items-center gap-3">
            <button 
              type="button" 
              onClick={onTestConnection}
              className="rounded-md bg-slate-900 px-3 py-2 text-sm font-semibold text-white hover:bg-slate-800"
            >
              {testStatus === 'testing' ? 'Testando...' : 'Testar conexao'}
            </button>
            {testStatus === 'success' && <span className="text-sm font-medium text-emerald-600">Online</span>}
            {testStatus === 'error' && <span className="text-sm font-medium text-red-600">Offline</span>}
          </div>
        </div>
      </Card>
    </div>
  )
}
