import ApiConsole from '@/components/api-console'
import ToolsNav from '@/components/tools-nav'
import { getWorkspaceContext } from '@/utils/workspace/server'

export default async function AlertsToolsPage() {
  const { workspaceId } = await getWorkspaceContext()

  return (
    <div className="min-h-screen bg-slate-950 p-6 text-slate-100 md:p-10">
      <div className="mx-auto max-w-6xl space-y-6">
        <ToolsNav />
        <header className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
          <h1 className="text-3xl font-bold">Alerts</h1>
          <p className="mt-2 text-slate-300">Gerencie regras e eventos de alerta.</p>
        </header>

        <ApiConsole
          title="Listar regras"
          description="GET /api/alerts"
          workspaceId={workspaceId}
          defaultPath="/api/alerts"
          defaultMethod="GET"
          defaultQuery={{}}
        />

        <ApiConsole
          title="Criar regra"
          description="POST /api/alerts"
          workspaceId={workspaceId}
          defaultPath="/api/alerts"
          defaultMethod="POST"
          defaultBody={{
            name: 'Preco abaixo do limite',
            condition: {
              field: 'price',
              op: 'lt',
              value: 99.9,
            },
            is_active: true,
          }}
        />

        <ApiConsole
          title="Listar eventos"
          description="GET /api/alerts/events"
          workspaceId={workspaceId}
          defaultPath="/api/alerts/events"
          defaultMethod="GET"
          defaultQuery={{}}
        />
      </div>
    </div>
  )
}
