import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return '-'
  return new Date(iso).toLocaleDateString('ko-KR', { year: 'numeric', month: '2-digit', day: '2-digit' })
}

export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return '-'
  return new Date(iso).toLocaleString('ko-KR', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

export function formatNumber(n: number | null | undefined, decimals = 1): string {
  if (n == null) return '-'
  return n.toLocaleString('ko-KR', { maximumFractionDigits: decimals })
}

export function formatPct(n: number | null | undefined): string {
  if (n == null) return '-'
  return (n > 0 ? '+' : '') + n.toFixed(1) + '%'
}
