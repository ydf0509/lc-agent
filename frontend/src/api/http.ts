const BASE_URL = '/api'

export async function fetchApi<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!response.ok) {
    throw new Error(`API error: ${response.status} ${response.statusText}`)
  }
  if (response.status === 204) return undefined as T
  return response.json()
}

export const api = {
  health: () => fetchApi<{ status: string; version: string }>('/health'),

  getTools: () => fetchApi<{ name: string; group: string; description: string }[]>('/tools'),
  getToolGroups: () => fetchApi<{ name: string; tools: { name: string; description: string }[] }[]>('/tools/groups'),

  getModels: () => fetchApi<{ id: string; provider: string; base_url: string; context_limit: number }[]>('/models'),

  getAgents: () => fetchApi<any[]>('/agents'),
  createAgent: (data: object) => fetchApi<any>('/agents', { method: 'POST', body: JSON.stringify(data) }),
  updateAgent: (id: string, data: object) => fetchApi<any>(`/agents/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteAgent: (id: string) => fetchApi<void>(`/agents/${id}`, { method: 'DELETE' }),

  getSessions: () => fetchApi<any[]>('/sessions'),
  createSession: (data: { title?: string; agent_id?: string; model?: string }) =>
    fetchApi<{ id: string; title: string }>('/sessions', { method: 'POST', body: JSON.stringify(data) }),
  updateSession: (id: string, data: { title?: string }) =>
    fetchApi<any>(`/sessions/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteSession: (id: string) =>
    fetchApi<void>(`/sessions/${id}`, { method: 'DELETE' }),
}
