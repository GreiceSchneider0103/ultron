import { withProtectedShell } from '@/components/layout/protected-app-page'
import { UsersPage } from '@/components/pages/users-page'

export default async function UsuariosPageRoute() {
  return withProtectedShell((ctx) => <UsersPage workspaceId={ctx.workspaceId} />)
}
