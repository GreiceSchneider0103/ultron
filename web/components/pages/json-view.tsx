'use client'

export function JsonView({ value }: { value: unknown }) {
  return (
    <pre className="overflow-auto rounded-lg bg-slate-950 p-4 text-xs text-slate-50">
      {JSON.stringify(value, null, 2)}
    </pre>
  )
}