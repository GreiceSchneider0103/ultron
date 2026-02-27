import type { ReactNode } from 'react'

import { AppShell } from '@/components/layout/app-shell'
import { getWorkspaceContext } from '@/utils/workspace/server'

export async function withProtectedShell(children: (ctx: Awaited<ReturnType<typeof getWorkspaceContext>>) => ReactNode) {
  const ctx = await getWorkspaceContext()
  return (
    <AppShell userEmail={ctx.user.email ?? 'usuario'} workspaceName={ctx.workspace.name}>
      {children(ctx)}
    </AppShell>
  )
}
