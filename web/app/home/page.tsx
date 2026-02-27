import { DashboardHome } from '@/components/pages/dashboard-home'
import { withProtectedShell } from '@/components/layout/protected-app-page'

export default async function HomePage() {
  return withProtectedShell((ctx) => <DashboardHome workspaceId={ctx.workspaceId} />)
}
