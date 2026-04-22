import { supabase } from './supabase'

const BASE = import.meta.env.VITE_API_BASE_URL as string

async function apiFetch(path: string, options: RequestInit = {}): Promise<Response> {
  const { data: { session } } = await supabase.auth.getSession()
  const token = session?.access_token

  const res = await fetch(`${BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  })

  if (res.status === 401) {
    await supabase.auth.refreshSession()
    const { data: { session: next } } = await supabase.auth.getSession()
    if (!next) throw new Error('session_expired')
    return fetch(`${BASE}${path}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${next.access_token}`,
        ...options.headers,
      },
    })
  }
  return res
}

async function parseJson(res: Response) {
  const json = await res.json()
  if (!res.ok) throw new Error(json?.error ?? `HTTP ${res.status}`)
  return json?.data ?? json
}

// ── Categories ────────────────────────────────────────
export const categoryApi = {
  create: (body: unknown) =>
    apiFetch('/api/v1/categories', { method: 'POST', body: JSON.stringify(body) }).then(parseJson),
  update: (code: string, body: unknown) =>
    apiFetch(`/api/v1/categories/${code}`, { method: 'PUT', body: JSON.stringify(body) }).then(parseJson),
  remove: (code: string) =>
    apiFetch(`/api/v1/categories/${code}`, { method: 'DELETE' }).then(parseJson),
}

// ── Consumer Items ────────────────────────────────────
export const consumerItemApi = {
  create: (body: unknown) =>
    apiFetch('/api/v1/consumer-items', { method: 'POST', body: JSON.stringify(body) }).then(parseJson),
  update: (id: string, body: unknown) =>
    apiFetch(`/api/v1/consumer-items/${id}`, { method: 'PUT', body: JSON.stringify(body) }).then(parseJson),
  remove: (id: string) =>
    apiFetch(`/api/v1/consumer-items/${id}`, { method: 'DELETE' }).then(parseJson),
  restore: (id: string) =>
    apiFetch(`/api/v1/consumer-items/${id}/restore`, { method: 'POST' }).then(parseJson),
}
