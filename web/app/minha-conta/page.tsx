import { withProtectedShell } from '@/components/layout/protected-app-page'
import { MyAccountPage } from '@/components/pages/my-account-page'

export default async function MinhaContaPage() {
  return withProtectedShell((ctx) => (
    <MyAccountPage
      email={ctx.user.email ?? 'usuario@exemplo.com'}
      workspaceName={ctx.workspace.name}
      role={ctx.role}
      workspaceId={ctx.workspaceId}
    />
  ))
}
