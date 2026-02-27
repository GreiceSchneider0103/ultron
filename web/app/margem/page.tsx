import { withProtectedShell } from '@/components/layout/protected-app-page'
import { MarginPage } from '@/components/pages/margin-page'

export default async function MargemPage() {
  return withProtectedShell((ctx) => <MarginPage workspaceId={ctx.workspaceId} />)
}
