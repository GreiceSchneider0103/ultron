'use client'

import { useCallback, useEffect, useState } from 'react'

import { Card, ErrorState } from '@/components/ui/primitives'
import { getWorkspaceMembers } from '@/services/settings.service'

type Member = {
  user_id: string
  role: string
  created_at: string
}

export function UsersPage({ workspaceId }: { workspaceId: string }) {
  const [members, setMembers] = useState<Member[]>([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const data = (await getWorkspaceMembers(workspaceId)) as Member[]
      setMembers(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro ao carregar usuarios')
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

  return (
    <div className="space-y-5">
      <h1 className="text-3xl font-semibold">Usuarios</h1>
      {error ? <ErrorState message={error} onRetry={() => load()} /> : null}
      <Card>
        {loading ? (
          <p className="text-sm text-muted-foreground">Carregando membros...</p>
        ) : (
          <table className="min-w-full text-left text-sm">
            <thead className="text-slate-500">
              <tr>
                <th className="py-2 pr-3">User ID</th>
                <th className="py-2 pr-3">Role</th>
                <th className="py-2 pr-3">Criado em</th>
              </tr>
            </thead>
            <tbody>
              {members.map((m) => (
                <tr key={`${m.user_id}-${m.created_at}`} className="border-t border-border">
                  <td className="py-2 pr-3">{m.user_id}</td>
                  <td className="py-2 pr-3">{m.role}</td>
                  <td className="py-2 pr-3">{new Date(m.created_at).toLocaleString('pt-BR')}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  )
}
