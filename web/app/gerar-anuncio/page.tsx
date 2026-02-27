import { withProtectedShell } from '@/components/layout/protected-app-page'
import { GenerateAdPage } from '@/components/pages/generate-ad-page'

export default async function GerarAnuncioPage() {
  return withProtectedShell((ctx) => <GenerateAdPage workspaceId={ctx.workspaceId} />)
}
