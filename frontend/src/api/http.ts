const BASE_URL = '/api'

export async function fetchApi<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!response.ok) {
    throw new Error(`API error: ${response.status} ${response.statusText}`)
  }
  return response.json()
}

export const api = {
  health: () => fetchApi<{ status: string; version: string }>('/health'),
  getTools: () => fetchApi<any[]>('/tools'),
  getModels: () => fetchApi<any[]>('/models'),
  getAgents: () => fetchApi<any[]>('/agents'),
  getSessions: () => fetchApi<any[]>('/sessions'),
}
