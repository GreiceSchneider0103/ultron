import ApiConsole from '@/components/api-console'
import ToolsNav from '@/components/tools-nav'
import { getWorkspaceContext } from '@/utils/workspace/server'

export default async function SeoToolsPage() {
  const { workspaceId } = await getWorkspaceContext()

  return (
    <div className="min-h-screen bg-slate-950 p-6 text-slate-100 md:p-10">
      <div className="mx-auto max-w-6xl space-y-6">
        <ToolsNav />
        <header className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
          <h1 className="text-3xl font-bold">SEO</h1>
          <p className="mt-2 text-slate-300">Teste rapido dos endpoints de SEO.</p>
        </header>

        <ApiConsole
          title="Extrair keywords"
          description="GET /api/seo/keywords"
          workspaceId={workspaceId}
          defaultPath="/api/seo/keywords"
          defaultMethod="GET"
          defaultQuery={{
            marketplace: 'mercadolivre',
            product_title: 'Tenis Nike corrida masculino amortecimento',
            limit: 20,
          }}
        />

        <ApiConsole
          title="Otimizar titulo"
          description="POST /api/seo/optimize-title"
          workspaceId={workspaceId}
          defaultPath="/api/seo/optimize-title"
          defaultMethod="POST"
          defaultBody={{
            marketplace: 'mercadolivre',
            product_title: 'Tenis Nike corrida masculino',
            limit: 5,
          }}
        />
      </div>
    </div>
  )
}
