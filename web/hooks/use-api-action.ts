'use client'

import { useCallback, useState } from 'react'
import { useToast } from '@/components/ui/toast/use-toast'

export function useApiAction<T>() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string>('')
  const [data, setData] = useState<T | null>(null)
  const toast = useToast()

  const run = useCallback(async (fn: () => Promise<T>) => {
    setLoading(true)
    setError('')
    try {
      const response = await fn()
      setData(response)
      return response
    } catch (err) {
      // Extrai mensagem de erro com prioridade:
      // 1) objeto com .message (ApiError do cliente)
      // 2) Error normal -> err.message
      // 3) fallback genérico
      let message = 'Erro ao conectar com o backend'
      if (typeof err === 'object' && err !== null && 'message' in err) {
        try {
          message = String((err as { message?: unknown }).message || message)
        } catch {
          message = 'Erro ao conectar com o backend'
        }
      } else if (err instanceof Error) {
        message = err.message
      } else if (typeof err === 'string') {
        message = err
      }

      setError(message)
      toast.error(message)
      return null
    } finally {
      setLoading(false)
    }
  }, [toast])

  return { loading, error, data, setData, setError, run }
}
