import { useCallback, useState } from 'react'

/**
 * 非同期操作を管理するカスタムフック
 * - 実行中の操作名を busyOp で追跡
 * - 同時実行を防止
 * - try/catch/finally の定型を吸収
 *
 * @returns {{ busyOp: string, run: (name: string, fn: () => Promise<void>) => Promise<void> }}
 */
export function useAsyncAction() {
  const [busyOp, setBusyOp] = useState('')

  const run = useCallback(async (name, fn) => {
    if (busyOp) return
    setBusyOp(name)
    try {
      await fn()
    } finally {
      setBusyOp('')
    }
  }, [busyOp])

  return { busyOp, setBusyOp, run }
}
