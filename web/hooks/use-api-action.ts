'use client'

import { useCallback, useState } from 'react'

export function useApiAction<T>() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string>('')
  const [data, setData] = useState<T | null>(null)

  const run = useCallback(async (fn: () => Promise<T>) => {
    setLoading(true)
    setError('')
    try {
      const response = await fn()
      setData(response)
      return response
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Erro desconhecido'
      setError(message)
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  return { loading, error, data, setData, setError, run }
}
