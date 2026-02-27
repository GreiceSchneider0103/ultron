import Link from 'next/link'

import ToolsNav from '@/components/tools-nav'
import { getWorkspaceContext } from '@/utils/workspace/server'

export default async function ToolsHomePage() {
  const { workspaceId } = await getWorkspaceContext()

  const cards = [
    {
      href: '/tools/market-research',
      title: 'Market Research',
      description: 'Busca de produtos, analise de concorrencia e validacao de catalogo.',
    },
    {
      href: '/tools/seo',
      title: 'SEO',
      description: 'Keywords, sugestao de titulos e auditoria de listing.',
    },
    {
      href: '/tools/alerts',
      title: 'Alerts',
      description: 'Criacao e leitura de regras/eventos de monitoramento.',
    },
    {
      href: '/tools/custom',
      title: 'Custom API',
      description: 'Monte requests para qualquer endpoint /api/*.',
    },
  ]

  return (
    <div className="min-h-screen bg-slate-950 p-6 text-slate-100 md:p-10">
      <div className="mx-auto max-w-6xl space-y-6">
        <ToolsNav />
        <header className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
          <h1 className="text-3xl font-bold">Ferramentas da API</h1>
          <p className="mt-2 text-slate-300">Workspace ativo: {workspaceId}</p>
        </header>

        <section className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {cards.map((card) => (
            <Link
              key={card.href}
              href={card.href}
              className="rounded-xl border border-slate-800 bg-slate-900 p-5 transition hover:border-cyan-400"
            >
              <h2 className="text-xl font-semibold">{card.title}</h2>
              <p className="mt-2 text-sm text-slate-400">{card.description}</p>
            </Link>
          ))}
        </section>
      </div>
    </div>
  )
}
