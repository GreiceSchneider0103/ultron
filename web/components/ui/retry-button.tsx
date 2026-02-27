'use client'

type RetryButtonProps = {
  onRetry: () => void | Promise<void>
  loading?: boolean
  label?: string
}

export function RetryButton({ onRetry, loading, label = 'Tentar novamente' }: RetryButtonProps) {
  return (
    <button
      type="button"
      onClick={() => onRetry()}
      disabled={loading}
      className="mt-2 inline-flex items-center gap-2 rounded-md border border-red-200 bg-white px-3 py-2 text-sm font-medium text-red-700 hover:bg-red-50 disabled:opacity-50"
    >
      <svg
        xmlns="http://www.w3.org/2000/svg"
        width="16"
        height="16"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        className={loading ? 'animate-spin' : ''}
      >
        <path d="M21 12a9 9 0 1 1-9-9c2.52 0 4.93 1 6.74 2.74L21 8" />
        <path d="M21 3v5h-5" />
      </svg>
      {loading ? 'Tentando...' : label}
    </button>
  )
}