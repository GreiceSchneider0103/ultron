import { withProtectedShell } from '@/components/layout/protected-app-page'
import { AdAuditPage } from '@/components/pages/ad-audit-page'

export default async function AuditoriaPage() {
  return withProtectedShell((ctx) => <AdAuditPage workspaceId={ctx.workspaceId} />)
}
