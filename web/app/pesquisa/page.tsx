import { withProtectedShell } from '@/components/layout/protected-app-page'
import { MarketResearchPage } from '@/components/pages/market-research-page'

export default async function PesquisaPage() {
  return withProtectedShell((ctx) => <MarketResearchPage workspaceId={ctx.workspaceId} />)
}
