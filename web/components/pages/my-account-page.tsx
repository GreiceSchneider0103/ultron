'use client'

import { Card, Chip } from '@/components/ui/primitives'

export function MyAccountPage({
  email,
  workspaceName,
  role,
  workspaceId,
}: {
  email: string
  workspaceName: string
  role: string
  workspaceId: string
}) {
  return (
    <div className="space-y-5">
      <h1 className="text-3xl font-semibold">Minha Conta</h1>
      <Card className="space-y-3">
        <div>
          <p className="text-xs uppercase tracking-wide text-slate-500">Email</p>
          <p className="text-sm text-slate-800">{email}</p>
        </div>
        <div>
          <p className="text-xs uppercase tracking-wide text-slate-500">Workspace</p>
          <p className="text-sm text-slate-800">{workspaceName}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Chip>{role}</Chip>
          <Chip>{workspaceId}</Chip>
        </div>
      </Card>
    </div>
  )
}
