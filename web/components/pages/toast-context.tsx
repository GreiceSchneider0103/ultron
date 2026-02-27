'use client'

import { createContext } from 'react'

export type ToastType = 'success' | 'error' | 'info'

export interface Toast {
  id: string
  message: string
  type: ToastType
  title?: string
}

export interface ToastContextValue {
  addToast: (message: string, type: ToastType, title?: string) => void
  removeToast: (id: string) => void
}

export const ToastContext = createContext<ToastContextValue | null>(null)