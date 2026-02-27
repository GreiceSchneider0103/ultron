import ApiConsole from '@/components/api-console'
import ToolsNav from '@/components/tools-nav'
import { getWorkspaceContext } from '@/utils/workspace/server'

export default async function CustomToolsPage() {
  const { workspaceId } = await getWorkspaceContext()

  return (
    <div className="min-h-screen bg-slate-950 p-6 text-slate-100 md:p-10">
      <div className="mx-auto max-w-6xl space-y-6">
        <ToolsNav />
        <header className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
          <h1 className="text-3xl font-bold">Custom API</h1>
          <p className="mt-2 text-slate-300">
            Execute qualquer endpoint da API usando seu token autenticado.
          </p>
        </header>

        <ApiConsole
          title="Request customizada"
          description="Edite metodo, path, query e body livremente."
          workspaceId={workspaceId}
          defaultPath="/api/market-research/search"
          defaultMethod="GET"
          defaultQuery={{
            marketplace: 'mercadolivre',
            query: 'tenis',
            limit: 5,
            offset: 0,
          }}
          defaultBody={{}}
          lockPath={false}
        />
      </div>
    </div>
  )
}
