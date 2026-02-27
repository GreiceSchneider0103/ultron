'use client'

import { Toast } from './toast-context'

export function ToastItem({ toast, onClose }: { toast: Toast; onClose: () => void }) {
  const bg =
    toast.type === 'success'
      ? 'bg-emerald-50 border-emerald-200 text-emerald-800'
      : toast.type === 'error'
        ? 'bg-red-50 border-red-200 text-red-800'
        : 'bg-blue-50 border-blue-200 text-blue-800'

  return (
    <div className={`flex w-80 items-start justify-between rounded-lg border p-4 shadow-lg transition-all ${bg}`}>
      <div>
        {toast.title && <h4 className="font-semibold">{toast.title}</h4>}
        <p className="text-sm">{toast.message}</p>
      </div>
      <button onClick={onClose} className="ml-4 text-sm font-bold opacity-50 hover:opacity-100">
        X
      </button>
    </div>
  )
}
