import { withProtectedShell } from '@/components/layout/protected-app-page'
import { SettingsPage } from '@/components/pages/settings-page'

export default async function ConfiguracoesPage() {
  return withProtectedShell((ctx) => <SettingsPage workspaceId={ctx.workspaceId} />)
}
