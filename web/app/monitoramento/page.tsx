import { withProtectedShell } from '@/components/layout/protected-app-page'
import { MonitoringPage } from '@/components/pages/monitoring-page'

export default async function MonitoramentoPage() {
  return withProtectedShell((ctx) => <MonitoringPage workspaceId={ctx.workspaceId} />)
}
