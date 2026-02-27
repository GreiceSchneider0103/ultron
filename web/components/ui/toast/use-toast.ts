'use client'

import { useContext } from 'react'

import { ToastContext } from './toast-context'

export function useToast() {
  const context = useContext(ToastContext)
  if (!context) {
    throw new Error('useToast must be used within a ToastProvider')
  }

  return {
    success: (msg: string, title?: string) => context.addToast(msg, 'success', title),
    error: (msg: string, title?: string) => context.addToast(msg, 'error', title),
    info: (msg: string, title?: string) => context.addToast(msg, 'info', title),
  }
}
