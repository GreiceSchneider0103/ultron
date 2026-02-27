export function JsonView({ value }: { value: unknown }) {
  return (
    <pre className="ultron-scrollbar overflow-x-auto rounded-lg border border-border bg-slate-950 p-3 text-xs text-slate-100">
      {JSON.stringify(value, null, 2)}
    </pre>
  )
}
