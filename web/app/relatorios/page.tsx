import { withProtectedShell } from '@/components/layout/protected-app-page'
import { ReportsPage } from '@/components/pages/reports-page'

export default async function RelatoriosPage() {
  return withProtectedShell((ctx) => <ReportsPage workspaceId={ctx.workspaceId} />)
}
