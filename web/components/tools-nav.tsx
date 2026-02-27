import Link from 'next/link'

const links = [
  { href: '/dashboard', label: 'Dashboard' },
  { href: '/tools', label: 'Ferramentas' },
  { href: '/tools/market-research', label: 'Market Research' },
  { href: '/tools/seo', label: 'SEO' },
  { href: '/tools/alerts', label: 'Alerts' },
  { href: '/tools/custom', label: 'Custom API' },
]

export default function ToolsNav() {
  return (
    <nav className="flex flex-wrap gap-2">
      {links.map((link) => (
        <Link
          key={link.href}
          href={link.href}
          className="rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-200 hover:border-cyan-400 hover:text-cyan-300"
        >
          {link.label}
        </Link>
      ))}
    </nav>
  )
}
