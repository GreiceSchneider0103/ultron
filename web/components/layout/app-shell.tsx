'use client'

import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import { type ReactNode, useMemo, useState } from 'react'

import { createClient } from '@/utils/supabase/client'
import { ApiStatus } from '@/components/layout/api-status'

type AppShellProps = {
  children: ReactNode
  userEmail: string
  workspaceName: string
}

const primaryNav = [
  { href: '/home', label: 'Dashboard' },
  { href: '/pesquisa', label: 'Pesquisa de Mercado' },
  { href: '/auditoria', label: 'Auditoria de Anuncio' },
  { href: '/gerar-anuncio', label: 'Gerar Anuncio' },
  { href: '/monitoramento', label: 'Monitoramento & Alertas' },
  { href: '/relatorios', label: 'Relatorios' },
  { href: '/biblioteca', label: 'Biblioteca' },
  { href: '/regras', label: 'Regras por Marketplace' },
  { href: '/margem', label: 'Margem & Estrategia' },
]

const secondaryNav = [
  { href: '/configuracoes', label: 'Configuracoes' },
  { href: '/usuarios', label: 'Usuarios' },
  { href: '/minha-conta', label: 'Minha Conta' },
]

export function AppShell({ children, userEmail, workspaceName }: AppShellProps) {
  const pathname = usePathname()
  const router = useRouter()
  const [collapsed, setCollapsed] = useState(false)
  const initials = useMemo(() => (userEmail?.slice(0, 2).toUpperCase() || 'UL'), [userEmail])

  async function onSignOut() {
    const supabase = createClient()
    await supabase.auth.signOut()
    router.push('/login')
  }

  function NavItem({ href, label }: { href: string; label: string }) {
    const active = pathname === href || (href !== '/home' && pathname.startsWith(href))
    return (
      <Link
        href={href}
        className={`flex items-center rounded-lg px-3 py-2 text-sm transition ${
          active ? 'bg-primary text-primary-foreground' : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
        }`}
      >
        {!collapsed ? label : label.slice(0, 2)}
      </Link>
    )
  }

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      <aside className={`hidden border-r border-border bg-white lg:flex lg:flex-col ${collapsed ? 'w-20' : 'w-64'}`}>
        <div className="border-b border-border px-4 py-4">
          <p className="text-lg font-semibold text-slate-900">{collapsed ? 'U' : 'Ultron'}</p>
          {!collapsed ? <p className="text-xs text-slate-500">Marketplace AI</p> : null}
        </div>
        <nav className="ultron-scrollbar flex-1 space-y-1 overflow-y-auto px-3 py-3">
          {primaryNav.map((item) => (
            <NavItem key={item.href} {...item} />
          ))}
        </nav>
        <div className="space-y-1 border-t border-border px-3 py-3">
          {secondaryNav.map((item) => (
            <NavItem key={item.href} {...item} />
          ))}
          <button
            type="button"
            className="w-full rounded-lg px-3 py-2 text-left text-sm text-red-600 hover:bg-red-50"
            onClick={onSignOut}
          >
            {collapsed ? 'Sair' : 'Sair'}
          </button>
          <button
            type="button"
            className="w-full rounded-lg border border-border px-3 py-2 text-left text-xs text-slate-600 hover:bg-slate-50"
            onClick={() => setCollapsed((v) => !v)}
          >
            {collapsed ? 'Expandir' : 'Recolher'}
          </button>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
        <header className="flex h-14 items-center gap-3 border-b border-border bg-white px-4">
          <input
            className="w-full max-w-md rounded-lg border border-border bg-slate-50 px-3 py-2 text-sm outline-none focus:border-primary"
            placeholder="Buscar anuncio, SKU, palavra-chave..."
          />
          <ApiStatus />
          <div className="hidden rounded-lg border border-border px-3 py-1.5 text-sm text-slate-700 md:block">
            ML
          </div>
          <div className="hidden rounded-lg border border-border px-3 py-1.5 text-sm text-slate-700 md:block">
            {workspaceName}
          </div>
          <button className="rounded-lg bg-primary px-3 py-1.5 text-sm font-semibold text-primary-foreground">
            Nova analise
          </button>
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-blue-600 text-xs font-semibold text-white">
            {initials}
          </div>
        </header>

        <main className="ultron-scrollbar flex-1 overflow-y-auto p-4 lg:p-6">{children}</main>
      </div>
    </div>
  )
}
