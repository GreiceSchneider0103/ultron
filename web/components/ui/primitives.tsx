import type { ReactNode } from 'react'

export function Card({ children, className = '' }: { children: ReactNode; className?: string }) {
  return <section className={`rounded-xl border border-border bg-card p-5 shadow-sm ${className}`}>{children}</section>
}

export function Badge({
  children,
  tone = 'neutral',
}: {
  children: ReactNode
  tone?: 'neutral' | 'success' | 'warning' | 'danger'
}) {
  const tones: Record<string, string> = {
    neutral: 'bg-slate-100 text-slate-700',
    success: 'bg-emerald-100 text-emerald-700',
    warning: 'bg-amber-100 text-amber-700',
    danger: 'bg-red-100 text-red-700',
  }
  return <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-semibold ${tones[tone]}`}>{children}</span>
}

export function Chip({ children }: { children: ReactNode }) {
  return <span className="inline-flex rounded-md border border-border bg-white px-2 py-1 text-xs text-slate-600">{children}</span>
}

export function Skeleton({ className = '' }: { className?: string }) {
  return <div className={`animate-pulse rounded-md bg-slate-200 ${className}`} />
}

export function EmptyState({
  title,
  description,
  action,
}: {
  title: string
  description: string
  action?: ReactNode
}) {
  return (
    <Card className="text-center">
      <h3 className="text-lg font-semibold">{title}</h3>
      <p className="mt-2 text-sm text-muted-foreground">{description}</p>
      {action ? <div className="mt-4">{action}</div> : null}
    </Card>
  )
}

export function ErrorState({
  message,
  onRetry,
}: {
  message: string
  onRetry?: () => void
}) {
  return (
    <Card className="border-red-200 bg-red-50">
      <p className="text-sm text-red-700">{message}</p>
      {onRetry ? (
        <button
          type="button"
          className="mt-3 rounded-md bg-red-600 px-3 py-2 text-sm font-semibold text-white hover:bg-red-700"
          onClick={onRetry}
        >
          Tentar novamente
        </button>
      ) : null}
    </Card>
  )
}
