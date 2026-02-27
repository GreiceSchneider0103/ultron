import ApiConsole from '@/components/api-console'
import ToolsNav from '@/components/tools-nav'
import { getWorkspaceContext } from '@/utils/workspace/server'

export default async function MarketResearchToolsPage() {
  const { workspaceId } = await getWorkspaceContext()

  return (
    <div className="min-h-screen bg-slate-950 p-6 text-slate-100 md:p-10">
      <div className="mx-auto max-w-6xl space-y-6">
        <ToolsNav />
        <header className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
          <h1 className="text-3xl font-bold">Market Research</h1>
          <p className="mt-2 text-slate-300">Consumo direto dos endpoints de pesquisa de mercado.</p>
        </header>

        <ApiConsole
          title="Buscar listings"
          description="GET /api/market-research/search"
          workspaceId={workspaceId}
          defaultPath="/api/market-research/search"
          defaultMethod="GET"
          defaultQuery={{
            marketplace: 'mercadolivre',
            query: 'tenis corrida',
            limit: 10,
            offset: 0,
          }}
        />

        <ApiConsole
          title="Analisar mercado"
          description="POST /api/market-research/analyze"
          workspaceId={workspaceId}
          defaultPath="/api/market-research/analyze"
          defaultMethod="POST"
          defaultBody={{
            keyword: 'tenis corrida',
            marketplace: 'mercadolivre',
            limit: 10,
          }}
        />
      </div>
    </div>
  )
}
